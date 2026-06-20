"""Per-column text-value rendering for the reporter.

Extracted from :mod:`._reporter_format_text` to keep that file under
wemake WPS202 (module members <= 7). Provides the per-cell dispatch
plus the ``format_text`` entry point that drives row + total
rendering.

Reference: plans/13-script-3-report.md.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._reporter_dispatch import VALUE_DISPATCH
from hermes_skill_creator_plugin._reporter_format_consts import (
    COUNT_COLUMNS as _COUNT_COLUMNS,
)
from hermes_skill_creator_plugin._reporter_format_consts import (
    DEFAULT_TEXT_COLUMNS,
    NA_TEXT,
)
from hermes_skill_creator_plugin._reporter_format_consts import (
    TIMESTAMP_COLUMNS as _TIMESTAMP_COLUMNS,
)
from hermes_skill_creator_plugin._reporter_format_text_render import (
    _compute_column_widths,
    _render_row,
)
from hermes_skill_creator_plugin._reporter_format_text_total import (
    _build_total_cells,
)
from hermes_skill_creator_plugin._reporter_models import SkillRow


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
