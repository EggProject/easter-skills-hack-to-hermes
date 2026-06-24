"""Orchestrator for cli_profiles per-profile audit + apply.

Re-exports helpers from the split sub-modules so existing
``easter_hermes_sorry_skills.cli_profiles`` imports keep working.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from easter_hermes_sorry_skills import _cli_profiles_audit_bindings as _bindings
from easter_hermes_sorry_skills import _cli_profiles_audit_types as _types

# Pull in the centralized rebindings from the sibling
# ``_cli_profiles_*`` modules via the bindings module — keeps this
# orchestrator under wemake WPS201 (<=12 imports per module) and
# WPS202 (<=7 module members).
_SaveDisabledArgs = _bindings._SaveDisabledArgs
apply_clear_cache = _bindings.apply_clear_cache
apply_do_install = _bindings.apply_do_install
apply_save_disabled = _bindings.apply_save_disabled
desired_disabled_after_save = _bindings.desired_disabled_after_save
load_config_or_error = _bindings.load_config_or_error
read_disabled_or_empty = _bindings.read_disabled_or_empty
build_bilingual = _bindings.build_bilingual
diff_sets = _bindings.diff_sets
walk_skills = _bindings.walk_skills
walk_profile_subdirs = _bindings.walk_profile_subdirs
read_gateway_pid_stat = _bindings.read_gateway_pid_stat
PROFILE_DIRS = _bindings.PROFILE_DIRS
AuditReport = _bindings.AuditReport
new_row = _bindings.new_row
populate_diff_row = _bindings.populate_diff_row
populate_walk_row = _bindings.populate_walk_row
hermes_home_scope = _bindings.hermes_home_scope

# Re-bind the apply types for callers that import them from
# ``easter_hermes_sorry_skills._cli_profiles_audit``.
_ApplyDeps = _types._ApplyDeps
_ApplyCallArgs = _types._ApplyCallArgs
_ApplySlot = _types._ApplySlot


def audit_profile(
    profile_path: Path,
    *,
    apply: bool,
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
                bilingual_fn=bilingual_fn,
            )
        )
    return row


def _audit_load_or_error(
    profile_path: Path,
    errors: list[str],
    row: dict[str, Any],
) -> dict[str, Any]:
    """Load the scoped HERMES_HOME config; append error and return ``row`` sentinel on failure.

    Returns either the loaded config dict or the ``row`` sentinel (both
    ``dict[str, Any]``). ``load_config_or_error`` is typed ``Any`` for
    monkeypatch flexibility; the union of its two return paths is
    statically known to be ``dict[str, Any]``.
    """
    load_config: Callable[[], dict[str, Any]] | None
    try:
        from hermes_cli.config import load_config
    except ImportError:  # hermes_cli not installed in this venv
        load_config = None

    config = load_config_or_error(load_config, errors, row)
    # Look up the mutator at call time so monkeypatch.setattr on
    # the module works. The top-of-function import caches a
    # reference; the test infrastructure may rebind it.
    return cast("dict[str, Any]", config)


def _audit_disabled_now(errors: list[str]) -> set[str]:
    """Read the currently-disabled skill names; append error on failure."""
    get_disabled_skill_names: Callable[[], list[str]] | None
    try:
        from agent.skill_utils import get_disabled_skill_names
    except ImportError:
        get_disabled_skill_names = None

    return read_disabled_or_empty(get_disabled_skill_names, errors)


def _audit_diff_row(
    row: dict[str, Any],
    profile_path: Path,
    disabled_now: set[str],
) -> None:
    """Walk installed skills, the PROFILE_DIRS subdirs, and ``gateway.pid``.

    Populates the diff columns (installed vs. desired) and the AC-3.10
    walk fields (``subdirs``, ``gateway_pid``).
    """
    installed_now: set[str] = walk_skills(profile_path / "skills")
    populate_diff_row(row, disabled_now, installed_now)
    populate_walk_row(row, profile_path)


def _audit_apply(args: _ApplyCallArgs) -> dict[str, Any]:
    """Build the apply dep set and run the apply pipeline for one profile."""
    from agent.prompt_builder import clear_skills_system_prompt_cache

    save_config: Callable[[dict[str, Any]], None] | None
    try:
        from hermes_cli.config import save_config
    except ImportError:  # hermes_cli not installed in this venv
        save_config = None
    save_disabled_skills: Callable[[list[str]], None] | None
    try:
        from hermes_cli.skills_config import save_disabled_skills
    except ImportError:  # hermes_cli not installed in this venv
        save_disabled_skills = None
    do_install: Callable[..., Path] | None
    try:
        from hermes_cli.skills_hub import do_install
    except ImportError:  # hermes_cli not installed in this venv
        do_install = None

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
    )

    return args.row


def _run_apply(
    config: Any,
    disabled_now: set[str],
    deps: _ApplyDeps,
    *,
    slot: _ApplySlot,
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
