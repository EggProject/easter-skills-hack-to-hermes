"""Path resolution + SKILL.md helpers for the reporter CLI.

Split from ``_cli_report_helpers`` to keep module surface (WPS202)
and cognitive complexity (WPS231) within toolchain budgets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

UNAVAILABLE_DESC_FMT = "<description unavailable for {name}>"


def resolve_hermes_home() -> Path:
    """Resolve HERMES_HOME from env, default to ~/.hermes."""
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path("~/.hermes").expanduser()


def load_curator(hermes_home: Path) -> Any | None:
    """Best-effort: load tools.skill_usage. Return None when unavailable."""
    try:
        from tools import skill_usage as usage_mod
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
        return UNAVAILABLE_DESC_FMT.format(name=skill_name)
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return UNAVAILABLE_DESC_FMT.format(name=skill_name)
    if text.startswith("---"):
        return _strip_frontmatter(text, skill_name)
    return text.strip()


def _strip_frontmatter(text: str, skill_name: str) -> str:
    """Extract the description from a SKILL.md frontmatter block."""
    end = text.find("\n---", 3)
    if end <= 0:
        return text.strip()
    frontmatter = text[3:end]
    body = text[end + 4 :].strip()
    desc = _description_from_frontmatter(frontmatter)
    if desc is not None:
        return desc
    return body.split("\n\n", 1)[0] if body else UNAVAILABLE_DESC_FMT.format(name=skill_name)


def _description_from_frontmatter(frontmatter: str) -> str | None:
    """Return the description value from a frontmatter block, else ``None``."""
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None
