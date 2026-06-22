"""Text-format helpers for the hermes-skill-creator reporter.

Re-export hub. The actual implementations live in sibling modules:

- :mod:`._reporter_format_text_render` — ``_render_row``,
  ``_padded_cell``, ``_compute_column_widths``.
- :mod:`._reporter_format_text_total` — ``_build_total_cells``.
- :mod:`._reporter_format_text_value` — ``_format_value_for_text`` and
  the ``_format_optional_*`` / ``_render_optional_*`` helpers.
"""

from __future__ import annotations
