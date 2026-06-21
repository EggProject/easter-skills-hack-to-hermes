"""Per-sort-key implementations for the reporter row sort.

Extracted from ``_reporter_sort.py`` to keep that module under wemake
WPS202 (≤7 module members). Each sort key gets its own function so the
top-level ``sort_rows`` orchestrator stays compact.
"""

from __future__ import annotations

from collections import OrderedDict

from hermes_skill_creator_plugin import _reporter_models as _models_mod

SkillRow = _models_mod.SkillRow

_NA_MARKER_FIRST = 0
_NA_MARKER_LAST = 1


def _sort_key_tokens(row: SkillRow) -> tuple[int, str]:
    """Tokens desc, name asc — also the fallback for unknown sort keys."""
    return (-row.tokens, row._sort_name)


def _sort_key_use_count(row: SkillRow) -> tuple[int, int, str]:
    """Use-count desc, name asc; n/a rows sort LAST."""
    if row.use_count is None:
        # n/a rows sort AFTER non-na rows (1 > 0). The 0/0 placeholders
        # for primary+name are not consulted because na_marker dominates.
        return (_NA_MARKER_LAST, 0, row._sort_name)
    return (_NA_MARKER_FIRST, -row.use_count, row._sort_name)


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
