"""Migration note generator: ``MIGRATION.md`` index + ``MIGRATION.hermes-patch.md``.

Script #1's ``--emit-migration-note`` writes a deterministic pair of
markdown files to the WORKTREE root (NOT to --target per plans/04
§Migration note row counts + plans/08 §Determinism). The two files
serve two audiences:

- ``MIGRATION.hermes-patch.md`` — the patch site table (S1.cap + 7
  Task E sites). Per-row schema: site_id | location | current |
  replacement | anchor. The ``anchor`` column is REQUIRED for every
  row (plans/08 §MIGRATION.hermes-patch.md). Cap row anchor is
  ``if len(desc) > 60:`` (the primary comparator line). Task E row
  anchors are the byte-exact single-line locator for each site
  (E1=``"Skills that aren't maintained become liabilities."``, etc.).

- ``MIGRATION.md`` — the top-level index pointing at the two files in
  the set. Plain operator-facing "how to apply" instructions.

Determinism (plans/08 D6) is enforced by:

- Using ``HERMES_SKILL_CREATOR_FROZEN_TIME`` (set by CI) so the
  ``Generated at`` timestamp is stable across runs.
- LF line endings; no trailing whitespace.
- Tables sorted by ``site_id`` (the site table itself is fixed-order).

See also: plans/04-script-1-patch.md, plans/05-script-1-task-e-toggle.md,
plans/08-migration-note-format.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import Iterable
from pathlib import Path

from hermes_skill_creator_plugin._patcher_sites import S1_CAP_SITE, Site, sites_for_mode

# Cap-raise row anchor (the primary 8+ char anchor for S1.cap).
# The 5-column schema is: site_id | location | current | replacement | anchor.
S1_CAP_ROW_ANCHOR = "if len(desc) > 60:"


def _now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME")
    if frozen:
        return frozen
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "(with `MAX_DESCRIPTION_LENGTH` defined locally, e.g. "
        "`MAX_DESCRIPTION_LENGTH = 1024`, to avoid a circular import from "
        "`tools.skills_tool`) "
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
    anchor_text = _truncate(site.primary_anchor().text, 60)
    return (
        f"| {site.site_id} | {site.file}:{site.line_for_state} "
        f"(L{site.line_for_state}: `{anchor_text}`; "
        f"single physical line) | (preserved verbatim) | "
        f"`{_truncate(site.insertion.rstrip(chr(10)), 80)}` (additive) "
        f"| `{anchor_text}` |"
    )


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", "\\n")
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


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
            "\n## Task E sites (only if --task-e-redirect)\n\n"
            "| site_id | location | current | replacement | anchor |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{rows_text}\n"
        )
    body = (
        "# Hermes Patch — Script #1 (cap raise + 7 Task E sites)\n"
        "\n"
        "<!-- generated; do not edit by hand -->\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| Target | {target.resolve()} |\n"
        f"| Target git head | {git_head} |\n"
        f"| --task-e-redirect | {'yes' if task_e_redirect else 'no'} |\n"
        f"| --no-schema-redirect | {'yes' if no_schema_redirect else 'no'} |\n"
        f"| Generated at | {timestamp} |\n"
        "\n"
        "## Cap-raise site (always applied)\n"
        "\n"
        "| site_id | location | current | replacement | anchor |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{cap_row}\n"
        f"{task_e_section}"
    )
    return body


def _render_migration_index(timestamp: str) -> str:
    return (
        "# Migration Note — Hermes Skill-Creator Plugin\n"
        "\n"
        "<!-- generated by hermes-skill-creator-patch --emit-migration-note; "
        "do not edit by hand -->\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Source repo | https://github.com/anthropics/claude-plugins-official |\n"
        "| Source skillId | skill-creator |\n"
        "| Pinned upstream commit | TBD |\n"
        "| Plugin version | 0.1.0 |\n"
        f"| Generated at | {timestamp} |\n"
        "\n"
        "## Documents in this set\n"
        "\n"
        "- `MIGRATION.hermes-patch.md` — Script #1 patches (cap raise + 7 Task E sites).\n"
        "- `MIGRATION.skill-port.md` — migrated skill bindings (T3 inventory).\n"
        "\n"
        "## How to apply\n"
        "\n"
        "1. Run Script #1 against your user-owned Hermes checkout:\n"
        "   `uv run hermes-skill-creator-patch --apply --task-e-redirect "
        "--target <hermes-checkout>`\n"
        "2. Run Script #1 with `--emit-migration-note` to regenerate this file.\n"
    )


def generate_migration_note(
    *,
    target: Path,
    worktree: Path,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    git_head: str = "",
) -> Path:
    """Render ``MIGRATION.hermes-patch.md`` and ``MIGRATION.md`` index.

    The two files land in the worktree root, NOT in --target (per
    plans/04 §Migration note row counts + plans/08 §Determinism).
    Returns the path to ``MIGRATION.hermes-patch.md``.
    """
    timestamp = _now_iso()
    sites = sites_for_mode(task_e_redirect=task_e_redirect, no_schema_redirect=no_schema_redirect)
    patch_rows = _render_patch_table(sites)
    cap_row = _render_cap_row()
    patch_md = _render_migration_hermes_patch(
        target=target,
        git_head=git_head,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        timestamp=timestamp,
        cap_row=cap_row,
        patch_rows=patch_rows,
    )
    (worktree / "MIGRATION.hermes-patch.md").write_text(patch_md, encoding="utf-8")
    index_md = _render_migration_index(timestamp)
    (worktree / "MIGRATION.md").write_text(index_md, encoding="utf-8")
    return worktree / "MIGRATION.hermes-patch.md"


def migration_rows_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> int:
    """Return the number of rows in the MIGRATION.hermes-patch.md table."""
    n = 1  # cap
    if task_e_redirect:
        n += 7
        if no_schema_redirect:
            n -= 1
    return n
