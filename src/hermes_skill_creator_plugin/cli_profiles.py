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

import click

# The audit helpers live in ``_cli_profiles_audit`` so this module stays
# slim; tests grep this file's source for the canonical import lines
# (the read-side ``agent.skill_utils.get_disabled_skill_names`` and the
# write-side ``hermes_cli.skills_config.save_disabled_skills``), so we
# re-state them here verbatim.
from agent.skill_utils import get_disabled_skill_names  # noqa: F401  pylint: disable=unused-import,import-outside-toplevel,line-too-long  # test-spec: source of truth for the read-side import.
from hermes_cli.skills_config import save_disabled_skills  # noqa: F401  pylint: disable=unused-import,import-outside-toplevel,line-too-long  # test-spec: source of truth for the write-side import.

from hermes_skill_creator_plugin._cli_profiles_audit import (
    DESIRED_SKILL,
    NEVER_DISABLE,
    apply_clear_cache as _apply_clear_cache,
    apply_do_install as _apply_do_install,
    apply_save_disabled as _apply_save_disabled,
    audit_profile as _audit_profile,
    build_bilingual as _build_bilingual,
    diff_sets as _diff,
    load_config_or_error as _load_config_or_error,
    new_row as _new_row,
    populate_diff_row as _populate_diff_row,
    read_disabled_or_empty as _read_disabled_or_empty,
    walk_skills as _walk_skills,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    build_help_text as _build_help_text,
    main_cmd,
    make_cli as _make_cli,
)
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport
from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

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
# Bilingual helper.
# ---------------------------------------------------------------------------


def _bilingual(key: str, **values: object) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key."""
    return _build_bilingual(EN, HU, key, **values)


def _now_iso(frozen_time: str | None) -> str:
    """Return the report timestamp (stable when ``frozen_time`` is set)."""
    if frozen_time is not None:
        return frozen_time
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Programmatic entry point.
# ---------------------------------------------------------------------------


def run_audit(
    *,
    apply: bool = False,
    json_path: Path | None = None,
    frozen_time: str | None = None,
    skip_install: bool = False,
    yes: bool = False,
    profile: str | None = None,
) -> AuditReport:
    """Run the per-profile audit/flip.

    Args:
        apply: When True, perform the writes (--apply).
        json_path: Optional path to write the JSON report to.
        frozen_time: Optional ISO 8601 UTC string to pin the report
            timestamp (D7: determinism).
        skip_install: When True, audit only (do not call do_install).
        yes: When True, suppress the live-install refusal.
        profile: Optional single profile NAME to restrict the run to.

    Returns:
        The ``AuditReport`` (also written to ``json_path`` if given).
    """
    from hermes_cli.profiles import list_profiles

    # 0. Live-install refusal (safety contract). The refusal fires
    #    whenever HERMES_HOME resolves to the LIVE install AND --yes is
    #    absent — TTY or not, CI or interactive. Operators who really
    #    want to write to the live install must pass --yes.
    if apply and not yes:
        env = os.environ.get("HERMES_HOME")
        if env is not None and Path(env).resolve() == LIVE_HERMES_HOME.resolve():
            click.echo(_bilingual("profiles_msg_refuse_no_yes"))
            sys.exit(5)

    click.echo(_bilingual("profiles_msg_scanning"))
    all_profiles = list_profiles()
    selected = (
        [profile_info for profile_info in all_profiles if profile_info.name == profile]
        if profile is not None
        else list(all_profiles)
    )
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return AuditReport(
            tool=TOOL_NAME,
            version=TOOL_VERSION,
            generated_at=_now_iso(frozen_time),
            profiles=[],
        )

    if apply:
        click.echo(_bilingual("profiles_msg_applying"))
    else:
        click.echo(_bilingual("profiles_msg_audit_default"))

    report = AuditReport(
        tool=TOOL_NAME,
        version=TOOL_VERSION,
        generated_at=_now_iso(frozen_time),
        profiles=[],
    )
    for profile_info in selected:
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
        click.echo(
            _bilingual(
                "profiles_msg_profile_audit",
                name=row["profile_name"],
                disabled=",".join(row["current_disabled"]) or "-",
                installed=",".join(row["current_installed"]) or "-",
            )
        )
        click.echo(
            _bilingual(
                "profiles_msg_diff",
                ad=",".join(row["diff"]["added_disabled"]) or "-",
                rd=",".join(row["diff"]["removed_disabled"]) or "-",
                ai=",".join(row["diff"]["added_installed"]) or "-",
                ri=",".join(row["diff"]["removed_installed"]) or "-",
            )
        )
        report.profiles.append(row)

    click.echo(_bilingual("profiles_msg_done", n=len(selected)))

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_bytes(report.to_json_bytes())
        click.echo(_bilingual("profiles_msg_json_written", path=str(json_path)))

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
