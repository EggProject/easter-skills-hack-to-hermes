"""Filesystem helpers for the skill installer.

Extracted from ``skill_installer.py`` to keep that module under wemake
WPS202 (≤7 module members). Holds the refuse-live-install guard, the
``shutil.copy2`` walk over the source skill tree, and the SKILL.md
copy.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hermes_skill_creator_plugin._skill_installer_consts import (
    FULL_SKILL_MD_NAME,
    SKILL_DEST_REL_PARTS,
    STATE_UNPATCHED,
)
from hermes_skill_creator_plugin._skill_installer_consts import (
    LIVE_HERMES_AGENT as _LIVE_HERMES_AGENT,
)


def refuse_live_install(hermes_home: Path) -> None:
    message = (
        f"refusing to install to live Hermes install: {hermes_home}. "
        "Set HERMES_HOME to a tmp_path or pass --hermes-home explicitly."
    )
    raise ValueError(message)


def guard_install_preconditions(skill_source: Path, hermes_home: Path, live_agent: Path = _LIVE_HERMES_AGENT) -> None:
    if hermes_home.resolve() == live_agent.resolve():
        refuse_live_install(hermes_home)
    if not skill_source.exists():
        message = f"skill source not found: {skill_source}"
        raise FileNotFoundError(message)


def prepare_target_dir(hermes_home: Path) -> Path:
    target_dir = hermes_home.joinpath(*SKILL_DEST_REL_PARTS)
    # Re-install: clear the prior copy so leftover files from a previous
    # install (e.g. a SKILL.md.short from a prior unpatched-cap install)
    # do not shadow the new SKILL.md.
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    return target_dir


def copy_skill_tree(skill_source: Path, target_dir: Path) -> None:
    for child in skill_source.rglob("*"):
        rel = child.relative_to(skill_source)
        dst = target_dir / rel
        if child.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dst)


def select_skill_md(skill_dir: Path, *, cap: str) -> Path:
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
    return skill_dir / FULL_SKILL_MD_NAME


def copy_skill_md(src_md: Path, target_dir: Path) -> Path:
    target_md = target_dir / FULL_SKILL_MD_NAME
    shutil.copy2(src_md, target_md)
    return target_md
