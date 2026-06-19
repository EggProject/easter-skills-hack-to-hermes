"""Text + JSON format helpers for the hermes-skill-creator reporter.

TDD tests reference ``hermes_skill_creator_plugin._reporter.format_text`` /
``format_json`` / ``_format_value_for_text`` / ``_skill_to_dict``;
``_reporter.py`` re-exports them so existing imports continue to work.
"""

from __future__ import annotations

import json
from typing import Any

from hermes_skill_creator_plugin._reporter_models import ProfileSection, SkillRow
from hermes_skill_creator_plugin._tokenizer import MAX_DESCRIPTION_LENGTH

# Column-name constants (extracted to keep WPS226 quiet; used in the
# ``_format_value_for_text`` dispatch + the ``format_text`` total row).
COL_PROFILE = "profile"
COL_NAME = "name"
COL_DESCRIPTION = "description"
COL_TOKENS = "tokens"
COL_USE_COUNT = "use_count"
COL_VIEW_COUNT = "view_count"
COL_PATCH_COUNT = "patch_count"
COL_LAST_USED_AT = "last_used_at"
COL_LAST_VIEWED_AT = "last_viewed_at"
COL_LAST_PATCHED_AT = "last_patched_at"
COL_PCT_OF_CAP = "pct_of_cap"
NA_TEXT = "n/a"

# Default columns tuple (mirrors ``_reporter.TEXT_COLUMNS``); we can't
# import the constant from ``_reporter`` here (circular import risk), so
# it is duplicated. Keep both definitions in lock-step.
DEFAULT_TEXT_COLUMNS: tuple[str, ...] = (
    COL_PROFILE,
    COL_NAME,
    COL_DESCRIPTION,
    COL_TOKENS,
    COL_USE_COUNT,
    COL_VIEW_COUNT,
    COL_PATCH_COUNT,
    COL_LAST_USED_AT,
    COL_LAST_VIEWED_AT,
    COL_LAST_PATCHED_AT,
    COL_PCT_OF_CAP,
)


def _format_optional_count(row: SkillRow, attr: str) -> str:
    """Render an Optional[int] counter as ``n/a`` or its str form."""
    value = getattr(row, attr)
    return NA_TEXT if value is None else str(value)


def _format_optional_str(row: SkillRow, attr: str) -> str:
    """Render an Optional[str] timestamp as ``n/a`` or its value."""
    value: str | None = getattr(row, attr)
    return NA_TEXT if value is None else value


_COUNT_COLUMNS = frozenset({COL_USE_COUNT, COL_VIEW_COUNT, COL_PATCH_COUNT})
_TIMESTAMP_COLUMNS = frozenset({COL_LAST_USED_AT, COL_LAST_VIEWED_AT, COL_LAST_PATCHED_AT})


def _render_optional_count(row: SkillRow, attr: str) -> str:
    """Return the formatted optional count for `attr`."""
    return _format_optional_count(row, attr)


def _render_optional_str(row: SkillRow, attr: str) -> str:
    """Return the formatted optional str for `attr`."""
    return _format_optional_str(row, attr)


def _format_value_for_text(row: SkillRow, column: str) -> str:
    """Return the text-rendered value for `column` of `row`."""
    if column in _COUNT_COLUMNS:
        return _render_optional_count(row, column)
    if column in _TIMESTAMP_COLUMNS:
        return _render_optional_str(row, column)
    if column == COL_PROFILE:
        return row.profile
    if column == COL_NAME:
        return row.name
    if column == COL_DESCRIPTION:
        return row.description_display
    if column == COL_TOKENS:
        return str(row.tokens)
    if column == COL_PCT_OF_CAP:
        return f"{row.pct_of_cap:.1f}"
    return ""


def _render_row(cells: list[str], widths: list[int]) -> str:
    """Render a single text row with stable column widths (module helper)."""
    return "  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(cells))


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
    """Render a plain-text table for `profile` with the given rows.

    The columns are rendered in the order given by `columns` (default:
    `TEXT_COLUMNS`). A `total` row is appended at the bottom showing the
    total tokens for the profile. n/a values are rendered as the literal
    string `n/a`.
    """
    headers = list(columns)
    body = [[_format_value_for_text(row, column_name) for column_name in columns] for row in rows]
    widths = _compute_column_widths(headers, body)
    lines = [_render_row(headers, widths)]
    for body_row in body:
        lines.append(_render_row(body_row, widths))
    lines.append(_render_row(_build_total_cells(columns, total_tokens), widths))
    return "\n".join(lines)


def _skill_to_dict(row_obj: SkillRow) -> dict[str, Any]:
    return {
        "name": row_obj.name,
        "description": row_obj.description_full,
        "tokens": row_obj.tokens,
        "use_count": row_obj.use_count,
        "view_count": row_obj.view_count,
        "patch_count": row_obj.patch_count,
        "last_used_at": row_obj.last_used_at,
        "last_viewed_at": row_obj.last_viewed_at,
        "last_patched_at": row_obj.last_patched_at,
        "pct_of_cap": row_obj.pct_of_cap,
    }


def format_json(
    *,
    tool: str,
    version: str,
    generated_at: str,
    sections: list[ProfileSection],
) -> str:
    """Render a deterministic JSON document for one OR MANY profiles.

    Args:
        tool: tool name (top-level).
        version: tool version (top-level).
        generated_at: ISO 8601 timestamp (top-level).
        sections: list of ProfileSection, one per profile. The single-profile
            case is `sections=[ProfileSection(...)]`; the output is always
            a single valid JSON object with a `profiles: [...]` array.

    Returns:
        String with the rendered JSON document (sort_keys=True for stability).
    """
    payload: dict[str, Any] = {
        "tool": tool,
        "version": version,
        "generated_at": generated_at,
        "profiles": [
            {
                "profile_name": section.profile_name,
                "enabled_skills": [_skill_to_dict(row_obj) for row_obj in section.rows],
                "total_tokens": section.total_tokens,
            }
            for section in sections
        ],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
