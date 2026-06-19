"""src/hermes_skill_creator_plugin/_enabled_detection.py

Single source of truth for "which skills are enabled for a profile?"
- shared by Script #2 (apply) and Script #3 (reporter). Owns:
hermes_skill_creator_plugin.

See also: plans/06-script-2-profiles.md (owner),
plans/13-script-3-report.md (consumer)

The reporter (Script #3) imports get_enabled_skills() from this module
at module top level. Script #2 also imports it. Neither re-implements
the detection logic locally. If this module is unavailable at import
time the reporter aborts with exit 6 - there is NO local
re-implementation fallback.

This module exposes two parallel helper APIs:

  - The original helpers (``_parse_frontmatter``, ``_load_config``,
    ``_disabled_set``, ``_platform_blocked``, ``_conditional_excluded``)
    used by the read-only reporter (Script #3) and its tests under
    ``tests/report/``.
  - The richer helpers (``_walk_installed_skill_names``,
    ``_find_skill_md``, ``_apply_platform_filter``,
    ``_apply_conditional_exclusions``, ``_platform_disables``,
    ``_split_top_level_commas``, ``_extract_disabled_from_inline``)
    used by Script #2's apply path and its tests under
    ``tests/unit/``.

``get_enabled_skills`` is the public entry point; it routes each call
through the richer helper pipeline and accepts BOTH the
``platforms: {darwin: value}`` shape (used by Script #2's unit tests)
and the ``platforms: [{disable_if_platform_present: [darwin]}]`` shape
(used by the reporter's tests).
"""
from __future__ import annotations

import re
from pathlib import Path

import frontmatter
import yaml

from hermes_skill_creator_plugin._enabled_detection_filter import (
    apply_conditional_exclusions as _apply_conditional_exclusions,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    apply_platform_filter as _apply_platform_filter,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    conditional_excluded as _conditional_excluded,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    disabled_set as _disabled_set,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    drop_disabled as _drop_disabled,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    find_skill_md as _find_skill_md,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    platform_blocked as _platform_blocked,
)
from hermes_skill_creator_plugin._enabled_detection_filter import (
    platform_disables as _platform_disables,
)
from hermes_skill_creator_plugin._enabled_detection_inline import (
    extract_disabled_from_inline as _extract_disabled_from_inline,
)
from hermes_skill_creator_plugin._enabled_detection_inline import (
    split_top_level_commas as _split_top_level_commas,
)
from hermes_skill_creator_plugin._enabled_detection_inline import strip_quotes as _strip_quotes
from hermes_skill_creator_plugin._enabled_detection_parse import (
    load_config as _load_config,
)
from hermes_skill_creator_plugin._enabled_detection_parse import (
    parse_frontmatter as _parse_frontmatter,
)


_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_SKILLS_DIR_NAME = "skills"
_SKILL_MD_NAME = "SKILL.md"
_TEXT_ENCODING = "utf-8"


def _walk_installed_skill_names(skills_dir: Path) -> set[str]:
    """Walk ``skills_dir`` and return the set of installed skill NAMES."""
    if not skills_dir.is_dir():
        return set()
    names: set[str] = set()
    for child in sorted(skills_dir.iterdir()):
        skill_name = _name_from_skill_dir(child)
        if skill_name is not None:
            names.add(skill_name)
    return names


def _name_from_skill_dir(child: Path) -> str | None:
    """Return the installed-skill name for ``child`` (a skill directory)."""
    if not child.is_dir():
        return None
    skill_md = child / _SKILL_MD_NAME
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding=_TEXT_ENCODING)
    except OSError:
        return None
    match = _NAME_RE.search(text)
    if match is None:
        return str(child.name)
    return _strip_quotes(match.group(1))


def get_enabled_skills(
    profile_path: Path,
    *,
    platform: str | None = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for ``profile_path``."""
    profile_path = Path(profile_path)
    skills_dir = profile_path / _SKILLS_DIR_NAME
    installed = _walk_installed_skill_names(skills_dir)
    if not installed:
        return frozenset()
    config = _load_config(profile_path)
    disabled = _disabled_set(config, platform)
    if disabled:
        installed = _drop_disabled(installed, disabled)
    installed = _apply_platform_filter(installed, profile_path, platform)
    installed = _apply_conditional_exclusions(
        installed,
        profile_path,
        platform,
    )
    return frozenset(installed)


__all__ = [
    "get_enabled_skills",
    "_parse_frontmatter",
    "_load_config",
    "_disabled_set",
    "_platform_blocked",
    "_conditional_excluded",
    "_walk_installed_skill_names",
    "_find_skill_md",
    "_apply_platform_filter",
    "_apply_conditional_exclusions",
    "_platform_disables",
    "_extract_disabled_from_inline",
    "_split_top_level_commas",
]
