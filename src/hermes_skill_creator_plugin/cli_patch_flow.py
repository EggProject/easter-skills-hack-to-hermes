"""Target-resolution + migration-note pre-flight flow for the patcher CLI.

Extracted from ``cli_patch.py`` to keep that module under wemake WPS202
(≤7 module members). Holds the small pre-patch helpers that decide
whether to refuse the run (``is_hermes_agent``), resolve the
``--target`` path, and emit a migration note on demand.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from hermes_skill_creator_plugin import _patcher as _patcher_mod
from hermes_skill_creator_plugin.cli_patch_git import git_head as _git_head
from hermes_skill_creator_plugin.i18n.messages_en import (
    MIGRATION_REGENERATED,
    TARGET_IS_HERMES_AGENT,
)

EXIT_OK = 0


def resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None


def refuse_hermes_agent(target_path: Path) -> None:
    click.echo(
        TARGET_IS_HERMES_AGENT.format(resolved=str(target_path)),
        err=True,
    )
    sys.exit(4)


def emit_migration_note_flow(
    target_path: Path,
    *,
    task_e_redirect: bool,
    no_schema_redirect: bool,
) -> None:
    if _patcher_mod.is_hermes_agent(target_path):
        refuse_hermes_agent(target_path)
    worktree = Path.cwd()
    git_head = _git_head(target_path)
    path = _patcher_mod.generate_migration_note(
        target=target_path,
        worktree=worktree,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        git_head=git_head,
    )
    click.echo(MIGRATION_REGENERATED.format(path=str(path)))
    sys.exit(EXIT_OK)
