"""Migration note renderer bodies (cap row, Task E rows, full sections).

Split from ``_patcher_migration`` to reduce module surface (WPS202)
and trim function complexity (WPS221 / WPS231).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from hermes_skill_creator_plugin._patcher_sites import S1_CAP_SITE, Site

# Cap-raise row anchor (the primary 8+ char anchor for S1.cap).
# The 5-column schema is: site_id | location | current | replacement | anchor.
S1_CAP_ROW_ANCHOR = "if len(desc) > 60:"
# Default truncate widths for the ``current`` / ``replacement`` columns
# (per plans/08 §MIGRATION.hermes-patch.md row schema).
ANCHOR_COL_WIDTH = 60
INSERTION_COL_WIDTH = 80
# Replacement literal shown to operators (cap-row column).
MAX_DESC_LENGTH_HINT = (
    "`MAX_DESCRIPTION_LENGTH` defined locally, e.g. "
    "`MAX_DESCRIPTION_LENGTH = 1024`, to avoid a circular import from "
    "`tools.skills_tool`"
)
# Ellipsis character for _truncate().
ELLIPSIS_CHAR = "…"
# Raw-string newline escape for the markdown LF -> ``\\n`` rendering.
NEWLINE_ESCAPE = r"\n"
# Actual LF character (real newline).
LF = "\n"


def _truncate(text: str, max_len: int) -> str:
    """Escape LF and truncate to ``max_len`` (suffix with ellipsis when over)."""
    text = text.replace(LF, NEWLINE_ESCAPE)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + ELLIPSIS_CHAR


def _render_cap_row() -> str:
    """Render the S1.cap table row (5 columns: site_id | location | current | replacement | anchor).

    The ``anchor`` column carries the byte-exact primary anchor for the
    site (plans/08 §MIGRATION.hermes-patch.md). For S1.cap, that is
    ``if len(desc) > 60:`` (the comparator line; the slice line is a
    secondary anchor and is documented in the ``current`` column).
    """
    return (
        "| S1.cap | agent/skill_utils.py \\| extract_skill_description | "
        '`if len(desc) > 60:` and `return desc[:57] + "..."` | '
        "`if len(desc) > MAX_DESCRIPTION_LENGTH:` and "
        '`return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` '
        f"(with {MAX_DESC_LENGTH_HINT}) "
        f"| `{S1_CAP_ROW_ANCHOR}` |"
    )


def _render_patch_table(sites: Iterable[Site]) -> list[str]:
    """Render Task E rows. Excludes ``S1.cap`` (rendered separately)."""
    rows: list[str] = []
    for site in sites:
        if site.site_id == S1_CAP_SITE.site_id:
            continue
        rows.append(_render_task_e_row(site))
    return rows


def _render_task_e_row(site: Site) -> str:
    """Render one Task E table row (5 columns including ``anchor``).

    The ``anchor`` column carries the byte-exact single-line locator
    for the site (plans/05 D5: single physical line, NOT a joined
    implicit-concat string). The locator is the primary anchor's
    text, truncated to 60 chars (whitespace / quotes preserved).
    """
    anchor_text = _truncate(site.primary_anchor().text, ANCHOR_COL_WIDTH)
    insertion_text = _truncate(
        site.insertion.rstrip(LF),
        INSERTION_COL_WIDTH,
    )
    return (
        f"| {site.site_id} | {site.file_path}:{site.line_for_state} "
        f"(L{site.line_for_state}: `{anchor_text}`; "
        "single physical line) | (preserved verbatim) | "
        f"`{insertion_text}` (additive) "
        f"| `{anchor_text}` |"
    )


def _yes_no(value: bool) -> str:
    """Render a boolean as the bare ``yes``/``no`` cell value."""
    return "yes" if value else "no"


def _render_migration_hermes_patch(
    *,
    target: Path,
    git_head: str,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    timestamp: str,
    cap_row: str,
    patch_rows: list[str],
) -> str:
    task_e_section = ""
    if task_e_redirect:
        rows_text = "\n".join(patch_rows)
        task_e_section = (
            LF
            + "## Task E sites (only if --task-e-redirect)"
            + LF
            + LF
            + "| site_id | location | current | replacement | anchor |"
            + LF
            + "| --- | --- | --- | --- | --- |"
            + LF
            + rows_text
            + LF
        )
    body = _build_body(
        target=target,
        git_head=git_head,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        timestamp=timestamp,
        cap_row=cap_row,
        task_e_section=task_e_section,
    )
    return body


def _build_body(
    *,
    target: Path,
    git_head: str,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    timestamp: str,
    cap_row: str,
    task_e_section: str,
) -> str:
    return (
        "# Hermes Patch — Script #1 (cap raise + 7 Task E sites)"
        + LF
        + LF
        + "<!-- generated; do not edit by hand -->"
        + LF
        + LF
        + "| Field | Value |"
        + LF
        + "| --- | --- |"
        + LF
        + f"| Target | {target.resolve()} |"
        + LF
        + f"| Target git head | {git_head} |"
        + LF
        + f"| --task-e-redirect | {_yes_no(task_e_redirect)} |"
        + LF
        + f"| --no-schema-redirect | {_yes_no(no_schema_redirect)} |"
        + LF
        + f"| Generated at | {timestamp} |"
        + LF
        + LF
        + "## Cap-raise site (always applied)"
        + LF
        + LF
        + "| site_id | location | current | replacement | anchor |"
        + LF
        + "| --- | --- | --- | --- | --- |"
        + LF
        + cap_row
        + LF
        + task_e_section
    )


def _render_migration_index(timestamp: str) -> str:
    return (
        "# Migration Note — Hermes Skill-Creator Plugin"
        + LF
        + LF
        + "<!-- generated by hermes-skill-creator-patch --emit-migration-note; "
        + "do not edit by hand -->"
        + LF
        + LF
        + "| Field | Value |"
        + LF
        + "| --- | --- |"
        + LF
        + "| Source repo | https://github.com/anthropics/claude-plugins-official |"
        + LF
        + "| Source skillId | skill-creator |"
        + LF
        + "| Pinned upstream commit | TBD |"
        + LF
        + "| Plugin version | 0.1.0 |"
        + LF
        + f"| Generated at | {timestamp} |"
        + LF
        + LF
        + "## Documents in this set"
        + LF
        + LF
        + "- `MIGRATION.hermes-patch.md` — Script #1 patches "
        "(cap raise + 7 Task E sites)."
        + LF
        + "- `MIGRATION.skill-port.md` — migrated skill bindings (T3 inventory)."
        + LF
        + LF
        + "## How to apply"
        + LF
        + LF
        + "1. Run Script #1 against your user-owned Hermes checkout:"
        + LF
        + "   `uv run hermes-skill-creator-patch --apply --task-e-redirect "
        + "--target <hermes-checkout>`"
        + LF
        + "2. Run Script #1 with `--emit-migration-note` to regenerate this file."
        + LF
    )
