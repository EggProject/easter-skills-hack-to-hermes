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


def test_plugin_subprocess_module_exposes_vendored_marker() -> None:
    """Plugin ``_subprocess`` exposes the vendored-helper marker."""
    module = importlib.import_module(
        "hermes_skill_creator_plugin._subprocess",
    )
    assert module._VENDORED_HELPERS_MODULE == "tools.subprocess_env"


def test_fallback_description_with_empty_body() -> None:
    """Empty body returns the unavailable-description placeholder."""
    assert _fallback_description("", "alpha") == UNAVAILABLE_DESC_FMT.format(
        name="alpha",
    )


def test_dict_blocks_with_empty_dict() -> None:
    """Empty dict never blocks."""
    assert _dict_blocks({}) is False
