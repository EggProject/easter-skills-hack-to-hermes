"""Row construction for the reporter: usage rows, profile rows, json-path safety.

The usage-map building helpers (safe-wrappers around the curator) live
in ``_cli_report_rows_usage`` to keep this module under wemake WPS202
(≤7 module members).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin import _cli_report_rows_usage as _usage_mod
from hermes_skill_creator_plugin._cli_report_helpers_consts import (
    EMPTY_USAGE,
)
from hermes_skill_creator_plugin._cli_report_helpers_parse import (
    emit_tokenizer_warning,
)
from hermes_skill_creator_plugin._cli_report_helpers_paths import load_skill_description
from hermes_skill_creator_plugin._reporter import SkillRow, make_row
from hermes_skill_creator_plugin._reporter_sort import _RowFields


class EnabledDetectionUnavailable(Exception):
    """Raised when get_enabled_skills is unavailable."""


def build_usage_rows(
    curator: Any | None,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    """Build a name -> usage-fields map. None values when not persisted."""
    if curator is None:
        return _usage_mod.empty_usage_map(enabled_names)
    return _usage_mod.filled_usage_map(curator, skills_dir, enabled_names)


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


def _enabled_skills_safe(*, profile: Path, platform: str | None, fn: Any) -> frozenset[str]:
    """Call ``enabled_skills_fn`` and raise :class:`EnabledDetectionUnavailable`."""
    try:
        return _usage_mod.call_enabled_skills_fn(profile, platform, fn)
    except Exception as exc:
        raise EnabledDetectionUnavailable(str(exc)) from None


def _build_skill_rows(
    *,
    profile: Path,
    skills_dir: Path,
    usage: dict[str, dict[str, Any]],
    enabled: frozenset[str],
    estimate_tokens_fn: Any,
) -> tuple[list[SkillRow], int]:
    """Build the SkillRow list and total_tokens."""
    rows: list[SkillRow] = []
    total = 0
    for name in sorted(enabled):
        row, tokens = _make_one_row(
            profile=profile,
            name=name,
            skills_dir=skills_dir,
            usage=usage,
            estimate_tokens_fn=estimate_tokens_fn,
        )
        rows.append(row)
        total += tokens
    return rows, total


def _make_one_row(
    *,
    profile: Path,
    name: str,
    skills_dir: Path,
    usage: dict[str, dict[str, Any]],
    estimate_tokens_fn: Any,
) -> tuple[SkillRow, int]:
    """Build a single SkillRow (and its token count)."""
    description = load_skill_description(skills_dir, name)
    tokens = estimate_tokens_fn(name, description, warning=emit_tokenizer_warning)
    usage_for = usage.get(name, EMPTY_USAGE)
    row = make_row(
        _RowFields(
            profile=profile.name,
            name=name,
            description=description,
            tokens=tokens,
            use_count=usage_for["use_count"],
            view_count=usage_for["view_count"],
            patch_count=usage_for["patch_count"],
            last_used_at=usage_for["last_used_at"],
            last_viewed_at=usage_for["last_viewed_at"],
            last_patched_at=usage_for["last_patched_at"],
        ),
    )
    return row, tokens


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
