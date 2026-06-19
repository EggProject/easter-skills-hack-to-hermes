"""Text + JSON format helpers for the hermes-skill-creator reporter.

Re-export hub. The actual implementations live in sibling modules:

- :mod:`._reporter_format_consts` — column-name constants, default
  columns, count + timestamp column groups.
- :mod:`._reporter_format_text` — ``format_text`` and the
  ``_format_value_for_text`` / ``_render_*`` / ``_padded_cell`` /
  ``_compute_column_widths`` / ``_build_total_cells`` helpers.
- :mod:`._reporter_format_json` — ``format_json`` and the
  ``_skill_to_dict`` row converter.

TDD tests reference ``hermes_skill_creator_plugin._reporter.format_text`` /
``format_json`` / ``_format_value_for_text`` / ``_skill_to_dict``;
``_reporter.py`` re-exports them so existing imports continue to work.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._reporter_format_consts import (
    COL_DESCRIPTION,
    COL_NAME,
    COL_PCT_OF_CAP,
    COL_PROFILE,
    COL_TOKENS,
    DEFAULT_TEXT_COLUMNS,
)
from hermes_skill_creator_plugin._reporter_format_json import (
    _skill_to_dict,
    format_json,
)
from hermes_skill_creator_plugin._reporter_format_text import (
    _format_value_for_text,
    format_text,
)

# Re-export the column-name constants (and the default columns tuple)
# that other modules (``_reporter_dispatch``) import from this module.
__all__ = [
    "COL_DESCRIPTION",
    "COL_NAME",
    "COL_PCT_OF_CAP",
    "COL_PROFILE",
    "COL_TOKENS",
    "DEFAULT_TEXT_COLUMNS",
    "format_json",
    "format_text",
    "_format_value_for_text",
    "_skill_to_dict",
]
