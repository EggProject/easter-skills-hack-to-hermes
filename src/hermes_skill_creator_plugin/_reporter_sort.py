"""Row-builder + sort helpers for the hermes-skill-creator reporter.

TDD tests reference ``hermes_skill_creator_plugin._reporter.make_row`` /
``sort_rows`` / ``_truncate_for_display`` / ``_sort_key``; ``_reporter.py``
re-exports them so existing imports continue to work.
"""

from __future__ import annotations

import dataclasses
from collections import OrderedDict

from hermes_skill_creator_plugin._reporter_models import SkillRow
from hermes_skill_creator_plugin._tokenizer import MAX_DESCRIPTION_LENGTH

# Default ellipsis suffix for truncated descriptions (3 chars).
ELLIPSIS = "..."

# Markers used to push n/a rows AFTER populated rows in the sort tuple.
_NA_MARKER_LAST = 1
_NA_MARKER_FIRST = 0


def _truncate_for_display(description: str, *, width: int = 60) -> str:
    """Truncate `description` to `width` chars with a trailing ellipsis when over.

    Mirrors `extract_skill_description` in agent/skill_utils.py:688-689:
    `desc[:57] + "..."` when `len(desc) > 60`, otherwise the full description.
    """
    if len(description) > width:
        return description[: width - len(ELLIPSIS)] + ELLIPSIS
    return description


@dataclasses.dataclass(frozen=True)
class _RowFields:
    """Group of keyword-only inputs for :func:`make_row`."""

    profile: str
    name: str
    description: str
    tokens: int
    use_count: int | None
    view_count: int | None
    patch_count: int | None
    last_used_at: str | None
    last_viewed_at: str | None
    last_patched_at: str | None


def make_row(fields: _RowFields) -> SkillRow:
    """Build a SkillRow with derived display + pct_of_cap fields."""
    return _build_row(fields)


def _build_row(fields: _RowFields) -> SkillRow:
    """Compose a SkillRow from a :class:`_RowFields` bundle."""
    pct = round((fields.tokens / MAX_DESCRIPTION_LENGTH) * 100, 1)
    return SkillRow(
        profile=fields.profile,
        name=fields.name,
        description_full=fields.description,
        description_display=_truncate_for_display(fields.description),
        tokens=fields.tokens,
        use_count=fields.use_count,
        view_count=fields.view_count,
        patch_count=fields.patch_count,
        last_used_at=fields.last_used_at,
        last_viewed_at=fields.last_viewed_at,
        last_patched_at=fields.last_patched_at,
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
            return (_NA_MARKER_LAST, 0, name)
        return (_NA_MARKER_FIRST, -row.use_count, name)
    # Unknown — fall back to tokens desc.
    return (-row.tokens, name)


def sort_rows(rows: list[SkillRow], sort_key: str) -> list[SkillRow]:
    """Return a NEW list of rows sorted by `sort_key` (desc on the primary key).

    Stable secondary key: skill name ascending.
    Rows with `n/a` on the primary sort column sort LAST.
    """
    if sort_key == "last_used_at":
        return _sort_by_last_used_at(rows)
    return sorted(rows, key=lambda row: _sort_key(row, sort_key))


def _sort_by_last_used_at(rows: list[SkillRow]) -> list[SkillRow]:
    """Sort by ``last_used_at`` desc with name-asc tiebreaker and n/a LAST."""
    na_rows = _sorted_na_rows(rows)
    groups = _group_dated_rows(rows)
    for bucket in groups.values():
        bucket.sort(key=lambda bucket_row: bucket_row.name)
    out: list[SkillRow] = []
    for ts in reversed(list(groups.keys())):
        out.extend(groups[ts])
    return out + na_rows


def _sorted_na_rows(rows: list[SkillRow]) -> list[SkillRow]:
    """Return ``rows`` with ``last_used_at is None`` sorted by name asc."""
    return sorted(
        (na_row for na_row in rows if na_row.last_used_at is None),
        key=lambda na_row: na_row.name,
    )


def _group_dated_rows(rows: list[SkillRow]) -> OrderedDict[str, list[SkillRow]]:
    """Bucket ``rows`` whose ``last_used_at`` is non-None by their timestamp."""
    groups: OrderedDict[str, list[SkillRow]] = OrderedDict()
    for dated_row in rows:
        if dated_row.last_used_at is not None:
            groups.setdefault(dated_row.last_used_at, []).append(dated_row)
    return groups
