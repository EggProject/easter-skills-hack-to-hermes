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

# Default columns tuple (mirrors ``_reporter.TEXT_COLUMNS``); we can't
# import the constant from ``_reporter`` here (circular import risk), so
# it is duplicated. Keep both definitions in lock-step.
DEFAULT_TEXT_COLUMNS: tuple[str, ...] = (
    "profile",
    "name",
    "description",
    "tokens",
    "use_count",
    "view_count",
    "patch_count",
    "last_used_at",
    "last_viewed_at",
    "last_patched_at",
    "pct_of_cap",
)


def _format_value_for_text(row: SkillRow, column: str) -> str:
    """Return the text-rendered value for `column` of `row`."""
    if column == "profile":
        return row.profile
    if column == "name":
        return row.name
    if column == "description":
        return row.description_display
    if column == "tokens":
        return str(row.tokens)
    if column == "use_count":
        return "n/a" if row.use_count is None else str(row.use_count)
    if column == "view_count":
        return "n/a" if row.view_count is None else str(row.view_count)
    if column == "patch_count":
        return "n/a" if row.patch_count is None else str(row.patch_count)
    if column == "last_used_at":
        return "n/a" if row.last_used_at is None else row.last_used_at
    if column == "last_viewed_at":
        return "n/a" if row.last_viewed_at is None else row.last_viewed_at
    if column == "last_patched_at":
        return "n/a" if row.last_patched_at is None else row.last_patched_at
    if column == "pct_of_cap":
        return f"{row.pct_of_cap:.1f}"
    return ""


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
    lines: list[str] = []
    # Build a header row and a body row. We compute the column widths from
    # the union of headers + body values for stable alignment.
    headers = list(columns)
    body: list[list[str]] = []
    for row in rows:
        body.append([_format_value_for_text(row, c) for c in columns])
    # Compute widths
    widths = [len(h) for h in headers]
    for body_row in body:
        for cell_index, cell_value in enumerate(body_row):
            widths[cell_index] = max(widths[cell_index], len(cell_value))

    def _render(cells: list[str]) -> str:
        return "  ".join(
            cell.ljust(widths[i]) for i, cell in enumerate(cells)
        )

    lines.append(_render(headers))
    for body_row in body:
        lines.append(_render(body_row))
    # Total row
    total_cells = [""] * len(columns)
    for i, c in enumerate(columns):
        if c == "profile":
            total_cells[i] = "total"
        elif c == "tokens":
            total_cells[i] = str(total_tokens)
        elif c == "pct_of_cap":
            total_cells[i] = f"{(total_tokens / MAX_DESCRIPTION_LENGTH) * 100:.1f}"
        else:
            total_cells[i] = ""
    lines.append(_render(total_cells))
    return "\n".join(lines)


def _skill_to_dict(r: SkillRow) -> dict[str, Any]:
    return {
        "name": r.name,
        "description": r.description_full,
        "tokens": r.tokens,
        "use_count": r.use_count,
        "view_count": r.view_count,
        "patch_count": r.patch_count,
        "last_used_at": r.last_used_at,
        "last_viewed_at": r.last_viewed_at,
        "last_patched_at": r.last_patched_at,
        "pct_of_cap": r.pct_of_cap,
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
                "profile_name": s.profile_name,
                "enabled_skills": [_skill_to_dict(r) for r in s.rows],
                "total_tokens": s.total_tokens,
            }
            for s in sections
        ],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
