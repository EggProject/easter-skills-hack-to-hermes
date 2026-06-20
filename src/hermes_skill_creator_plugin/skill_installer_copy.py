"""Copy helpers for the skill installer.

Split from ``skill_installer`` (WPS202 module surface budget). The
tree-copy / SKILL.md-copy / target-prep helpers live here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hermes_skill_creator_plugin._skill_installer_consts import (
    FULL_SKILL_MD_NAME,
    SKILL_DEST_REL_PARTS,
)


def _copy_skill_tree(skill_source: Path, target_dir: Path) -> None:
    for child in skill_source.rglob("*"):
        rel = child.relative_to(skill_source)
        dst = target_dir / rel
        if child.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dst)


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
    target_md = target_dir / FULL_SKILL_MD_NAME
    shutil.copy2(src_md, target_md)
    return target_md
