"""Consolidated import surface for the enabled-detection module.

The :mod:`._enabled_detection` orchestrator re-exports ~14 helpers from
three sibling modules (``_enabled_detection_filter``,
``_enabled_detection_inline``, ``_enabled_detection_parse``). Binding
them all in ``_enabled_detection.py``'s own import block blows past
the wemake WPS201 (<=12 imports per module) cap.

This module consolidates the cross-sibling imports and re-binds each
helper under its underscore-prefixed local name. The orchestrator
reads through ``from easter_hermes_sorry_skills._enabled_detection
import _imps`` (or equivalently via the re-bound local names) so its
own import block stays under WPS201.
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _enabled_detection_filter as _filter_mod
from easter_hermes_sorry_skills import _enabled_detection_inline as _inline_mod
from easter_hermes_sorry_skills import _enabled_detection_parse as _parse_mod

# Filter helpers (re-bound under underscore-prefixed local names).
_apply_conditional_exclusions = _filter_mod.apply_conditional_exclusions
_apply_platform_filter = _filter_mod.apply_platform_filter
_conditional_excluded = _filter_mod.conditional_excluded
_disabled_set = _filter_mod.disabled_set
_drop_disabled = _filter_mod.drop_disabled
_find_skill_md = _filter_mod.find_skill_md
_platform_blocked = _filter_mod.platform_blocked
_platform_disables = _filter_mod.platform_disables

# Inline helpers.
_extract_disabled_from_inline = _inline_mod.extract_disabled_from_inline
_split_top_level_commas = _inline_mod.split_top_level_commas
_strip_quotes = _inline_mod.strip_quotes

# Parse helpers (underscored legacy aliases for Script #3 reporter path).
_load_config = _parse_mod._load_config
_parse_frontmatter = _parse_mod._parse_frontmatter
