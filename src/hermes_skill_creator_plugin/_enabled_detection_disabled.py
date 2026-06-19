"""Disabled-set builder for enabled-detection.

Extracted from :mod:`._enabled_detection_filter` to keep the parent
under wemake WPS202 (module members <= 7).

Provides ``disabled_set`` (union of global disabled + per-platform
disabled) and ``drop_disabled`` (set difference).
"""

from __future__ import annotations

from typing import Any

from hermes_skill_creator_plugin._enabled_detection_parse import (
    _DISABLED_IF_PLATFORM_KEY,
    _DISABLED_KEY,
    _SKILLS_KEY,
    add_list_entries,
)


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


def drop_disabled(installed: set[str], disabled: set[str]) -> set[str]:
    """Return the subset of ``installed`` that is not in ``disabled``."""
    return {name for name in installed if name not in disabled}


__all__ = [
    "disabled_set",
    "drop_disabled",
]
