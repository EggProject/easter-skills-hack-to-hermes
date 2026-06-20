"""Script #2 — per-profile audit/flip for the migrated skill-creator (plan 06).

Public surface:
    app:                click command group (the CLI)
    run_audit(...):     programmatic entry point used by tests
    make_cli():         click.testing.CliRunner factory
    AuditReport:        dataclass-shaped dict-like report (the JSON shape)

The script is invoked as ``hermes-skill-creator-profiles`` (declared in
``pyproject.toml``). It walks every Hermes profile (the default
``hermes`` profile and every named profile returned by
``hermes_cli.profiles.list_profiles()``), audits the per-profile
skills tree, and (with ``--apply``) installs/replaces the migrated
``skill-creator`` at the flat path ``<HERMES_HOME>/skills/skill-creator/``.

The replace is in-place: the factory skill-creator (installed from
``openai/skills/skill-creator`` per ``hermes_cli/skills_hub.py``) and
the migrated skill share the same dir/name; ``do_install(force=True,
...)`` overwrites the factory at the flat path. We do NOT disable the
factory by NAME (the disable check is keyed by skill NAME per
``tools/skills_tool.py:597``: ``return name in global_disabled``);
adding ``"openai"`` or ``"skills"`` to the disabled list is a no-op
(no skill has those names) and would mislead operators — S5 BLOCKER
fix.

Safety:
- Runs under ``hermes_home_scope(path)`` which mirrors HERMES_HOME in
  BOTH the ``hermes_constants`` override token AND ``os.environ``.
- Refuses ``--apply`` against the live ``~/.hermes`` unless ``--yes``
  is passed AND the output is a TTY.
- All console messages are bilingual (en/hu single line).
- ``--help`` has two mirrored sections (English / magyar).

See also: plans/06-script-2-profiles.md, plans/09-test-strategy.md.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import cast

import click

# Tests grep this module's source for the canonical import lines
# (the read-side ``agent.skill_utils.get_disabled_skill_names`` and
# the write-side ``hermes_cli.skills_config.save_disabled_skills``);
# the audit helpers live in ``_cli_profiles_audit`` and the unused-
# import silencer is mandated by the test contract.
from agent.skill_utils import get_disabled_skill_names  # noqa: F401
from hermes_cli.profiles import ProfileInfo
from hermes_cli.skills_config import save_disabled_skills  # noqa: F401

from hermes_skill_creator_plugin._cli_profiles_cli import (
    main_cmd,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    make_cli as _make_cli,
)
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport
from hermes_skill_creator_plugin.cli_profiles_row import (
    _audit_and_collect_row,
    _bilingual,
    _empty_report,
)
from hermes_skill_creator_plugin.cli_profiles_select import (
    _live_install_refused,
    _select_profiles,
)

# ---------------------------------------------------------------------------
# Module-level constants (preserved for tests / external callers).
# ---------------------------------------------------------------------------

TOOL_NAME = "hermes-skill-creator-profiles"
TOOL_VERSION = "0.1.0"
# Canonical per-profile subdir set (mirrors hermes_cli/profiles.py).
PROFILE_DIRS: tuple[str, ...] = (
    "memories",
    "sessions",
    "skills",
    "skins",
    "logs",
    "plans",
    "workspace",
    "cron",
    "home",
)


# ---------------------------------------------------------------------------
# Programmatic entry point.
# ---------------------------------------------------------------------------


def _extract_audit_options(options: dict[str, object]) -> dict[str, object]:
    """Pull the recognized keyword options out of the raw options dict."""
    return {
        "apply": bool(options.get("apply", False)),
        "json_path": options.get("json_path"),
        "frozen_time": options.get("frozen_time"),
        "skip_install": bool(options.get("skip_install", False)),
        "yes": bool(options.get("yes", False)),
        "profile": options.get("profile"),
    }


def _run_audit_phase(opts: dict[str, object]) -> AuditReport:
    """Drive the audit/flip after the live-install refusal gate."""
    audit_params = _AuditPhaseParams.from_opts(opts)
    click.echo(_bilingual("profiles_msg_scanning"))
    selected = _select_profiles(_list_all_profiles(), audit_params.profile)
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return _empty_report(audit_params.frozen_time)
    return _audit_each_profile(selected, audit_params)


def _list_all_profiles() -> list[ProfileInfo]:
    from hermes_cli.profiles import list_profiles

    return list_profiles()


def _audit_each_profile(
    selected: list[ProfileInfo],
    audit_params: _AuditPhaseParams,
) -> AuditReport:
    mode_key = "profiles_msg_applying" if audit_params.apply else "profiles_msg_audit_default"
    click.echo(_bilingual(mode_key))
    report = _empty_report(audit_params.frozen_time)
    for profile_info in selected:
        row = _audit_and_collect_row(
            profile_info,
            apply=audit_params.apply,
            skip_install=audit_params.skip_install,
            frozen_time=audit_params.frozen_time,
        )
        report.profiles.append(row)
    click.echo(_bilingual("profiles_msg_done", n=len(selected)))
    return report


@dataclasses.dataclass(frozen=True)
class _AuditPhaseParams:
    """Validated, typed view of the audit-phase options dict."""

    apply: bool
    frozen_time: str | None
    skip_install: bool
    profile: str | None

    @classmethod
    def from_opts(cls, opts: dict[str, object]) -> _AuditPhaseParams:
        return cls(
            apply=bool(opts["apply"]),
            frozen_time=cast("str | None", opts["frozen_time"]),
            skip_install=bool(opts["skip_install"]),
            profile=cast("str | None", opts["profile"]),
        )


def run_audit(**options: object) -> AuditReport:
    """Run the per-profile audit/flip.

    Accepted keyword options:
        apply (bool): Perform the writes (--apply).
        json_path (Path | None): Optional path to write the JSON report to.
        frozen_time (str | None): Optional ISO 8601 UTC string to pin
            the report timestamp (D7: determinism).
        skip_install (bool): Audit only; do not call do_install.
        yes (bool): Suppress the live-install refusal.
        profile (str | None): Optional single profile NAME to restrict.

    Returns:
        The AuditReport (also written to json_path if given).
    """
    opts = _extract_audit_options(options)

    # 0. Live-install refusal (safety contract). The refusal fires
    #    whenever HERMES_HOME resolves to the LIVE install AND --yes is
    #    absent — TTY or not, CI or interactive. Operators who really
    #    want to write to the live install must pass --yes.
    if _live_install_refused(bool(opts["apply"]), bool(opts["yes"])):
        click.echo(_bilingual("profiles_msg_refuse_no_yes"))
        sys.exit(5)

    report = _run_audit_phase(opts)

    json_path = opts["json_path"]
    if json_path is not None:
        from hermes_skill_creator_plugin.cli_profiles_row import (
            _write_json_report,
        )

        _write_json_report(report, cast("Path", json_path))

    return report


# ---------------------------------------------------------------------------
# Click CLI re-export.
# ---------------------------------------------------------------------------


# `app` is the alias tests use; `main` is the click entry point declared
# in pyproject.toml. Both alias the click command built in
# ``_cli_profiles_cli.main_cmd``.
app = main_cmd
main = main_cmd
make_cli = _make_cli
