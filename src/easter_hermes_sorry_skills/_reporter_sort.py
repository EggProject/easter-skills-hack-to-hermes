"""Row sorting for the reporter output.

Extracted from ``_reporter.py`` to keep the reporter module under wemake
WPS202 (≤7 module members). The per-sort-key implementations live in
``_reporter_sort_keys`` for the same reason; this module owns the
``_RowFields`` dataclass, the ``make_row`` / ``_build_row`` helpers, and
the public ``sort_rows`` orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass

from easter_hermes_sorry_skills import _reporter_models as _models_mod
from easter_hermes_sorry_skills import _reporter_sort_keys as _keys_mod

SkillRow = _models_mod.SkillRow

_NA_MARKER_FIRST = _keys_mod._NA_MARKER_FIRST
_NA_MARKER_LAST = _keys_mod._NA_MARKER_LAST
MAX_DESCRIPTION_LENGTH = 1024


def _truncate_for_display(description: str, *, width: int = 60) -> str:
    """Truncate ``description`` to ``width`` chars + ellipsis if longer."""
    if len(description) <= width:
        return description
    truncated = description[: width - 3]
    return f"{truncated}..."


@dataclass(frozen=True)
class _RowFields:
    """All fields required to build a :class:`SkillRow`.

    Bundled so ``make_row`` / ``_build_row`` keep WPS211 in check.
    """

    profile: str
    name: str
    description: str
    tokens: int
    use_count: int | None
    view_count: int | None = None
    patch_count: int | None = None
    last_used_at: str | None = None
    last_viewed_at: str | None = None
    last_patched_at: str | None = None


def make_row(fields: _RowFields) -> SkillRow:
    """Build a :class:`SkillRow` from a :class:`_RowFields`."""
    return _build_row(fields)


def _build_row(fields: _RowFields) -> SkillRow:
    """Build a :class:`SkillRow` from a :class:`_RowFields`.

    ``description`` is truncated to 60 chars for display; the original
    is preserved by callers that need it.
    """
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


def _sort_key(
    row: SkillRow,
    sort_key: str,
) -> tuple[int, int, str] | tuple[int, str]:
    """Return a tuple sort key for `sort_key`.

    The key has the form `(na_marker, primary_desc, name_asc)` for keys that
    support n/a (use_count). For `tokens` there is no n/a branch.
    For `last_used_at` we cannot build a homogeneous tuple because the
    primary is a string — that case is handled separately in sort_rows().
    """
    if sort_key == "use_count":
        return _keys_mod._sort_key_use_count(row)
    return _keys_mod._sort_key_tokens(row)


def sort_rows(rows: list[SkillRow], sort_key: str) -> list[SkillRow]:
    """Return a NEW list of rows sorted by `sort_key` (desc on the primary key).

    Stable secondary key: skill name ascending.
    Rows with `n/a` on the primary sort column sort LAST.
    """
    if sort_key == "last_used_at":
        return _keys_mod._sort_by_last_used_at(rows)
    return sorted(rows, key=lambda row: _sort_key(row, sort_key))
