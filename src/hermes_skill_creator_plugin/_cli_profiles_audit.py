"""Orchestrator for cli_profiles per-profile audit + apply.

Re-exports helpers from the split sub-modules so existing
``hermes_skill_creator_plugin.cli_profiles`` imports keep working.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_apply import (
    apply_clear_cache,
    apply_do_install,
    apply_save_disabled,
    desired_disabled_after_save,
    load_config_or_error,
    read_disabled_or_empty,
)
from hermes_skill_creator_plugin._cli_profiles_bilingual import (
    build_bilingual as build_bilingual,
)
from hermes_skill_creator_plugin._cli_profiles_diff import (
    diff_sets as diff_sets,
)
from hermes_skill_creator_plugin._cli_profiles_diff import walk_skills
from hermes_skill_creator_plugin._cli_profiles_report import (
    AuditReport as AuditReport,
)
from hermes_skill_creator_plugin._cli_profiles_row import new_row, populate_diff_row
from hermes_skill_creator_plugin._scope import hermes_home_scope


@dataclasses.dataclass(frozen=True)
class _ApplyDeps:
    """Lazily-bound callables captured inside ``hermes_home_scope``."""

    save_disabled_skills: Any
    save_config: Any
    do_install: Any
    clear_skills_system_prompt_cache: Any
    bilingual_fn: Any


def audit_profile(
    profile_path: Path,
    *,
    apply: bool,
    skip_install: bool,
    frozen_time: str | None,
    bilingual_fn: Any,
) -> dict[str, Any]:
    """Audit (and optionally apply) a single profile.

    Returns the per-profile row of the report. The call runs inside
    ``hermes_home_scope(profile_path)`` so all ``load_config`` /
    ``do_install`` / ``save_config`` calls resolve against the
    scoped HERMES_HOME (per plan 06 D4 + AC-3.4 / AC-3.6).
    """
    row, actions, errors = new_row(profile_path)
    with hermes_home_scope(profile_path):
        config = _audit_load_or_error(profile_path, errors, row)
        if config is row:
            return row
        disabled_now = _audit_disabled_now(errors)
        _audit_diff_row(row, profile_path, disabled_now)
        if not apply:
            return row
        _audit_apply(
            _ApplyCallArgs(
                config=config,
                disabled_now=disabled_now,
                row=row,
                actions=actions,
                errors=errors,
                profile_path=profile_path,
                skip_install=skip_install,
                bilingual_fn=bilingual_fn,
            )
        )
    return row


def _audit_load_or_error(profile_path: Path, errors: list[str], row: dict[str, Any]) -> Any:
    """Load the scoped HERMES_HOME config; append error and return ``row`` sentinel on failure."""
    from hermes_cli.config import load_config

    config = load_config_or_error(load_config, errors, row)
    # Look up the mutator at call time so monkeypatch.setattr on
    # the module works. The top-of-function import caches a
    # reference; the test infrastructure may rebind it.
    return config


def _audit_disabled_now(errors: list[str]) -> set[str]:
    """Read the currently-disabled skill names; append error on failure."""
    from agent.skill_utils import get_disabled_skill_names

    return read_disabled_or_empty(get_disabled_skill_names, errors)


def _audit_diff_row(
    row: dict[str, Any],
    profile_path: Path,
    disabled_now: set[str],
) -> None:
    """Walk installed skills and populate the diff columns on ``row``."""
    installed_now: set[str] = walk_skills(profile_path / "skills")
    populate_diff_row(row, disabled_now, installed_now)


@dataclasses.dataclass(frozen=True)
class _ApplyCallArgs:
    """Per-profile args for the apply pipeline (bundled to stay under WPS211)."""

    config: Any
    disabled_now: set[str]
    row: dict[str, Any]
    actions: list[str]
    errors: list[str]
    profile_path: Path
    skip_install: bool
    bilingual_fn: Any


def _audit_apply(args: _ApplyCallArgs) -> dict[str, Any]:
    """Build the apply dep set and run the apply pipeline for one profile."""
    from agent.prompt_builder import clear_skills_system_prompt_cache
    from hermes_cli.config import save_config
    from hermes_cli.skills_config import save_disabled_skills
    from hermes_cli.skills_hub import do_install

    deps = _ApplyDeps(
        save_disabled_skills=save_disabled_skills,
        save_config=save_config,
        do_install=do_install,
        clear_skills_system_prompt_cache=clear_skills_system_prompt_cache,
        bilingual_fn=args.bilingual_fn,
    )
    slot = _ApplySlot(row=args.row, actions=args.actions, errors=args.errors)
    _run_apply(
        args.config,
        args.disabled_now,
        deps,
        slot=slot,
        skip_install=args.skip_install,
    )

    return args.row


@dataclasses.dataclass(frozen=True)
class _ApplySlot:
    """Per-profile mutable row + action log + error log (bundled for WPS211)."""

    row: dict[str, Any]
    actions: list[str]
    errors: list[str]


def _run_apply(
    config: Any,
    disabled_now: set[str],
    deps: _ApplyDeps,
    *,
    slot: _ApplySlot,
    skip_install: bool,
) -> None:
    apply_save_disabled(
        deps.save_disabled_skills,
        deps.save_config,
        config,
        desired_disabled_after_save(disabled_now),
        disabled_now,
        slot.actions,
        slot.errors,
    )
    if not skip_install:
        apply_do_install(
            deps.do_install,
            slot.row,
            slot.actions,
            slot.errors,
            deps.bilingual_fn,
        )
    apply_clear_cache(
        deps.clear_skills_system_prompt_cache,
        slot.row,
        slot.actions,
        slot.errors,
        deps.bilingual_fn,
    )


__all__ = [
    "build_bilingual",
    "diff_sets",
    "AuditReport",
    "audit_profile",
    "walk_skills",
]
