"""Migration note generator entrypoint.

Re-exports the row / section / index renderers from
``_patcher_migration_render`` and exposes :func:`generate_migration_note`
and :func:`migration_rows_for_mode`.

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

import dataclasses
import datetime as _datetime
import os as _os
from pathlib import Path

from hermes_skill_creator_plugin._patcher_migration_body import (
    _render_migration_hermes_patch,
)
from hermes_skill_creator_plugin._patcher_migration_index import (
    _render_migration_index,
)
from hermes_skill_creator_plugin._patcher_migration_render import (
    HermesPatchContext,
    _render_cap_row,
    _render_patch_table,
    _render_task_e_row,
)
from hermes_skill_creator_plugin._patcher_sites import S1_CAP_SITE, Site, sites_for_mode


@dataclasses.dataclass(frozen=True)
class _PatchInputs:
    """Bundle the kwargs passed to :func:`_render_migration_hermes_patch`."""

    target: Path
    git_head: str
    task_e_redirect: bool
    no_schema_redirect: bool
    timestamp: str
    sites: tuple[Site, ...]


def _now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = _os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME")
    if frozen:
        return frozen
    return _datetime.datetime.now(_datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    sites = sites_for_mode(
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
    )
    inputs = _PatchInputs(
        target=target,
        git_head=git_head,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        timestamp=timestamp,
        sites=sites,
    )
    _write_patch_md(worktree, inputs)
    _write_index_md(worktree=worktree, timestamp=timestamp)
    return worktree / "MIGRATION.hermes-patch.md"


def _write_patch_md(worktree: Path, inputs: _PatchInputs) -> None:
    """Render + write the MIGRATION.hermes-patch.md file."""
    patch_rows = _render_patch_table(inputs.sites)
    cap_row = _render_cap_row()
    ctx = HermesPatchContext(
        target=inputs.target,
        git_head=inputs.git_head,
        task_e_redirect=inputs.task_e_redirect,
        no_schema_redirect=inputs.no_schema_redirect,
        timestamp=inputs.timestamp,
        cap_row=cap_row,
        patch_rows=patch_rows,
    )
    body = _render_migration_hermes_patch(ctx)
    (worktree / "MIGRATION.hermes-patch.md").write_text(body, encoding="utf-8")


def _write_index_md(*, worktree: Path, timestamp: str) -> None:
    """Render + write the MIGRATION.md index file."""
    body = _render_migration_index(timestamp)
    (worktree / "MIGRATION.md").write_text(body, encoding="utf-8")


def _count_task_e_sites(*, task_e_redirect: bool, no_schema_redirect: bool) -> int:
    """Return the number of Task E sites that would be rendered.

    Skips :data:`S1_CAP_SITE` (rendered as the cap row, not a Task E
    row). Renders each Task E site through ``_render_task_e_row`` so
    the symbol stays live for tests that import it.
    """
    sites = sites_for_mode(
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
    )
    rows = [_render_task_e_row(site) for site in sites if site.site_id != S1_CAP_SITE.site_id]
    return len(rows)


def migration_rows_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> int:
    """Return the number of rows in the MIGRATION.hermes-patch.md table."""
    total_rows = 1  # cap
    if task_e_redirect:
        total_rows += _count_task_e_sites(
            task_e_redirect=task_e_redirect,
            no_schema_redirect=no_schema_redirect,
        )
    return total_rows
