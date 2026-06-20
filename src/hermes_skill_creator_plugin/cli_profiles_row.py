"""Per-row + presentation helpers for the cli_profiles script.

Split from ``cli_profiles`` (WPS202 module surface budget). The bilingual
echo, JSON write, audit-and-collect glue, and the empty-report builder
live here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import click

from hermes_skill_creator_plugin._cli_profiles_audit import (
    audit_profile as _audit_profile,
)
from hermes_skill_creator_plugin._cli_profiles_bilingual import (
    build_bilingual as _build_bilingual,
)
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport

TOOL_NAME = "hermes-skill-creator-profiles"
TOOL_VERSION = "0.1.0"
_DASH = "-"


def _bilingual(key: str, **format_kwargs: object) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key."""
    from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
    from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

    return _build_bilingual(EN, HU, key, **format_kwargs)


def _now_iso(frozen_time: str | None) -> str:
    """Return the report timestamp (stable when ``frozen_time`` is set)."""
    if frozen_time is not None:
        return frozen_time
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _join_or_dash(names: list[str]) -> str:
    """Join a list of names with commas, or ``-`` for empty/None."""
    if not names:
        return _DASH
    return ",".join(names)


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
            disabled=_join_or_dash(cast("list[str]", row["current_disabled"])),
            installed=_join_or_dash(cast("list[str]", row["current_installed"])),
        )
    )
    diff_row = cast("dict[str, object]", row["diff"])
    click.echo(
        _bilingual(
            "profiles_msg_diff",
            ad=_join_or_dash(cast("list[str]", diff_row["added_disabled"])),
            rd=_join_or_dash(cast("list[str]", diff_row["removed_disabled"])),
            ai=_join_or_dash(cast("list[str]", diff_row["added_installed"])),
            ri=_join_or_dash(cast("list[str]", diff_row["removed_installed"])),
        )
    )


def _write_json_report(report: AuditReport, json_path: Path) -> None:
    """Write the report JSON to json_path (creating parent dirs)."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes(report.to_json_bytes())
    click.echo(_bilingual("profiles_msg_json_written", path=str(json_path)))


def _audit_and_collect_row(
    profile_info: Any,
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
