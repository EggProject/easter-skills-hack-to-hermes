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
from hermes_skill_creator_plugin._cli_profiles_walk import (
    read_gateway_pid_stat,
    walk_profile_subdirs,
)


def new_row(
    profile_path: Path,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build the initial empty row + convenience handles for actions/errors."""
    row: dict[str, Any] = empty_row(profile_path.name or "hermes")
    return row, row["actions_taken"], row["errors"]


def empty_row(profile_name: str) -> dict[str, Any]:
    """Return the baseline empty row dict (no convenience handles).

    ``subdirs`` and ``gateway_pid`` are populated by
    ``populate_walk_row`` (AC-3.10). They start empty so the JSON
    serialization is deterministic before the walk runs.
    """
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
        "subdirs": {},
        "gateway_pid": {"present": False, "size": 0, "mtime": 0},
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


def populate_walk_row(row: dict[str, Any], profile_path: Path) -> None:
    """Fill in the per-profile directory walk fields on ``row`` (AC-3.10).

    Calls ``walk_profile_subdirs`` for the canonical PROFILE_DIRS set
    and ``read_gateway_pid_stat`` for the flat ``gateway.pid`` file.
    """
    row["subdirs"] = walk_profile_subdirs(profile_path)
    row["gateway_pid"] = read_gateway_pid_stat(profile_path)


def build_diff(
    disabled_now: set[str],
    installed_now: set[str],
    desired_disabled: set[str],
    desired_installed: set[str],
) -> dict[str, list[str]]:
    diff_disabled = diff_sets(disabled_now, desired_disabled)
    diff_installed = diff_sets(installed_now, desired_installed)
    return _diff_payload(diff_disabled, diff_installed)


def _diff_payload(
    diff_disabled: dict[str, list[str]],
    diff_installed: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Assemble the four-key diff payload from per-set diff results."""
    return {
        "added_disabled": diff_disabled["added"],
        "removed_disabled": diff_disabled["removed"],
        "added_installed": diff_installed["added"],
        "removed_installed": diff_installed["removed"],
    }
