"""Apply-phase helpers for ``_cli_profiles_audit``.

Split from ``_cli_profiles_audit`` (WPS202 module surface budget). The
apply pipeline wires the apply-deps dataclass + the per-call args
dataclass + the per-slot dataclass, then runs the public apply helpers.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_apply import (
    _SaveDisabledArgs,
    apply_clear_cache,
    apply_do_install,
    apply_save_disabled,
    desired_disabled_after_save,
)


@dataclasses.dataclass(frozen=True)
class _ApplyDeps:
    """Lazily-bound callables captured inside ``hermes_home_scope``."""

    save_disabled_skills: Any
    save_config: Any
    do_install: Any
    clear_skills_system_prompt_cache: Any
    bilingual_fn: Any


@dataclasses.dataclass(frozen=True)
class _ApplyCallArgs:
    """Per-profile args for the apply pipeline (bundled to stay under WPS211)."""

    config: Any
    disabled_now: set[str]
    row: dict[str, Any]
    actions: list[str]
    errors: list[str]
    profile_path: Any  # Path, kept as Any to avoid extra import
    skip_install: bool
    bilingual_fn: Any


@dataclasses.dataclass(frozen=True)
class _ApplySlot:
    """Per-profile mutable row + action log + error log (bundled for WPS211)."""

    row: dict[str, Any]
    actions: list[str]
    errors: list[str]


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


def _run_apply(
    config: Any,
    disabled_now: set[str],
    deps: _ApplyDeps,
    *,
    slot: _ApplySlot,
    skip_install: bool,
) -> None:
    apply_save_disabled(
        _SaveDisabledArgs(
            save_disabled_skills=deps.save_disabled_skills,
            save_config=deps.save_config,
            config=config,
            desired_disabled=desired_disabled_after_save(disabled_now),
            disabled_now=disabled_now,
            actions=slot.actions,
            errors=slot.errors,
        ),
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
