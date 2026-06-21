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

    The ``anchor`` column carries the byte-exact locator for the site.
    For single-line anchors (plans/05 D5) the locator is one physical
    line; for multi-line anchors (e.g. E4/E5 after the WPS342 fix) only
    the FIRST physical line is shown in the table cell to keep the
    markdown row on a single line. Truncated to 60 chars (whitespace /
    quotes preserved).
    """
    raw_text = site.primary_anchor().text
    first_line = raw_text.splitlines()[0] if raw_text else ""
    anchor_text = _truncate(first_line, ANCHOR_COL_WIDTH)
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
