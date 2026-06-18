"""src/hermes_skill_creator_plugin/_reporter.py

Format text/JSON output and sort rows for the reporter. Owns: hermes_skill_creator_plugin.

See also: plans/13-script-3-report.md

n/a-vs-0 (binding, V8/W4 fix): render `n/a` iff the Curator row's
`_persisted` flag is `False` (or the Curator module is absent). Render the
recorded integer when `_persisted` is `True`, even if the count is `0`.
We NEVER call `get_record()` (the backfill accessor) in the n/a decision
path — it always backfills `_empty_record()` and would collapse
"never tracked" into a zeroed record.

TDD test cases for this module:
  test_format_text_columns_present
  test_format_text_truncates_description_to_60
  test_format_text_total_row
  test_format_text_alignment
  test_format_json_shape
  test_format_json_deterministic_with_frozen_time
  test_format_json_includes_pct_of_cap
  test_sort_rows_by_tokens_desc
  test_sort_rows_by_use_count_desc_with_na_last
  test_sort_rows_by_last_used_at_desc_with_na_last
  test_sort_rows_stable_secondary_key_by_name
  test_na_renders_when_persisted_false
  test_zero_renders_when_persisted_true
  test_na_when_curator_absent
  test_no_call_to_get_record
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ._tokenizer import MAX_DESCRIPTION_LENGTH

# Curator's 6 documented field names (verified against tools/skill_usage.py:463-468).
DOCUMENTED_USAGE_FIELDS = frozenset(
    {"use_count", "view_count", "patch_count", "last_used_at", "last_viewed_at", "last_patched_at"}
)

# Columns rendered in the plain-text table (in this fixed order).
TEXT_COLUMNS = (
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


@dataclass(frozen=True)
class SkillRow:
    """A single skill row in the report. All values are already resolved.

    `use_count`, `view_count`, `patch_count` are Optional[int] — None means
    "n/a" (rendered as the string "n/a" in text, as `null` in JSON).
    `last_used_at`, `last_viewed_at`, `last_patched_at` are Optional[str] —
    None means "n/a".
    `description_full` is the full description (preserved in JSON).
    `description_display` is the truncated 60-char form for text rendering.
    `pct_of_cap` is rounded to one decimal place.
    """

    profile: str
    name: str
    description_full: str
    description_display: str
    tokens: int
    use_count: int | None
    view_count: int | None
    patch_count: int | None
    last_used_at: str | None
    last_viewed_at: str | None
    last_patched_at: str | None
    pct_of_cap: float
    # Sort key cached (used internally to break ties by name).
    _sort_name: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        # Stable secondary sort key: name asc.
        object.__setattr__(self, "_sort_name", self.name)


def _truncate_for_display(description: str, *, width: int = 60) -> str:
    """Truncate `description` to `width` chars with a trailing ellipsis when over.

    Mirrors `extract_skill_description` in agent/skill_utils.py:688-689:
    `desc[:57] + "..."` when `len(desc) > 60`, otherwise the full description.
    """
    if len(description) > width:
        return description[: width - 3] + "..."
    return description


def make_row(
    *,
    profile: str,
    name: str,
    description: str,
    tokens: int,
    use_count: int | None,
    view_count: int | None,
    patch_count: int | None,
    last_used_at: str | None,
    last_viewed_at: str | None,
    last_patched_at: str | None,
) -> SkillRow:
    """Build a SkillRow with derived display + pct_of_cap fields."""
    pct = round((tokens / MAX_DESCRIPTION_LENGTH) * 100, 1)
    return SkillRow(
        profile=profile,
        name=name,
        description_full=description,
        description_display=_truncate_for_display(description),
        tokens=tokens,
        use_count=use_count,
        view_count=view_count,
        patch_count=patch_count,
        last_used_at=last_used_at,
        last_viewed_at=last_viewed_at,
        last_patched_at=last_patched_at,
        pct_of_cap=pct,
    )


def _sort_key(row: SkillRow, sort_key: str) -> tuple[int, int, str] | tuple[int, str]:
    """Return a tuple sort key for `sort_key`.

    The key has the form `(na_marker, primary_desc, name_asc)` for keys that
    support n/a (use_count). For `tokens` there is no n/a branch.
    For `last_used_at` we cannot build a homogeneous tuple because the
    primary is a string — that case is handled separately in sort_rows().
    """
    name = row._sort_name
    if sort_key == "tokens":
        return (-row.tokens, name)
    if sort_key == "use_count":
        if row.use_count is None:
            # n/a rows sort AFTER non-na rows (1 > 0). The 0/0 placeholders
            # for primary+name are not consulted because na_marker dominates.
            return (1, 0, name)
        return (0, -row.use_count, name)
    # Unknown — fall back to tokens desc.
    return (-row.tokens, name)


def sort_rows(rows: list[SkillRow], sort_key: str) -> list[SkillRow]:
    """Return a NEW list of rows sorted by `sort_key` (desc on the primary key).

    Stable secondary key: skill name ascending.
    Rows with `n/a` on the primary sort column sort LAST.
    """
    if sort_key == "last_used_at":
        # n/a rows sort LAST (name asc within the n/a group).
        # non-na rows: most-recent first; within equal timestamps, name asc.
        # Implementation: group by timestamp, name-asc sort within each
        # group, then concatenate groups in reverse timestamp order.
        from collections import OrderedDict

        na_rows = sorted([r for r in rows if r.last_used_at is None], key=lambda r: r.name)
        groups: OrderedDict[str, list[SkillRow]] = OrderedDict()
        for r in rows:
            if r.last_used_at is not None:
                groups.setdefault(r.last_used_at, []).append(r)
        for ts in groups:
            groups[ts].sort(key=lambda r: r.name)
        out: list[SkillRow] = []
        for ts in reversed(list(groups.keys())):
            out.extend(groups[ts])
        return out + na_rows
    return sorted(rows, key=lambda r: _sort_key(r, sort_key))


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
    columns: tuple[str, ...] = TEXT_COLUMNS,
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
    for b in body:
        for i, cell in enumerate(b):
            widths[i] = max(widths[i], len(cell))

    # Render
    def _render(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines.append(_render(headers))
    for b in body:
        lines.append(_render(b))
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


@dataclass(frozen=True)
class ProfileSection:
    """One profile's section inside a multi-profile JSON report."""

    profile_name: str
    rows: list[SkillRow]
    total_tokens: int


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


__all__ = [
    "SkillRow",
    "ProfileSection",
    "make_row",
    "sort_rows",
    "format_text",
    "format_json",
    "TEXT_COLUMNS",
    "DOCUMENTED_USAGE_FIELDS",
    "_truncate_for_display",
]
