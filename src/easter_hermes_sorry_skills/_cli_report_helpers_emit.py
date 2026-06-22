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
    ProfileSection,
    SkillRow,
    format_json,
    format_text,
)
from easter_hermes_sorry_skills.i18n import messages_en as EN


def resolve_json_path(fmt: str, json_path: Path | None) -> Path | None:
    """Return default json_path when fmt=json and not given."""
    if json_path is None and fmt == FORMAT_JSON:
        return Path(DEFAULT_JSON_NAME)
    return json_path


def make_section(
    fmt: str,
    name: str,
    rows: list[SkillRow],
    total: int,
) -> str | ProfileSection:
    """Build a single text section string or json ProfileSection."""
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
