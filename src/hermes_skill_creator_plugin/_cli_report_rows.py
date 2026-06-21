"""src/hermes_skill_creator_plugin/_cli_report_rows.py

Row construction for the reporter: usage rows, profile rows, json-path safety.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_report_helpers import (
    EMPTY_USAGE,
    PERSISTED_KEY,
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
        return _empty_usage_map(enabled_names)
    return _filled_usage_map(curator, skills_dir, enabled_names)


def _empty_usage_map(enabled_names: frozenset[str]) -> dict[str, dict[str, Any]]:
    return {name: {**EMPTY_USAGE, PERSISTED_KEY: False} for name in enabled_names}


def _filled_usage_map(
    curator: Any,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    out = _filled_usage_map_for_report(curator, skills_dir, enabled_names)
    out = _backfill_missing_usage(out, enabled_names)
    return out


def _filled_usage_map_for_report(
    curator: Any,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    report = _usage_report_safe(curator, skills_dir)
    for entry in report:
        entry_name = _entry_name(entry)
        if entry_name is None or entry_name not in enabled_names:
            continue
        out[entry_name] = _entry_fields(entry)
    return out


def _backfill_missing_usage(
    out: dict[str, dict[str, Any]],
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    for enabled_name in enabled_names:
        if enabled_name not in out:
            out[enabled_name] = {**EMPTY_USAGE, PERSISTED_KEY: False}
    return out


def _usage_report_safe(curator: Any, skills_dir: Path) -> list[Any]:
    """Call ``curator.usage_report`` and return [] on any error."""
    try:
        report = curator.usage_report(skills_dir=skills_dir)
    except Exception:
        return []
    return report or []


def _entry_name(entry: Any) -> str | None:
    """Return ``entry.name`` if it is a string, else ``None``."""
    raw_name = getattr(entry, "name", None)
    if isinstance(raw_name, str) and raw_name:
        return raw_name
    return None


def _entry_fields(entry: Any) -> dict[str, Any]:
    """Project the persisted usage fields from ``entry`` (None if not persisted)."""
    persisted = bool(getattr(entry, PERSISTED_KEY, False))
    return {
        "use_count": (getattr(entry, "use_count", 0) if persisted else None),
        "view_count": (getattr(entry, "view_count", 0) if persisted else None),
        "patch_count": (getattr(entry, "patch_count", 0) if persisted else None),
        "last_used_at": (getattr(entry, "last_used_at", None) if persisted else None),
        "last_viewed_at": (getattr(entry, "last_viewed_at", None) if persisted else None),
        "last_patched_at": (getattr(entry, "last_patched_at", None) if persisted else None),
        PERSISTED_KEY: persisted,
    }


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
        return _call_enabled_skills(profile, platform, fn)
    except Exception as exc:
        raise EnabledDetectionUnavailable(str(exc)) from exc


def _call_enabled_skills(profile: Path, platform: str | None, fn: Any) -> frozenset[str]:
    """Call ``fn`` and return its detected skills as a frozenset."""
    detected: frozenset[str] = fn(profile, platform=platform)
    return detected


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
