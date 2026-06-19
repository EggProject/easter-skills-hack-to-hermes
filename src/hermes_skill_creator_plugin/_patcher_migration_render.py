"""Migration note renderer bodies (cap row + Task E row helpers).

Split from ``_patcher_migration`` to reduce module surface (WPS202)
and trim function complexity (WPS221 / WPS231).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from hermes_skill_creator_plugin._patcher_migration_consts import (
    MAX_DESC_LENGTH_HINT,
    S1_CAP_ROW_ANCHOR,
)
from hermes_skill_creator_plugin._patcher_migration_task_e import (
    _render_task_e_row,
)
from hermes_skill_creator_plugin._patcher_sites import S1_CAP_SITE, Site



@dataclass(frozen=True)
class HermesPatchContext:
    """Render-time inputs for the Script #1 migration note body."""

    target: Path
    git_head: str
    task_e_redirect: bool
    no_schema_redirect: bool
    timestamp: str
    cap_row: str
    patch_rows: list[str]


def _render_cap_row() -> str:
    """Render the S1.cap table row (5 columns: site_id | location | current | replacement | anchor).

    The ``anchor`` column carries the byte-exact primary anchor for the
    site (plans/08 §MIGRATION.hermes-patch.md). For S1.cap, that is
    ``if len(desc) > 60:`` (the comparator line; the slice line is a
    secondary anchor and is documented in the ``current`` column).
    """
    return _format_cap_row(MAX_DESC_LENGTH_HINT, S1_CAP_ROW_ANCHOR)


def _format_cap_row(hint: str, anchor: str) -> str:
    """Compose the S1.cap row from the description hint and anchor."""
    return (
        r"| S1.cap | agent/skill_utils.py \| extract_skill_description | "
        '`if len(desc) > 60:` and `return desc[:57] + "..."` | '
        "`if len(desc) > MAX_DESCRIPTION_LENGTH:` and "
        '`return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` '
        f"(with {hint}) "
        f"| `{anchor}` |"
    )


def _render_patch_table(sites: Iterable[Site]) -> list[str]:
    """Render Task E rows. Excludes ``S1.cap`` (rendered separately)."""
    rows: list[str] = []
    for site in sites:
        if site.site_id == S1_CAP_SITE.site_id:
            continue
        rows.append(_render_task_e_row(site))
    return rows


def _yes_no(flag: bool) -> str:
    """Render a boolean as the bare ``yes``/``no`` cell value."""
    return "yes" if flag else "no"


__all__ = [
    "HermesPatchContext",
    "S1_CAP_SITE",
    "Site",
    "_render_cap_row",
    "_render_patch_table",
    "_render_task_e_row",
]
