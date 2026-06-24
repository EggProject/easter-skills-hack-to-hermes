"""Render / emit / path-resolve helpers for the reporter CLI.

Extracted from ``_cli_report_helpers.py`` to keep that module under
wemake WPS202 (≤7 module members). These helpers build text / json
output sections and write them to disk / stdout.
"""

from __future__ import annotations

from pathlib import Path

import click

from easter_hermes_sorry_skills._cli_report_helpers_consts import (
    DEFAULT_JSON_NAME,
    FORMAT_JSON,
    FORMAT_TEXT,
    TOOL_NAME,
    TOOL_VERSION,
)
from easter_hermes_sorry_skills._reporter import (
    TEXT_COLUMNS,
    ProfileSection,
    SkillRow,
    format_json,
    format_text,
)
from easter_hermes_sorry_skills._reporter_format import _format_value_for_text
from easter_hermes_sorry_skills.i18n import messages_en as EN


def resolve_json_path(fmt: str, json_path: Path | None) -> Path | None:
    """Return default json_path when fmt=json and not given."""
    if json_path is None and fmt == FORMAT_JSON:
        return Path(DEFAULT_JSON_NAME)
    return json_path


def _emit_verbose_cell(
    profile: str,
    section: str,
    column: str,
    cell_value: object,
) -> None:
    """Emit a per-cell ``[verbose]`` line on stderr."""
    click.echo(
        f"[verbose] profile={profile} section={section} cell={column}={cell_value}",
        err=True,
    )


def _emit_verbose_section(
    rows: list[SkillRow],
    *,
    profile: str,
    section: str,
) -> None:
    """Emit one ``[verbose] cell=...=value`` line per (row, column)."""
    for row in rows:
        for column in TEXT_COLUMNS:
            _emit_verbose_cell(profile, section, column, _format_value_for_text(row, column))


def make_section(
    fmt: str,
    name: str,
    rows: list[SkillRow],
    total: int,
    *,
    verbose: bool = False,
) -> str | ProfileSection:
    """Build a single text section string or json ProfileSection."""
    if verbose:
        _emit_verbose_section(rows, profile=name, section=name)
    if fmt == FORMAT_TEXT:
        return format_text(name, rows, total_tokens=total)
    return ProfileSection(
        profile_name=name,
        rows=rows,
        total_tokens=total,
    )


def render_output(
    fmt: str,
    text_sections: list[str],
    json_sections: list[ProfileSection],
    generated_at: str,
) -> str:
    """Compose final output string for the requested format."""
    if fmt == FORMAT_TEXT:
        return "\n\n".join(text_sections)
    return format_json(
        tool=TOOL_NAME,
        version=TOOL_VERSION,
        generated_at=generated_at,
        sections=json_sections,
    )


def emit_output(fmt: str, output: str, json_path: Path | None) -> None:
    """Write or print the final output."""
    if fmt == FORMAT_JSON:
        assert json_path is not None
        json_path.write_text(output, encoding="utf-8")
        click.echo(EN.report_opt_json)
    else:
        click.echo(output)
