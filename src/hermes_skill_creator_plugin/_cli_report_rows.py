"""src/hermes_skill_creator_plugin/_cli_report_rows.py

Row construction for the reporter: usage rows, profile rows, json-path safety.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin._cli_report_rows_profile import (
    _build_skill_rows,
    _enabled_skills_safe,
)
from hermes_skill_creator_plugin._cli_report_rows_usage import (
    _empty_usage_map,
    _filled_usage_map,
)
from hermes_skill_creator_plugin._reporter import SkillRow

if TYPE_CHECKING:
    pass


class EnabledDetectionUnavailable(Exception):
    """Raised when get_enabled_skills is unavailable."""


def build_usage_rows(
    curator: Any | None,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    """Build a name -> usage-fields map. None values when not persisted."""
    if curator is None:
        return _empty_usage_map(enabled_names)
    return _filled_usage_map(curator, skills_dir, enabled_names)


def build_rows_for_profile(
    profile: Path,
    *,
    platform: str | None,
    curator: Any | None,
    estimate_tokens_fn: Any,
    enabled_skills_fn: Any,
) -> tuple[list[SkillRow], int]:
    """Build the SkillRow list and total_tokens for `profile`."""
    enabled = _enabled_skills_safe(
        profile=profile,
        platform=platform,
        fn=enabled_skills_fn,
    )
    skills_dir = profile / "skills"
    usage = build_usage_rows(curator, skills_dir, enabled)
    return _build_skill_rows(
        profile=profile,
        skills_dir=skills_dir,
        usage=usage,
        enabled=enabled,
        estimate_tokens_fn=estimate_tokens_fn,
    )


def check_json_path(json_path: Path, hermes_home: Path) -> bool:
    """Return True when json_path resolves inside hermes_home."""
    try:
        resolved = json_path.resolve()
    except OSError:
        return False
    try:
        home_resolved = hermes_home.resolve()
    except OSError:
        return False
    if resolved == home_resolved:
        return True
    return home_resolved in resolved.parents
