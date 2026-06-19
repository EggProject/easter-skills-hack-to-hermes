"""Skill-MD resolution + per-skill filter helpers for enabled-detection.

Extracted from :mod:`._enabled_detection_filter` to keep the parent
under wemake WPS202 (module members <= 7).

Provides the skill-discovery primitives: ``find_skill_md``,
``keep_if_not_platform_blocked``, ``keep_if_not_excluded``,
``apply_platform_filter``, ``apply_conditional_exclusions``.
"""

from __future__ import annotations

from pathlib import Path

from hermes_skill_creator_plugin._enabled_detection_parse import (
    parse_frontmatter,
)
from hermes_skill_creator_plugin._enabled_detection_platform import (
    _DISABLE_IF_KEY,
    _PLATFORM_KEY,
    conditional_excluded,
    platform_blocked,
)

SKILLS_DIR_NAME = "skills"
SKILL_MD_NAME = "SKILL.md"


def find_skill_md(skills_dir: Path, name: str) -> Path | None:
    """Locate the ``SKILL.md`` for a skill by NAME."""
    if not skills_dir.is_dir():
        return None
    direct = skills_dir / name / SKILL_MD_NAME
    if direct.is_file():
        return direct
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / SKILL_MD_NAME
        if not skill_md.is_file():
            continue
        meta = parse_frontmatter(skill_md)
        if str(meta.get("name", child.name)) == name:
            return skill_md
    return None


def keep_if_not_platform_blocked(
    name: str,
    *,
    skills_dir: Path,
    platform: str | None,
    out: set[str],
) -> None:
    """Add ``name`` to ``out`` unless the skill's platforms rule blocks it."""
    skill_md = find_skill_md(skills_dir, name)
    if skill_md is None:
        out.add(name)
        return
    meta = parse_frontmatter(skill_md)
    if not meta:
        out.add(name)
        return
    if not platform_blocked(meta, platform):
        out.add(name)


def apply_platform_filter(
    installed_names: set[str],
    profile_path: Path,
    platform: str | None,
) -> set[str]:
    """Return the subset of ``installed_names`` NOT disabled by the platform."""
    if platform is None:
        return set(installed_names)
    skills_dir = profile_path / SKILLS_DIR_NAME
    out: set[str] = set()
    for name in installed_names:
        keep_if_not_platform_blocked(
            name,
            skills_dir=skills_dir,
            platform=platform,
            out=out,
        )
    return out


def keep_if_not_excluded(
    name: str,
    *,
    skills_dir: Path,
    platform: str | None,
    out: set[str],
) -> None:
    """Add ``name`` to ``out`` unless the skill's disable_if rule excludes it."""
    skill_md = find_skill_md(skills_dir, name)
    if skill_md is None:
        out.add(name)
        return
    meta = parse_frontmatter(skill_md)
    if not meta:
        out.add(name)
        return
    rule = meta.get(_DISABLE_IF_KEY)
    has_platform_rule = isinstance(rule, dict) and _PLATFORM_KEY in rule
    if has_platform_rule:
        if not conditional_excluded(meta, platform):
            out.add(name)
        return
    if rule is None or rule == "":
        out.add(name)


def apply_conditional_exclusions(
    installed_names: set[str],
    profile_path: Path,
    platform: str | None,
) -> set[str]:
    """Return the subset of ``installed_names`` not excluded by per-skill rules."""
    skills_dir = profile_path / SKILLS_DIR_NAME
    out: set[str] = set()
    for name in installed_names:
        keep_if_not_excluded(
            name,
            skills_dir=skills_dir,
            platform=platform,
            out=out,
        )
    return out


__all__ = [
    "find_skill_md",
    "apply_platform_filter",
    "apply_conditional_exclusions",
]