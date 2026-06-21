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

from hermes_skill_creator_plugin import _reporter_format_consts as _consts
from hermes_skill_creator_plugin import _reporter_format_json as _json
from hermes_skill_creator_plugin import _reporter_format_text_value as _text

# Column-name constants + default column groups. Bound by name (instead of
# ``from x import a, b, c, ...``) to stay under the WPS235 "imported names
# from a module" cap while re-exporting all public symbols other modules
# (``_reporter_dispatch``, the format helpers) import from this hub.
COL_DESCRIPTION = _consts.COL_DESCRIPTION
COL_LAST_PATCHED_AT = _consts.COL_LAST_PATCHED_AT
COL_LAST_USED_AT = _consts.COL_LAST_USED_AT
COL_LAST_VIEWED_AT = _consts.COL_LAST_VIEWED_AT
COL_NAME = _consts.COL_NAME
COL_PATCH_COUNT = _consts.COL_PATCH_COUNT
COL_PCT_OF_CAP = _consts.COL_PCT_OF_CAP
COL_PROFILE = _consts.COL_PROFILE
COL_TOKENS = _consts.COL_TOKENS
COL_USE_COUNT = _consts.COL_USE_COUNT
COL_VIEW_COUNT = _consts.COL_VIEW_COUNT
COUNT_COLUMNS = _consts.COUNT_COLUMNS
DEFAULT_TEXT_COLUMNS = _consts.DEFAULT_TEXT_COLUMNS
NA_TEXT = _consts.NA_TEXT
TIMESTAMP_COLUMNS = _consts.TIMESTAMP_COLUMNS

# Text-format entry point + per-cell value renderer.
_format_value_for_text = _text._format_value_for_text
format_text = _text.format_text

# JSON-format entry point + row converter.
_skill_to_dict = _json._skill_to_dict
format_json = _json.format_json
