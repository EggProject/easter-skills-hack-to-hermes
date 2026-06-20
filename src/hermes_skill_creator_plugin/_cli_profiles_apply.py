"""Apply-step helpers (save / install / cache-clear) for cli_profiles audit.

Split from ``_cli_profiles_audit`` (WPS202 / WPS211).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import click

from hermes_skill_creator_plugin._cli_profiles_apply_safe import (
    _save_config_safe,
    _save_disabled_skills_safe,
)
from hermes_skill_creator_plugin._cli_profiles_diff import DESIRED_SKILL, NEVER_DISABLE

if TYPE_CHECKING:
    pass


def load_config_or_error(load_config: Any, errors: list[str], row: dict[str, Any]) -> dict[str, Any]:
    """Call ``load_config``; on failure record the error and return the row sentinel."""
    try:
        result = load_config()
    except Exception as exc:
        errors.append(f"load_config failed: {exc}")
        return row
    if not isinstance(result, dict):
        errors.append(f"load_config returned {type(result).__name__}, expected dict")
        return row
    return result


def read_disabled_or_empty(get_disabled_skill_names: Any, errors: list[str]) -> set[str]:
    """Read the currently-disabled skill names; fall back to an empty set on error."""
    try:
        return set(get_disabled_skill_names(platform=None))
    except Exception as exc:
        errors.append(f"get_disabled_skill_names failed: {exc}")
        return set()


@dataclasses.dataclass(frozen=True)
class _SaveDisabledArgs:
    """Group of inputs for :func:`apply_save_disabled` (bundled for WPS211)."""

    save_disabled_skills: Any
    save_config: Any
    config: Any
    desired_disabled: set[str]
    disabled_now: set[str]
    actions: list[str]
    errors: list[str]


def apply_save_disabled(args: _SaveDisabledArgs) -> None:
    """Persist the desired-disabled set when it actually changes."""
    if args.desired_disabled == args.disabled_now:
        return
    if not _save_disabled_skills_safe(
        args.save_disabled_skills,
        args.config,
        args.desired_disabled,
        args.errors,
    ):
        return
    args.actions.append("save_disabled_skills")
    if not _save_config_safe(args.save_config, args.config, args.errors):
        return
    args.actions.append("save_config")


def desired_disabled_after_save(disabled_now: set[str]) -> set[str]:
    """Return the desired-disabled set computed from the current snapshot."""
    return set(disabled_now) - NEVER_DISABLE


def apply_do_install(
    do_install: Any,
    row: dict[str, Any],
    actions: list[str],
    errors: list[str],
    bilingual_fn: Any,
) -> None:
    """Install (or refresh) the migrated skill-creator via the hub."""
    try:
        do_install(
            DESIRED_SKILL,
            category="",
            force=True,
            console=None,
            skip_confirm=True,
            invalidate_cache=True,
            name_override="",
        )
    except Exception as exc:
        msg = bilingual_fn(
            "profiles_msg_hub_error",
            name=row["profile_name"],
            err=exc,
        )
        click.echo(msg)
        errors.append(f"hub install failed: {exc}")
        return
    actions.append("do_install")


def apply_clear_cache(
    clear_skills_system_prompt_cache: Any,
    row: dict[str, Any],
    actions: list[str],
    errors: list[str],
    bilingual_fn: Any,
) -> None:
    """Clear the system-prompt cache (warn-and-continue on failure)."""
    try:
        clear_skills_system_prompt_cache(clear_snapshot=True)
    except Exception as exc:
        msg = bilingual_fn(
            "profiles_msg_cache_warn",
            name=row["profile_name"],
            err=exc,
        )
        click.echo(msg)
        errors.append(f"cache clear failed: {exc}")
        return
    actions.append("clear_skills_system_prompt_cache")
