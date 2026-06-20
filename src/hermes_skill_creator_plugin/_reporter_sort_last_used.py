"""Last-used-at sort helpers for the reporter.

Split from ``_reporter_sort`` (WPS202 module surface budget). The
``_sort_by_last_used_at`` driver + its ``_sorted_na_rows`` /
``_group_dated_rows`` helpers live here.
"""

from __future__ import annotations

from collections import OrderedDict

from hermes_skill_creator_plugin._reporter_models import SkillRow


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
