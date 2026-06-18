"""src/hermes_skill_creator_plugin/_cli_report_helpers.py

Internal helpers for the reporter CLI (paths, profiles, descriptions).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from ._reporter import ProfileSection, format_json, format_text
from .i18n import messages_en as EN


REJECTED_FLAGS = {
    "--apply": "apply",
    "--emit-migration-note": "emit-migration-note",
    "--write-report": "write-report",
}

HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"

EMPTY_USAGE: dict[str, Any] = {
    "use_count": None,
    "view_count": None,
    "patch_count": None,
    "last_used_at": None,
    "last_viewed_at": None,
    "last_patched_at": None,
}

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SORT_TOKENS = "tokens"
SORT_KEYS = (SORT_TOKENS, "use_count", "last_used_at")
FORMAT_KEYS = (FORMAT_TEXT, FORMAT_JSON)
TOOL_NAME = "hermes-skill-creator-report"
TOOL_VERSION = "0.1.0"
DEFAULT_JSON_NAME = "./skill-report.json"


def emit_tokenizer_warning(_msg: str) -> None:
    """Bilingual warning callback for tokenizer. See cli_report."""
    click.echo(EN.report_tokenizer_unavailable, err=True)


def resolve_hermes_home() -> Path:
    """Resolve HERMES_HOME from env, default to ~/.hermes."""
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path("~/.hermes").expanduser()


def load_curator(hermes_home: Path) -> Any | None:
    """Best-effort: load tools.skill_usage. Return None when unavailable."""
    try:
        import tools.skill_usage as usage_mod
    except Exception:
        return None
    if not hasattr(usage_mod, "usage_report"):
        return None
    return usage_mod


def resolve_profiles(hermes_home: Path, profile_arg: str | None) -> list[Path]:
    """Return the list of profile roots to report on."""
    if profile_arg:
        return [hermes_home / profile_arg]
    out: list[Path] = [hermes_home / "hermes"]
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.is_dir():
        for child in sorted(profiles_dir.iterdir()):
            if child.is_dir():
                out.append(child)
    return out


def load_skill_description(skills_dir: Path, skill_name: str) -> str:
    """Read the full description from <skills_dir>/<skill_name>/SKILL.md."""
    skill_md = skills_dir / skill_name / "SKILL.md"
    if not skill_md.is_file():
        return f"<description unavailable for {skill_name}>"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return f"<description unavailable for {skill_name}>"
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            frontmatter = text[3:end]
            body = text[end + 4 :].strip()
            for line in frontmatter.splitlines():
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip().strip("'\"")
            return body.split("\n\n", 1)[0] if body else text.strip()
    return text.strip()


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
        for prefix, key in REJECTED_FLAGS.items():
            with_eq = prefix + sep
            if arg == prefix or arg.startswith(with_eq):
                from ._cli_report_ui import reject_flag as _reject

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
    fmt: str, name: str, rows, total: int,
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