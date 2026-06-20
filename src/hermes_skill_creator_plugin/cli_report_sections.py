"""Section-build helpers for the reporter CLI.

Split from ``cli_report`` (WPS202 module surface budget). The
per-profile section builder + the :class:`ProfileBuildContext` bundle
live here so the dispatcher stays under the module surface cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import click

from hermes_skill_creator_plugin import cli_report_imports as _imps
from hermes_skill_creator_plugin._enabled_detection import get_enabled_skills
from hermes_skill_creator_plugin.i18n import messages_en as EN

_helpers = _imps._helpers
_rows = _imps._rows
estimate_tokens = _imps.estimate_tokens
sort_rows = _imps.sort_rows
EnabledDetectionUnavailable = _rows.EnabledDetectionUnavailable
_build_rows_for_profile = _rows.build_rows_for_profile
FORMAT_TEXT = _helpers.FORMAT_TEXT
ProfileSection = _imps.ProfileSection


@dataclass(frozen=True)
class ProfileBuildContext:
    """Per-profile build inputs (everything except the profile path)."""

    fmt: str
    sort: str
    platform: str | None
    curator: Any | None


def _build_profile_sections(
    profile_paths: list[Path],
    *,
    fmt: str,
    sort: str,
    platform: str | None,
    curator: Any | None,
) -> tuple[list[str], list[ProfileSection], int | None]:
    """Build text/json sections for all profiles. Error code or None."""
    text_sections: list[str] = []
    json_sections: list[ProfileSection] = []
    ctx = ProfileBuildContext(
        fmt=fmt,
        sort=sort,
        platform=platform,
        curator=curator,
    )
    for prof in profile_paths:
        rc = _build_one_profile_section(
            prof,
            ctx=ctx,
            text_sections=text_sections,
            json_sections=json_sections,
        )
        if rc is not None:
            return text_sections, json_sections, rc
    return text_sections, json_sections, None


def _build_one_profile_section(
    prof: Path,
    *,
    ctx: ProfileBuildContext,
    text_sections: list[str],
    json_sections: list[ProfileSection],
) -> int | None:
    """Append one profile's section; return 6 on detection error, else None."""
    try:
        rows, total = _build_rows_for_profile(
            prof,
            platform=ctx.platform,
            curator=ctx.curator,
            estimate_tokens_fn=estimate_tokens,
            enabled_skills_fn=get_enabled_skills,
        )
    except EnabledDetectionUnavailable:
        click.echo(EN.report_enabled_detection_unavailable, err=True)
        return 6
    rows = sort_rows(rows, ctx.sort)
    section = _helpers.make_section(ctx.fmt, prof.name, rows, total)
    if ctx.fmt == FORMAT_TEXT:
        text_sections.append(cast("str", section))
    else:
        json_sections.append(cast("ProfileSection", section))
    return None
