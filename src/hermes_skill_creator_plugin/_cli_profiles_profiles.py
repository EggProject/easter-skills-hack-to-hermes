"""Profile selection + empty report helpers for the ``cli_profiles`` CLI.

Moved out of ``_cli_profiles_pipeline`` to keep that module under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

import datetime as _datetime_mod
from pathlib import Path

from hermes_cli.profiles import ProfileInfo

from hermes_skill_creator_plugin import _cli_profiles_bindings as _bindings

AuditReport = _bindings.AuditReport

TOOL_NAME = "hermes-skill-creator-profiles"
TOOL_VERSION = "0.1.0"
LIVE_HERMES_HOME = Path.home() / ".hermes"


def _now_iso(frozen_time: str | None) -> str:
    """Return the report timestamp (stable when ``frozen_time`` is set)."""
    if frozen_time is not None:
        return frozen_time
    return _datetime_mod.datetime.now(_datetime_mod.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_report(frozen_time: str | None) -> AuditReport:
    """Build the zero-profile empty report (timestamp pinned by frozen_time)."""
    return AuditReport(
        tool=TOOL_NAME,
        version=TOOL_VERSION,
        generated_at=_now_iso(frozen_time),
        profiles=[],
    )


def _select_profiles(
    all_profiles: list[ProfileInfo],
    profile: str | None,
) -> list[ProfileInfo]:
    """Filter all_profiles to the requested NAME (or return them all)."""
    if profile is None:
        return list(all_profiles)
    return [profile_info for profile_info in all_profiles if profile_info.name == profile]


def _list_all_profiles() -> list[ProfileInfo]:
    from hermes_cli.profiles import list_profiles as _list_profiles

    return _list_profiles()
