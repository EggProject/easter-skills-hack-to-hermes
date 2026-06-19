"""src/hermes_skill_creator_plugin/_enabled_detection_filter.py

Platform / conditional-exclusion filtering for enabled-detection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._enabled_detection_parse import (
    _DISABLED_IF_PLATFORM_KEY,
    _DISABLED_KEY,
    _PLATFORMS_KEY,
    _SKILLS_KEY,
    add_list_entries,
    parse_frontmatter,
)


_DISABLE_IF_KEY = "disable_if"
_PLATFORM_KEY = "platform"
_DISABLE_IF_PLATFORM_PRESENT_KEY = "disable_if_platform_present"
_SKILLS_DIR_NAME = "skills"
_SKILL_MD_NAME = "SKILL.md"


def disabled_set(config: dict[str, Any], platform: str | None) -> set[str]:
    """Return the union of the disabled set and the platform-scoped set."""
    skills_section = config.get(_SKILLS_KEY, {})
    if not isinstance(skills_section, dict):
        skills_section = {}
    out: set[str] = set()
    add_list_entries(skills_section.get(_DISABLED_KEY, []), out)
    plat_map = skills_section.get(_DISABLED_IF_PLATFORM_KEY, {})
    if platform is not None and isinstance(plat_map, dict):
        add_list_entries(plat_map.get(platform, []) or [], out)
    return out


def list_blocks(plat_value: Any) -> bool:
    """Return True when the list-shape platforms entry blocks the host."""
    if isinstance(plat_value, (list, tuple, set)):
        return any(bool(entry) for entry in plat_value)
    return False


def plat_value_blocks(plat_value: Any) -> bool:
    """Return True iff a single ``platforms:`` value blocks the host."""
    if isinstance(plat_value, str):
        return bool(plat_value)
    if list_blocks(plat_value):
        return True
    if isinstance(plat_value, dict):
        return any(bool(v) for v in plat_value.values()) if plat_value else False
    if plat_value is None:
        return False
    return bool(plat_value)


def platform_blocked(
    frontmatter_dict: dict[str, Any],
    platform: str | None,
) -> bool:
    """Return True when the skill's ``platforms:`` section blocks ``platform``."""
    if platform is None:
        return False
    plats = frontmatter_dict.get(_PLATFORMS_KEY)
    if isinstance(plats, list):
        for entry in plats:
            if not isinstance(entry, dict):
                continue
            blocked = entry.get(_DISABLE_IF_PLATFORM_PRESENT_KEY, [])
            if isinstance(blocked, list) and platform in blocked:
                return True
        return False
    if isinstance(plats, dict):
        return plat_value_blocks(plats.get(platform))
    return False


def platform_disables(platforms: Any, platform: str) -> bool:
    """Return True if ``platforms`` (per-skill mapping) blocks ``platform``."""
    return platform_blocked({_PLATFORMS_KEY: platforms}, platform)


def conditional_excluded(
    frontmatter_dict: dict[str, Any],
    platform: str | None,
) -> bool:
    """Return True when the skill declares a per-skill ``disable_if:`` rule."""
    rule = frontmatter_dict.get(_DISABLE_IF_KEY)
    if not isinstance(rule, dict):
        return False
    if platform is None:
        return False
    plats = rule.get(_PLATFORM_KEY, [])
    return isinstance(plats, list) and platform in plats


def find_skill_md(skills_dir: Path, name: str) -> Path | None:
    """Locate the ``SKILL.md`` for a skill by NAME."""
    if not skills_dir.is_dir():
        return None
    direct = skills_dir / name / _SKILL_MD_NAME
    if direct.is_file():
        return direct
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / _SKILL_MD_NAME
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
    skills_dir = profile_path / _SKILLS_DIR_NAME
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
    skills_dir = profile_path / _SKILLS_DIR_NAME
    out: set[str] = set()
    for name in installed_names:
        keep_if_not_excluded(
            name,
            skills_dir=skills_dir,
            platform=platform,
            out=out,
        )
    return out


def drop_disabled(installed: set[str], disabled: set[str]) -> set[str]:
    """Return the subset of ``installed`` that is not in ``disabled``."""
    return {name for name in installed if name not in disabled}


__all__ = [
    "disabled_set",
    "platform_blocked",
    "conditional_excluded",
    "platform_disables",
    "find_skill_md",
    "apply_platform_filter",
    "apply_conditional_exclusions",
    "drop_disabled",
]
