"""Orchestrator for cli_profiles per-profile audit + apply.

Re-exports helpers from the split sub-modules so existing
``hermes_skill_creator_plugin.cli_profiles`` imports keep working.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_audit_apply import (
    _ApplyCallArgs,
    _audit_apply,
)
from hermes_skill_creator_plugin._cli_profiles_audit_load import (
    _audit_diff_row,
    _audit_disabled_now,
    _audit_load_or_error,
)
from hermes_skill_creator_plugin._cli_profiles_row import new_row
from hermes_skill_creator_plugin._scope import hermes_home_scope


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
            ),
        )
    return row
