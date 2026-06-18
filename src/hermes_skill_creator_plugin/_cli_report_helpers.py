"""src/hermes_skill_creator_plugin/_cli_report_helpers.py

Internal helpers for the reporter CLI (paths, profiles, descriptions).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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


def emit_tokenizer_warning(_msg: str) -> None:
    """Bilingual warning callback for tokenizer. See cli_report."""
    from .i18n import messages_en as EN

    import click

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