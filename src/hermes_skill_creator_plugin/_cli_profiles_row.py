"""Row scaffolding for the per-profile audit/apply report.

Split from ``_cli_profiles_audit`` (WPS202 / WPS210 / WPS221).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_profiles_diff import (
    DESIRED_SKILL,
    NEVER_DISABLE,
    diff_sets,
)


def new_row(profile_path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build the initial empty row + convenience handles for actions/errors."""
    row: dict[str, Any] = empty_row(profile_path.name or "hermes")
    return row, row["actions_taken"], row["errors"]


def empty_row(profile_name: str) -> dict[str, Any]:
    """Return the baseline empty row dict (no convenience handles)."""
    return {
        "profile_name": profile_name,
        "current_disabled": [],
        "current_installed": [],
        "desired_disabled": [],
        "desired_installed": [],
        "diff": {
            "added_disabled": [],
            "removed_disabled": [],
            "added_installed": [],
            "removed_installed": [],
        },
        "actions_taken": [],
        "errors": [],
    }


def populate_diff_row(
    row: dict[str, Any],
    disabled_now: set[str],
    installed_now: set[str],
) -> None:
    """Fill in current/desired/diff sub-fields on ``row``."""
    desired_disabled: set[str] = set(disabled_now) - NEVER_DISABLE
    desired_installed: set[str] = set(installed_now) | {DESIRED_SKILL}
    row["current_disabled"] = sorted(disabled_now)
    row["current_installed"] = sorted(installed_now)
    row["desired_disabled"] = sorted(desired_disabled)
    row["desired_installed"] = sorted(desired_installed)
    row["diff"] = build_diff(disabled_now, installed_now, desired_disabled, desired_installed)


def build_diff(
    disabled_now: set[str],
    installed_now: set[str],
    desired_disabled: set[str],
    desired_installed: set[str],
) -> dict[str, list[str]]:
    diff_disabled = diff_sets(disabled_now, desired_disabled)
    diff_installed = diff_sets(installed_now, desired_installed)
    return {
        "added_disabled": diff_disabled["added"],
        "removed_disabled": diff_disabled["removed"],
        "added_installed": diff_installed["added"],
        "removed_installed": diff_installed["removed"],
    }