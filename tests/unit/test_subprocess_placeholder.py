"""Unit tests for plugin placeholder modules + small private branches.

Two coverage goals:
1. Cover the plugin's ``_subprocess`` placeholder module (1 statement
   only, exists to suppress WPS411).
2. Cover private branches introduced when private helpers were split
   out of larger functions for WPS202/WPS231 budgets:
   - ``_fallback_description`` with empty body (returns
     ``UNAVAILABLE_DESC_FMT``).
   - ``_dict_blocks`` with an empty dict (returns False).
"""

from __future__ import annotations

import importlib

from hermes_skill_creator_plugin._cli_report_helpers_paths import (
    UNAVAILABLE_DESC_FMT,
    _fallback_description,
)
from hermes_skill_creator_plugin._enabled_detection_platform import (
    _dict_blocks,
)


def test_plugin_subprocess_module_exposes_canonical_helper_path() -> None:
    """Plugin ``_subprocess`` exposes the canonical helper's import path.

    The plugin ``_subprocess`` module is a non-empty marker for plugin
    discovery (AC-4.6 + AC-4.15). It points at the canonical helper's
    import path (``skills.skill_creator._subprocess``) so operators can
    grep from the plugin marker to the single source of truth.
    """
    module = importlib.import_module(
        "hermes_skill_creator_plugin._subprocess",
    )
    assert module._CANONICAL_HELPER_MODULE == "skills.skill_creator._subprocess"


def test_fallback_description_with_empty_body() -> None:
    """Empty body returns the unavailable-description placeholder."""
    assert _fallback_description("", "alpha") == UNAVAILABLE_DESC_FMT.format(
        name="alpha",
    )


def test_dict_blocks_with_empty_dict() -> None:
    """Empty dict never blocks."""
    assert _dict_blocks({}) is False
