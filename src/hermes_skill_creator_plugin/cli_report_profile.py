"""Profile section building for the reporter CLI.

Extracted from ``cli_report.py`` to keep that module under wemake WPS202
(≤7 module members). Holds the per-profile context struct and the
section-builders that walk ``profile_paths``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin import cli_report as _cli_report_mod
from hermes_skill_creator_plugin import cli_report_imports as _imps
from hermes_skill_creator_plugin.i18n import messages_en as EN

_ENABLED_DETECTION_RC = 6

# Lookup helper — reads through ``cli_report`` at call time so
# ``monkeypatch.setattr(cli_report, "get_enabled_skills", ...)`` reaches
# the same callable used here.
def _resolve_get_enabled_skills() -> Any:
    return _cli_report_mod.get_enabled_skills


@dataclass(frozen=True)
class ProfileBuildContext:
    """Per-profile build inputs (everything except the profile path)."""

    fmt: str
    sort: str
    platform: str | None
    curator: Any | None


def build_profile_sections(
    profile_paths: list[Path],
    *,
    fmt: str,
    sort: str,
    platform: str | None,
    curator: Any | None,
    make_section_fn: Any,
) -> tuple[list[str], list[Any], int | None]:
    """Build text/json sections for all profiles. Error code or None."""
    text_sections: list[str] = []
    json_sections: list[Any] = []
    ctx = ProfileBuildContext(
        fmt=fmt,
        sort=sort,
        platform=platform,
        curator=curator,
    )
    for prof in profile_paths:
        rc = build_one_profile_section(
            prof,
            ctx=ctx,
            text_sections=text_sections,
            json_sections=json_sections,
            make_section_fn=make_section_fn,
        )
        if rc is not None:
            return text_sections, json_sections, rc
    return text_sections, json_sections, None


def build_one_profile_section(
    prof: Path,
    *,
    ctx: ProfileBuildContext,
    text_sections: list[str],
    json_sections: list[Any],
    make_section_fn: Any,
) -> int | None:
    """Append one profile's section; return 6 on detection error, else None."""
    try:
        rows, total = _imps._build_rows_for_profile(
            prof,
            platform=ctx.platform,
            curator=ctx.curator,
            estimate_tokens_fn=_cli_report_mod.estimate_tokens,
            enabled_skills_fn=_resolve_get_enabled_skills(),
        )
    except _imps.EnabledDetectionUnavailable:
        click.echo(EN.report_enabled_detection_unavailable, err=True)
        return _ENABLED_DETECTION_RC
    rows = _imps.sort_rows(rows, ctx.sort)
    section = make_section_fn(ctx.fmt, prof.name, rows, total)
    if ctx.fmt == _imps.FORMAT_TEXT:
        text_sections.append(section)
    else:
        json_sections.append(section)
    return None
