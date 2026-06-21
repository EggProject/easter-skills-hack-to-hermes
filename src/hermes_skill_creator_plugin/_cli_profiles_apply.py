"""Apply-step helpers (save / install / cache-clear) for cli_profiles audit.

Split from ``_cli_profiles_audit`` (WPS202 / WPS211).
"""

from __future__ import annotations

import dataclasses
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_apply_io import (
    apply_clear_cache as _apply_clear_cache,
)
from hermes_skill_creator_plugin._cli_profiles_apply_io import (
    apply_do_install as _apply_do_install,
)
from hermes_skill_creator_plugin._cli_profiles_diff import NEVER_DISABLE

# Re-export so existing ``from _cli_profiles_apply import apply_clear_cache``
# keeps working after the WPS202 split.
apply_clear_cache = _apply_clear_cache
apply_do_install = _apply_do_install


def load_config_or_error(load_config: Any, errors: list[str], row: dict[str, Any]) -> Any:
    """Call ``load_config``; on failure record the error and return the row sentinel."""
    try:
        return load_config()
    except Exception as exc:
        errors.append(f"load_config failed: {exc}")
        return row


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


def _save_disabled_skills_safe(
    save_disabled_skills: Any,
    config: Any,
    desired_disabled: set[str],
    errors: list[str],
) -> bool:
    try:
        save_disabled_skills(config, sorted(desired_disabled), platform=None)
    except Exception as exc:
        errors.append(f"save_disabled_skills failed: {exc}")
        return False
    return True


def _save_config_safe(save_config: Any, config: Any, errors: list[str]) -> bool:
    try:
        save_config(config)
    except Exception as exc:
        errors.append(f"save_config failed: {exc}")
        return False
    return True


def desired_disabled_after_save(disabled_now: set[str]) -> set[str]:
    """Return the desired-disabled set computed from the current snapshot."""
    return set(disabled_now) - NEVER_DISABLE
