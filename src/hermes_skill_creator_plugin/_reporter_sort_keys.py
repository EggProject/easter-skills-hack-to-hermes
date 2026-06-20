"""Per-sort-key helpers for the reporter sort module.

Split from ``_reporter_sort`` (WPS202 module surface budget). Each
sort key (``tokens``, ``use_count``) gets its own tiny builder so the
main sort module stays under the module surface cap.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._reporter_models import SkillRow


def _sort_key_tokens(row: SkillRow) -> tuple[int, str]:
    """Tokens desc, name asc — also the fallback for unknown sort keys."""
    return (-row.tokens, row._sort_name)


def _sort_key_use_count(row: SkillRow) -> tuple[int, int, str]:
    """Use-count desc, name asc; n/a rows sort LAST."""
    if row.use_count is None:
        # n/a rows sort AFTER non-na rows (1 > 0). The 0/0 placeholders
        # for primary+name are not consulted because na_marker dominates.
        return (1, 0, row._sort_name)
    return (0, -row.use_count, row._sort_name)
