"""Row-builder + sort helpers for the hermes-skill-creator reporter.

TDD tests reference ``hermes_skill_creator_plugin._reporter.make_row`` /
``sort_rows`` / ``_truncate_for_display`` / ``_sort_key``; ``_reporter.py``
re-exports them so existing imports continue to work.
"""

from __future__ import annotations

from collections import OrderedDict

from hermes_skill_creator_plugin._reporter_models import SkillRow
from hermes_skill_creator_plugin._tokenizer import MAX_DESCRIPTION_LENGTH

# Default ellipsis suffix for truncated descriptions (3 chars).
ELLIPSIS = "..."


def _truncate_for_display(description: str, *, width: int = 60) -> str:
    """Truncate `description` to `width` chars with a trailing ellipsis when over.

    Mirrors `extract_skill_description` in agent/skill_utils.py:688-689:
    `desc[:57] + "..."` when `len(desc) > 60`, otherwise the full description.
    """
    if len(description) > width:
        return description[: width - len(ELLIPSIS)] + ELLIPSIS
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
        na_rows = sorted(
            [r for r in rows if r.last_used_at is None],
            key=lambda r: r.name,
        )
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
