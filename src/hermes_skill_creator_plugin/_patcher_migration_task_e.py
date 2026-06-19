"""Task E row rendering for the migration note.

Split from ``_patcher_migration_render.py`` to keep module member count
under wemake's WPS202 threshold. Renders the per-site row of the
Task E migration table.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._patcher_migration_consts import (
    ANCHOR_COL_WIDTH,
    INSERTION_COL_WIDTH,
    LF,
    _truncate,
)
from hermes_skill_creator_plugin._patcher_sites import Site


def _render_task_e_row(site: Site) -> str:
    """Render one Task E table row (5 columns including ``anchor``).

    The ``anchor`` column carries the byte-exact single-line locator
    for the site (plans/05 D5: single physical line, NOT a joined
    implicit-concat string). The locator is the primary anchor's
    text, truncated to 60 chars (whitespace / quotes preserved).
    """
    anchor_text = _truncate(site.primary_anchor().text, ANCHOR_COL_WIDTH)
    insertion_text = _truncate(site.insertion.rstrip(LF), INSERTION_COL_WIDTH)
    return _compose_task_e_row(site, anchor_text, insertion_text)


def _compose_task_e_row(site: Site, anchor_text: str, insertion_text: str) -> str:
    """Assemble the table row from precomputed cell strings."""
    line_num = site.line_for_state
    return (
        f"| {site.site_id} | {site.file_path}:{line_num} "
        f"(L{line_num}: `{anchor_text}`; "
        "single physical line) | (preserved verbatim) | "
        f"`{insertion_text}` (additive) "
        f"| `{anchor_text}` |"
    )
