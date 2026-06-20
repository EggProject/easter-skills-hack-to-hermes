"""Load-phase helpers for ``_cli_profiles_audit``.

Split from ``_cli_profiles_audit`` (WPS202 module surface budget). These
helpers build the per-profile row state by reading the scoped HERMES_HOME
config + the disabled-skill list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_apply import (
    load_config_or_error,
    read_disabled_or_empty,
)
from hermes_skill_creator_plugin._cli_profiles_diff import walk_skills
from hermes_skill_creator_plugin._cli_profiles_row import populate_diff_row


def _audit_load_or_error(profile_path: Path, errors: list[str], row: dict[str, Any]) -> dict[str, Any]:
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
