"""Platform / conditional-exclusion filtering for enabled-detection.

Extracted from :mod:`._enabled_detection_filter` to keep the parent
under wemake WPS202 (module members <= 7).

Provides the platform-blocking primitives: ``platform_blocked``,
``plat_value_blocks``, ``platform_disables``, and
``conditional_excluded``.
"""

from __future__ import annotations

from typing import Any

from hermes_skill_creator_plugin._enabled_detection_parse import (
    _PLATFORMS_KEY,
)

_DISABLE_IF_KEY = "disable_if"
_PLATFORM_KEY = "platform"
_DISABLE_IF_PLATFORM_PRESENT_KEY = "disable_if_platform_present"


def list_blocks(plat_value: Any) -> bool:
    """Return True when the list-shape platforms entry blocks the host."""
    if isinstance(plat_value, (list, tuple, set)):
        return any(bool(entry) for entry in plat_value)
    return False


def _dict_blocks(plat_value: dict[Any, Any]) -> bool:
    """Return True iff any value in the dict-shape platforms entry blocks."""
    if not plat_value:
        return False
    return any(bool(entry_value) for entry_value in plat_value.values())


def plat_value_blocks(plat_value: Any) -> bool:
    """Return True iff a single ``platforms:`` value blocks the host."""
    if isinstance(plat_value, str):
        return bool(plat_value)
    if list_blocks(plat_value):
        return True
    if isinstance(plat_value, dict):
        return _dict_blocks(plat_value)
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
        return _list_blocks_host(plats, platform)
    if isinstance(plats, dict):
        return plat_value_blocks(plats.get(platform))
    return False


def _list_blocks_host(plats: list[Any], platform: str) -> bool:
    """Return True iff any list-entry's disable_if_platform_present blocks ``platform``."""
    for entry in plats:
        if not isinstance(entry, dict):
            continue
        blocked = entry.get(_DISABLE_IF_PLATFORM_PRESENT_KEY, [])
        if isinstance(blocked, list) and platform in blocked:
            return True
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
