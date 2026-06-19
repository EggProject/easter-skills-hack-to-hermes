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

import os
import sys
from datetime import UTC, datetime
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

from hermes_skill_creator_plugin._cli_profiles_audit import (
    audit_profile as _audit_profile,
)
from hermes_skill_creator_plugin._cli_profiles_audit import (
    build_bilingual as _build_bilingual,
)
from hermes_skill_creator_plugin._cli_profiles_audit import (
    diff_sets,
    walk_skills,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    build_help_text as _build_help_text,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    main_cmd,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    make_cli as _make_cli,
)
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport
from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

# Re-exports for tests / external callers (do NOT remove — tests
# import these by name from ``hermes_skill_creator_plugin.cli_profiles``).
_walk_skills = walk_skills
_diff = diff_sets

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
# Live install refusal (per the safety contract).
LIVE_HERMES_HOME = Path.home() / ".hermes"


# ---------------------------------------------------------------------------
# Bilingual helper + per-row presentation.
# ---------------------------------------------------------------------------


def _bilingual(key: str, **format_kwargs: object) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key."""
    return _build_bilingual(EN, HU, key, **format_kwargs)


def _now_iso(frozen_time: str | None) -> str:
    """Return the report timestamp (stable when ``frozen_time`` is set)."""
    if frozen_time is not None:
        return frozen_time
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# Sentinels for the per-row "value list or dash" presentation.
_DASH = "-"
# Audit-options dict keys (WPS226 — reused > 3 times).
_KEY_APPLY = "apply"
_KEY_JSON_PATH = "json_path"
_KEY_FROZEN_TIME = "frozen_time"
_KEY_SKIP_INSTALL = "skip_install"
_KEY_YES = "yes"
_KEY_PROFILE = "profile"


def _as_str_list(row_value: object) -> list[str]:
    """Cast a ``row[...]`` lookup to ``list[str]`` (WPS226 helper).

    Centralises the ``cast("list[str]", ...)`` call so the literal
    ``"list[str]"`` forward-reference appears only ONCE in the module.
    """
    return cast("list[str]", row_value)


def _join_or_dash(names: list[str]) -> str:
    """Join a list of names with commas, or ``-`` for empty/None."""
    if not names:
        return _DASH
    return ",".join(names)


def _live_install_refused(apply: bool, yes: bool) -> bool:
    """Return True when the run should refuse to write the LIVE install."""
    if not apply or yes:
        return False
    env = os.environ.get("HERMES_HOME")
    if env is None:
        return False
    return Path(env).resolve() == LIVE_HERMES_HOME.resolve()


def _select_profiles(
    all_profiles: list[ProfileInfo],
    profile: str | None,
) -> list[ProfileInfo]:
    """Filter all_profiles to the requested NAME (or return them all)."""
    if profile is None:
        return list(all_profiles)
    return [profile_info for profile_info in all_profiles if profile_info.name == profile]


def _empty_report(frozen_time: str | None) -> AuditReport:
    """Build the zero-profile empty report (timestamp pinned by frozen_time)."""
    return AuditReport(
        tool=TOOL_NAME,
        version=TOOL_VERSION,
        generated_at=_now_iso(frozen_time),
        profiles=[],
    )


def _echo_row_summary(row: dict[str, object]) -> None:
    """Echo the per-profile audit summary + diff in bilingual form."""
    click.echo(
        _bilingual(
            "profiles_msg_profile_audit",
            name=row["profile_name"],
            disabled=_join_or_dash(_as_str_list(row["current_disabled"])),
            installed=_join_or_dash(_as_str_list(row["current_installed"])),
        )
    )
    diff_row = cast("dict[str, object]", row["diff"])
    click.echo(
        _bilingual(
            "profiles_msg_diff",
            ad=_join_or_dash(_as_str_list(diff_row["added_disabled"])),
            rd=_join_or_dash(_as_str_list(diff_row["removed_disabled"])),
            ai=_join_or_dash(_as_str_list(diff_row["added_installed"])),
            ri=_join_or_dash(_as_str_list(diff_row["removed_installed"])),
        )
    )


def _write_json_report(report: AuditReport, json_path: Path) -> None:
    """Write the report JSON to json_path (creating parent dirs)."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes(report.to_json_bytes())
    click.echo(_bilingual("profiles_msg_json_written", path=str(json_path)))


def _audit_and_collect_row(
    profile_info: ProfileInfo,
    *,
    apply: bool,
    skip_install: bool,
    frozen_time: str | None,
) -> dict[str, object]:
    """Audit a single profile and backfill profile_name from ProfileInfo."""
    row = _audit_profile(
        profile_info.path,
        apply=apply,
        skip_install=skip_install,
        frozen_time=frozen_time,
        bilingual_fn=_bilingual,
    )
    # Backfill the profile_name from the ProfileInfo (in case
    # the path-based name was "hermes" by default).
    row["profile_name"] = profile_info.name
    _echo_row_summary(row)
    return row


# ---------------------------------------------------------------------------
# Programmatic entry point.
# ---------------------------------------------------------------------------


def _extract_audit_options(options: dict[str, object]) -> dict[str, object]:
    """Pull the recognized keyword options out of the raw options dict."""
    return {
        _KEY_APPLY: bool(options.get(_KEY_APPLY, False)),
        _KEY_JSON_PATH: options.get(_KEY_JSON_PATH),
        _KEY_FROZEN_TIME: options.get(_KEY_FROZEN_TIME),
        _KEY_SKIP_INSTALL: bool(options.get(_KEY_SKIP_INSTALL, False)),
        _KEY_YES: bool(options.get(_KEY_YES, False)),
        _KEY_PROFILE: options.get(_KEY_PROFILE),
    }


def _run_audit_phase(opts: dict[str, object]) -> AuditReport:
    """Drive the audit/flip after the live-install refusal gate."""
    apply = bool(opts[_KEY_APPLY])
    frozen_time: str | None = cast("str | None", opts[_KEY_FROZEN_TIME])
    skip_install = bool(opts[_KEY_SKIP_INSTALL])
    profile: str | None = cast("str | None", opts[_KEY_PROFILE])

    from hermes_cli.profiles import list_profiles

    click.echo(_bilingual("profiles_msg_scanning"))
    selected = _select_profiles(list_profiles(), profile)
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return _empty_report(frozen_time)

    mode_key = "profiles_msg_applying" if apply else "profiles_msg_audit_default"
    click.echo(_bilingual(mode_key))

    report = _empty_report(frozen_time)
    for profile_info in selected:
        row = _audit_and_collect_row(
            profile_info,
            apply=apply,
            skip_install=skip_install,
            frozen_time=frozen_time,
        )
        report.profiles.append(row)

    click.echo(_bilingual("profiles_msg_done", n=len(selected)))
    return report


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
    if _live_install_refused(bool(opts[_KEY_APPLY]), bool(opts[_KEY_YES])):
        click.echo(_bilingual("profiles_msg_refuse_no_yes"))
        sys.exit(5)

    report = _run_audit_phase(opts)

    json_path = opts[_KEY_JSON_PATH]
    if json_path is not None:
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
_build_help_text = _build_help_text  # noqa: F841 - re-export for tests
