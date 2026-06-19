"""hermes_skill_creator_plugin.skill_installer — installs the migrated skill-creator.

The installer:
  1. Copies `skills/skill-creator/` (worktree root) into
     `HERMES_HOME/skills/skill-creator/` (flat, top-level deliverable).
  2. Emits `MIGRATION.skill-port.md` (worktree root) from the T3 inventory
     (18 rows; see docs/plans/07-skill-creator-migration.md).

NEVER writes to `~/.hermes/hermes-agent` (the live Hermes install). The
`HERMES_HOME` env var (or `--hermes-home`) selects the target.

The constant table, the T3 inventory, the migration-note renderer, and
the cap-detection routine live in sibling modules to keep this file
under wemake WPS202 (module members <= 7):

- :mod:`._skill_installer_consts` — keys, state strings, paths.
- :mod:`._skill_installer_t3` — the 18-row T3 inventory.
- :mod:`._skill_installer_note` — migration-note renderer + writer.
- :mod:`._skill_installer_cap` — active-cap detection.

Public API (``T3_INVENTORY``, ``InstallResult``, ``SHORT_DESC_CAP``,
``FULL_DESC_CAP``, ``PINNED_UPSTREAM_COMMIT``, ``detect_active_cap``,
``install``) is re-exported from this module.

TDD test cases for this module:
  test_skill_creator_home_has_skills_and_profiles_dirs
  test_installer_copies_skill_to_hermes_home_skills_dir
  test_installer_emits_migration_skill_port_md
  test_migration_skill_port_has_18_t3_rows
  test_migration_skill_port_deterministic_under_frozen_time
  test_migration_skill_port_mentions_anthropic_provenance
  test_installer_writes_only_to_hermes_home_and_worktree
  test_installer_refuses_to_write_to_live_hermes_agent
  test_installer_selects_short_or_full_description_per_active_cap
  test_detect_active_cap_raises_when_skill_utils_missing
  test_install_raises_when_skill_source_missing
  test_install_raises_when_short_skill_md_missing
  test_install_autodetects_cap
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from hermes_skill_creator_plugin._skill_installer_cap import detect_active_cap
from hermes_skill_creator_plugin._skill_installer_consts import (
    FULL_DESC_CAP,
    PINNED_UPSTREAM_COMMIT,
    SHORT_DESC_CAP,
    SKILL_DEST_REL_PARTS,
    STATE_UNPATCHED,
)
from hermes_skill_creator_plugin._skill_installer_consts import (
    LIVE_HERMES_AGENT as _LIVE_HERMES_AGENT,
)
from hermes_skill_creator_plugin._skill_installer_note import (
    write_migration_note as _write_migration_note,
)
from hermes_skill_creator_plugin._skill_installer_t3 import T3_INVENTORY


@dataclass
class InstallResult:
    target_dir: Path
    selected_skill_md: Path
    migration_note: Path


def _refuse_live_install(hermes_home: Path) -> None:
    message = (
        f"refusing to install to live Hermes install: {hermes_home}. "
        "Set HERMES_HOME to a tmp_path or pass --hermes-home explicitly."
    )
    raise ValueError(message)


def _copy_skill_tree(skill_source: Path, target_dir: Path) -> None:
    for child in skill_source.rglob("*"):
        rel = child.relative_to(skill_source)
        dst = target_dir / rel
        if child.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dst)


def _select_skill_md(skill_dir: Path, *, cap: str) -> Path:
    """Select SKILL.md.short (cap=unpatched) or SKILL.md (cap=patched)."""
    if cap == STATE_UNPATCHED:
        from hermes_skill_creator_plugin._skill_installer_consts import (
            SHORT_SKILL_MD_NAME,
        )

        short = skill_dir / SHORT_SKILL_MD_NAME
        if not short.exists():
            message = f"SKILL.md.short not found in {skill_dir}; cannot install under 60-char cap"
            raise FileNotFoundError(message)
        return short
    from hermes_skill_creator_plugin._skill_installer_consts import (
        FULL_SKILL_MD_NAME,
    )

    return skill_dir / FULL_SKILL_MD_NAME


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


def _guard_install_preconditions(skill_source: Path, hermes_home: Path) -> None:
    if hermes_home.resolve() == _LIVE_HERMES_AGENT.resolve():
        _refuse_live_install(hermes_home)
    if not skill_source.exists():
        message = f"skill source not found: {skill_source}"
        raise FileNotFoundError(message)


def _prepare_target_dir(hermes_home: Path) -> Path:
    target_dir = hermes_home.joinpath(*SKILL_DEST_REL_PARTS)
    # Re-install: clear the prior copy so leftover files from a previous
    # install (e.g. a SKILL.md.short from a prior unpatched-cap install)
    # do not shadow the new SKILL.md.
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    return target_dir


def _copy_skill_md(src_md: Path, target_dir: Path) -> Path:
    from hermes_skill_creator_plugin._skill_installer_consts import (
        FULL_SKILL_MD_NAME,
    )

    target_md = target_dir / FULL_SKILL_MD_NAME
    shutil.copy2(src_md, target_md)
    return target_md


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


__all__ = [
    "T3_INVENTORY",
    "InstallResult",
    "SHORT_DESC_CAP",
    "FULL_DESC_CAP",
    "PINNED_UPSTREAM_COMMIT",
    "detect_active_cap",
    "install",
]
