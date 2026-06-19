"""Text-format helpers for the hermes-skill-creator reporter.

Re-export hub. The actual implementations live in sibling modules:

- :mod:`._reporter_format_text_render` — ``_render_row``,
  ``_padded_cell``, ``_compute_column_widths``.
- :mod:`._reporter_format_text_total` — ``_build_total_cells``.
- :mod:`._reporter_format_text_value` — ``_format_value_for_text`` and
  the ``_format_optional_*`` / ``_render_optional_*`` helpers.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._reporter_format_text_render import (
    _compute_column_widths,
    _render_row,
)
from hermes_skill_creator_plugin._reporter_format_text_total import (
    _build_total_cells,
)
from hermes_skill_creator_plugin._reporter_format_text_value import (
    _format_value_for_text,
    format_text,
)

__all__ = [
    "format_text",
    "_format_value_for_text",
    "_render_row",
    "_compute_column_widths",
    "_build_total_cells",
]
