"""Text-format helpers for the hermes-skill-creator reporter.

Extracted from :mod:`._reporter_format` to keep the parent under wemake
WPS202 (module members <= 7). The ``format_text`` entry point plus its
small ``_format_optional_*`` / ``_render_*`` / ``_padded_cell`` /
``_compute_column_widths`` / ``_build_total_cells`` helpers live here.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._reporter_dispatch import VALUE_DISPATCH
from hermes_skill_creator_plugin._reporter_format_consts import (
    COL_PCT_OF_CAP,
    COL_PROFILE,
    COL_TOKENS,
    COUNT_COLUMNS as _COUNT_COLUMNS,
    DEFAULT_TEXT_COLUMNS,
    NA_TEXT,
    TIMESTAMP_COLUMNS as _TIMESTAMP_COLUMNS,
)
from hermes_skill_creator_plugin._reporter_models import SkillRow
from hermes_skill_creator_plugin._tokenizer import MAX_DESCRIPTION_LENGTH


def _format_optional_count(row: SkillRow, attr: str) -> str:
    """Render an Optional[int] counter as ``n/a`` or its str form."""
    raw = getattr(row, attr)
    return NA_TEXT if raw is None else str(raw)


def _format_optional_str(row: SkillRow, attr: str) -> str:
    """Render an Optional[str] timestamp as ``n/a`` or its value."""
    raw_text: str | None = getattr(row, attr)
    return NA_TEXT if raw_text is None else raw_text


def _render_optional_count(row: SkillRow, attr: str) -> str:
    """Return the formatted optional count for ``attr``."""
    return _format_optional_count(row, attr)


def _render_optional_str(row: SkillRow, attr: str) -> str:
    """Return the formatted optional str for ``attr``."""
    return _format_optional_str(row, attr)


def _format_value_for_text(row: SkillRow, column: str) -> str:
    """Return the text-rendered value for ``column`` of ``row``."""
    if column in _COUNT_COLUMNS:
        return _render_optional_count(row, column)
    if column in _TIMESTAMP_COLUMNS:
        return _render_optional_str(row, column)
    getter = VALUE_DISPATCH.get(column)
    if getter is None:
        return ""
    return getter(row)


def _render_row(cells: list[str], widths: list[int]) -> str:
    """Render a single text row with stable column widths (module helper)."""
    return "  ".join(_padded_cell(cell, widths[idx]) for idx, cell in enumerate(cells))


def _padded_cell(cell: str, width: int) -> str:
    """Pad ``cell`` to ``width`` (extracted to keep WPS221 quiet)."""
    return cell.ljust(width)


def _compute_column_widths(headers: list[str], body: list[list[str]]) -> list[int]:
    """Compute per-column widths = max(header, body cell)."""
    widths = [len(header) for header in headers]
    for body_row in body:
        for cell_index, cell_value in enumerate(body_row):
            widths[cell_index] = max(widths[cell_index], len(cell_value))
    return widths


def _build_total_cells(
    columns: tuple[str, ...],
    total_tokens: int,
) -> list[str]:
    """Build the bottom ``total`` row (profile=tokens=pct filled, rest blank)."""
    total_cells: list[str] = ["" for _ in columns]
    for idx, column_name in enumerate(columns):
        if column_name == COL_PROFILE:
            total_cells[idx] = "total"
        elif column_name == COL_TOKENS:
            total_tokens_str = str(total_tokens)
            total_cells[idx] = total_tokens_str
        elif column_name == COL_PCT_OF_CAP:
            pct_value = (total_tokens / MAX_DESCRIPTION_LENGTH) * 100
            total_cells[idx] = f"{pct_value:.1f}"
        else:
            total_cells[idx] = ""
    return total_cells


def format_text(
    profile: str,
    rows: list[SkillRow],
    *,
    total_tokens: int,
    columns: tuple[str, ...] = DEFAULT_TEXT_COLUMNS,
) -> str:
    """Render a plain-text table for ``profile`` with the given rows.

    The columns are rendered in the order given by ``columns`` (default:
    ``TEXT_COLUMNS``). A ``total`` row is appended at the bottom showing
    the total tokens for the profile. n/a values are rendered as the
    literal string ``n/a``.
    """
    headers = list(columns)
    body = [[_format_value_for_text(row, column_name) for column_name in columns] for row in rows]
    widths = _compute_column_widths(headers, body)
    lines = [_render_row(headers, widths)]
    for body_row in body:
        lines.append(_render_row(body_row, widths))
    lines.append(_render_row(_build_total_cells(columns, total_tokens), widths))
    return "\n".join(lines)


__all__ = [
    "format_text",
    "_format_value_for_text",
]