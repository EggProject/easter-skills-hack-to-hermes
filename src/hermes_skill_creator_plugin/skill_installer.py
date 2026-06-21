"""hermes_skill_creator_plugin.skill_installer — installs the migrated skill-creator.

The installer:
  1. Copies `skills/skill-creator/` (worktree root) into
     `HERMES_HOME/skills/skill-creator/` (flat, top-level deliverable).
  2. Emits `MIGRATION.skill-port.md` (worktree root) from the T3 inventory
     (18 rows; see docs/plans/07-skill-creator-migration.md).

NEVER writes to `~/.hermes/hermes-agent` (the live Hermes install). The
`HERMES_HOME` env var (or `--hermes-home`) selects the target.

Public API (``T3_INVENTORY``, ``InstallResult``, ``SHORT_DESC_CAP``,
``FULL_DESC_CAP``, ``PINNED_UPSTREAM_COMMIT``, ``detect_active_cap``,
``install``) is re-exported from this module.

Filesystem helpers (refuse-live guard, copy tree, copy SKILL.md) live in
``_skill_installer_io`` to keep this module under wemake WPS202 (≤7
module members).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hermes_skill_creator_plugin import _skill_installer_io as _io_mod
from hermes_skill_creator_plugin._skill_installer_cap import detect_active_cap
from hermes_skill_creator_plugin._skill_installer_note import (
    write_migration_note as _write_migration_note,
)

_copy_skill_md = _io_mod.copy_skill_md
_copy_skill_tree = _io_mod.copy_skill_tree
_guard_install_preconditions = _io_mod.guard_install_preconditions
_prepare_target_dir = _io_mod.prepare_target_dir
_select_skill_md = _io_mod.select_skill_md


@dataclass
class InstallResult:
    target_dir: Path
    selected_skill_md: Path
    migration_note: Path


def install(
    *,
    skill_source: Path,
    hermes_home: Path,
    worktree_root: Path,
    cap: str | None = None,
) -> InstallResult:
    """Install the migrated skill to ``hermes_home/skills/skill-creator/``.

    Emits ``MIGRATION.skill-port.md`` to ``worktree_root``. The destination
    is the flat path under HERMES_HOME so the skill appears in
    ``<available_skills>``. NEVER writes to the live
    ``~/.hermes/hermes-agent``.

    Args:
        skill_source: Path to ``skills/skill-creator/`` (worktree root).
        hermes_home: Path to the destination HERMES_HOME (must NOT be
            ``~/.hermes/hermes-agent``).
        worktree_root: Where to write ``MIGRATION.skill-port.md``.
        cap: "patched" (use SKILL.md, <= 1024) or "unpatched"
            (use SKILL.md.short, <= 60). If None, autodetect from the
            active checkout.

    Returns:
        InstallResult with the resolved paths.

    Raises:
        FileNotFoundError: if the source skill is missing.
        ValueError: if hermes_home resolves to the live install.
    """
    _guard_install_preconditions(skill_source, hermes_home)
    target_dir = _prepare_target_dir(hermes_home)
    _copy_skill_tree(skill_source, target_dir)
    chosen_cap = _resolve_cap(cap)
    src_md = _select_skill_md(skill_source, cap=chosen_cap)
    target_md = _copy_skill_md(src_md, target_dir)
    return _build_install_result(target_dir, target_md, worktree_root)


def _resolve_cap(cap: str | None) -> str:
    """Return ``cap`` if provided, else the autodetected cap."""
    if cap is not None:
        return cap
    return detect_active_cap()


def _build_install_result(
    target_dir: Path,
    target_md: Path,
    worktree_root: Path,
) -> InstallResult:
    migration_note = _write_migration_note(worktree_root)
    return InstallResult(
        target_dir=target_dir,
        selected_skill_md=target_md,
        migration_note=migration_note,
    )
