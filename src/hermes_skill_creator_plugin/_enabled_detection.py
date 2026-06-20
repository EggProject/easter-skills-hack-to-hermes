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

from hermes_skill_creator_plugin import _enabled_detection_imports as _imps

# Local bindings for the body; source-of-truth imports live in
# :mod:`._enabled_detection_imports` (extracted to satisfy WPS201).
_apply_conditional_exclusions = _imps._apply_conditional_exclusions
_apply_platform_filter = _imps._apply_platform_filter
_conditional_excluded = _imps._conditional_excluded
_disabled_set = _imps._disabled_set
_drop_disabled = _imps._drop_disabled
_extract_disabled_from_inline = _imps._extract_disabled_from_inline
_find_skill_md = _imps._find_skill_md
_load_config = _imps._load_config
_parse_frontmatter = _imps._parse_frontmatter
_platform_blocked = _imps._platform_blocked
_platform_disables = _imps._platform_disables
_split_top_level_commas = _imps._split_top_level_commas
_strip_quotes = _imps._strip_quotes

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
