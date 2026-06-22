"""Low-level text rendering primitives for the reporter.

Extracted from :mod:`._reporter_format_text` to keep that file under
wemake WPS202 (module members <= 7). Provides the small
``_padded_cell`` / ``_render_row`` / ``_compute_column_widths``
helpers used by ``format_text``.
"""

from __future__ import annotations


def _padded_cell(cell: str, width: int) -> str:
    """Pad ``cell`` to ``width`` (extracted to keep WPS221 quiet)."""
    return cell.ljust(width)


def _render_row(cells: list[str], widths: list[int]) -> str:
    """Render a single text row with stable column widths (module helper)."""
    return "  ".join(_zip_padded(cells, widths))


def _zip_padded(cells: list[str], widths: list[int]) -> list[str]:
    """Pad each cell to its corresponding width, preserving order."""
    return [_padded_cell(cell, widths[idx]) for idx, cell in enumerate(cells)]


def _compute_column_widths(headers: list[str], body: list[list[str]]) -> list[int]:
    """Compute per-column widths = max(header, body cell)."""
    widths = [len(header) for header in headers]
    for body_row in body:
        for cell_index, cell_value in enumerate(body_row):
            widths[cell_index] = max(widths[cell_index], len(cell_value))
    return widths
