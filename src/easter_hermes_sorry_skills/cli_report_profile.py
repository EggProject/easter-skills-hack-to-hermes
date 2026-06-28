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

from easter_hermes_sorry_skills import cli_report as _cli_report_mod
from easter_hermes_sorry_skills import cli_report_imports as _imps
from easter_hermes_sorry_skills._cli_report_helpers_emit import _VerboseEmit
from easter_hermes_sorry_skills._i18n_pick import pick

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
    verbose: bool


@dataclass(frozen=True)
class _SectionSinks:
    """Mutable text/json section sinks accumulated across profile iterations."""

    text_sections: list[str]
    json_sections: list[Any]


def build_profile_sections(
    profile_paths: list[Path],
    ctx: ProfileBuildContext,
    lang: str = "en",
) -> tuple[list[str], list[Any], int | None]:
    """Build text/json sections for all profiles. Error code or None."""
    sinks = _SectionSinks(text_sections=[], json_sections=[])
    for prof in profile_paths:
        rc = build_one_profile_section(
            prof,
            ctx=ctx,
            sinks=sinks,
            lang=lang,
        )
        if rc is not None:
            return sinks.text_sections, sinks.json_sections, rc
    return sinks.text_sections, sinks.json_sections, None


def build_one_profile_section(
    prof: Path,
    *,
    ctx: ProfileBuildContext,
    sinks: _SectionSinks,
    lang: str = "en",
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
        click.echo(pick(lang).report_enabled_detection_unavailable, err=True)
        return _ENABLED_DETECTION_RC
    rows = _imps.sort_rows(rows, ctx.sort)
    section = _imps.make_section(
        ctx.fmt,
        prof.name,
        rows,
        total,
        verbose=_VerboseEmit(enabled=ctx.verbose, lang=lang),
    )
    if ctx.verbose:
        skipped_empty = sum(1 for row in rows if row.tokens == 0)
        click.echo(
            f"[verbose] section={prof.name} rows={len(rows)} skipped_empty={skipped_empty}",
            err=True,
        )
    if ctx.fmt == _imps.FORMAT_TEXT:
        _append_text_section(sinks.text_sections, section)
    else:
        _append_json_section(sinks.json_sections, section)
    return None


def _append_text_section(sinks_list: list[str], section: str | object) -> None:
    """Append ``section`` to the text-section list after narrowing its type."""
    if isinstance(section, str):
        sinks_list.append(section)
        return
    # ``make_section`` returns ``str | ProfileSection``; the
    # ``_imps.FORMAT_TEXT`` branch guarantees a ``str`` here, so this
    # branch is unreachable at runtime but keeps mypy strict.
    raise TypeError("text-format section must be str")


def _append_json_section(sinks_list: list[Any], section: str | object) -> None:
    """Append ``section`` to the json-section list after narrowing its type."""
    if isinstance(section, str):
        raise TypeError("json-format section must be ProfileSection")
    sinks_list.append(section)
