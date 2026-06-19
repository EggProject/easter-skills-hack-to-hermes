"""Constants + emit/output helpers for the reporter CLI.

Path resolution + SKILL.md helpers live in ``_cli_report_helpers_paths``
(split to keep module surface WPS202-clean).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin._reporter import ProfileSection, format_json, format_text
from hermes_skill_creator_plugin.i18n import messages_en as EN


REJECTED_FLAGS = {
    "--apply": "apply",
    "--emit-migration-note": "emit-migration-note",
    "--write-report": "write-report",
}

HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"

EMPTY_USAGE: dict[str, Any | None] = {
    "use_count": None,
    "view_count": None,
    "patch_count": None,
    "last_used_at": None,
    "last_viewed_at": None,
    "last_patched_at": None,
}
PERSISTED_KEY = "_persisted"

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SORT_TOKENS = "tokens"
SORT_KEYS: tuple[str, ...] = (SORT_TOKENS, "use_count", "last_used_at")
FORMAT_KEYS: tuple[str, ...] = (FORMAT_TEXT, FORMAT_JSON)
TOOL_NAME = "hermes-skill-creator-report"
TOOL_VERSION = "0.1.0"
DEFAULT_JSON_NAME = "./skill-report.json"


def emit_tokenizer_warning(_msg: str) -> None:
    """Bilingual warning callback for tokenizer. See cli_report."""
    click.echo(EN.report_tokenizer_unavailable, err=True)


def now_iso() -> str:
    """Return an ISO 8601 UTC timestamp. Honors frozen-time env var."""
    frozen = os.environ.get(
        "HERMES_SKILL_CREATOR_FROZEN_TIME", ""
    ).strip()
    if frozen:
        return frozen
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def reject_unwanted_flags(argv: list[str]) -> int | None:
    """Return reject_flag code if argv contains a rejected flag, else None."""
    sep = "="
    for arg in argv:
        reject_code = _reject_for_arg(arg, sep)
        if reject_code is not None:
            return reject_code
    return None


def _reject_for_arg(arg: str, sep: str) -> int | None:
    """Return the reject flag code for ``arg`` when it matches a rejected flag."""
    for prefix, key in REJECTED_FLAGS.items():
        with_eq = prefix + sep
        if arg == prefix or arg.startswith(with_eq):
            from hermes_skill_creator_plugin._cli_report_ui import (
                reject_flag as _reject,
            )

            return _reject(key)
    return None


def validate_sort_and_fmt(sort: str, fmt: str) -> int | None:
    """Return 2 when sort/fmt invalid, else None."""
    if sort not in SORT_KEYS:
        click.echo(EN.report_opt_sort, err=True)
        return 2
    if fmt not in FORMAT_KEYS:
        click.echo(EN.report_opt_format, err=True)
        return 2
    return None


def resolve_json_path(fmt: str, json_path: Path | None) -> Path | None:
    """Return default json_path when fmt=json and not given."""
    if json_path is None and fmt == FORMAT_JSON:
        return Path(DEFAULT_JSON_NAME)
    return json_path


def make_section(
    fmt: str, name: str, rows: list, total: int,
) -> str | ProfileSection:
    """Build a single text section string or json ProfileSection."""
    if fmt == FORMAT_TEXT:
        return format_text(name, rows, total_tokens=total)
    return ProfileSection(
        profile_name=name, rows=rows, total_tokens=total,
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
