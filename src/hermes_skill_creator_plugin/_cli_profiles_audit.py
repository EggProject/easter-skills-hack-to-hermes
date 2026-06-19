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
from hermes_skill_creator_plugin._cli_profiles_bilingual import build_bilingual as build_bilingual
from hermes_skill_creator_plugin._cli_profiles_diff import diff_sets as diff_sets, walk_skills
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport as AuditReport
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
    from agent.prompt_builder import clear_skills_system_prompt_cache
    from agent.skill_utils import get_disabled_skill_names
    from hermes_cli.config import load_config, save_config
    from hermes_cli.skills_hub import do_install

    row, actions, errors = new_row(profile_path)
    with hermes_home_scope(profile_path):
        # Look up the mutator at call time so monkeypatch.setattr on
        # the module works. The top-of-function import caches a
        # reference; the test infrastructure may rebind it.
        from hermes_cli.skills_config import save_disabled_skills

        config = load_config_or_error(load_config, errors, row)
        if config is row:
            return row

        disabled_now = read_disabled_or_empty(get_disabled_skill_names, errors)
        installed_now: set[str] = walk_skills(profile_path / "skills")
        populate_diff_row(row, disabled_now, installed_now)

        if not apply:
            return row

        deps = _ApplyDeps(
            save_disabled_skills=save_disabled_skills,
            save_config=save_config,
            do_install=do_install,
            clear_skills_system_prompt_cache=clear_skills_system_prompt_cache,
            bilingual_fn=bilingual_fn,
        )
        _run_apply(
            row,
            config,
            disabled_now,
            deps,
            skip_install=skip_install,
            actions=actions,
            errors=errors,
        )

    return row


def _run_apply(
    row: dict[str, Any],
    config: Any,
    disabled_now: set[str],
    deps: _ApplyDeps,
    *,
    skip_install: bool,
    actions: list[str],
    errors: list[str],
) -> None:
    apply_save_disabled(
        deps.save_disabled_skills,
        deps.save_config,
        config,
        desired_disabled_after_save(disabled_now),
        disabled_now,
        actions,
        errors,
    )
    if not skip_install:
        apply_do_install(deps.do_install, row, actions, errors, deps.bilingual_fn)
    apply_clear_cache(
        deps.clear_skills_system_prompt_cache,
        row,
        actions,
        errors,
        deps.bilingual_fn,
    )
