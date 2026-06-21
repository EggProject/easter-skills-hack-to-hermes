"""Usage-map construction helpers for the reporter CLI.

Extracted from ``_cli_report_rows.py`` to keep that module under wemake
WPS202 (≤7 module members). The usage-map building walks the
``usage_report`` output of the curator and projects each entry into a
flat dict keyed by skill name; the parent module owns the orchestration
and the row-building path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._cli_report_helpers_consts import (
    EMPTY_USAGE,
    PERSISTED_KEY,
)


def empty_usage_map(enabled_names: frozenset[str]) -> dict[str, dict[str, Any]]:
    return {name: {**EMPTY_USAGE, PERSISTED_KEY: False} for name in enabled_names}


def filled_usage_map(
    curator: Any,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    out = filled_usage_map_for_report(curator, skills_dir, enabled_names)
    out = backfill_missing_usage(out, enabled_names)
    return out


def filled_usage_map_for_report(
    curator: Any,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    report = usage_report_safe(curator, skills_dir)
    for entry in report:
        entry_name_value = entry_name(entry)
        if entry_name_value is None or entry_name_value not in enabled_names:
            continue
        out[entry_name_value] = entry_fields(entry)
    return out


def backfill_missing_usage(
    out: dict[str, dict[str, Any]],
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    for enabled_name in enabled_names:
        if enabled_name not in out:
            out[enabled_name] = {**EMPTY_USAGE, PERSISTED_KEY: False}
    return out


def usage_report_safe(curator: Any, skills_dir: Path) -> list[Any]:
    """Call ``curator.usage_report`` and return [] on any error."""
    try:
        report = curator.usage_report(skills_dir=skills_dir)
    except Exception:
        return []
    return report or []


def entry_name(entry: Any) -> str | None:
    """Return ``entry.name`` if it is a string, else ``None``."""
    raw_name = getattr(entry, "name", None)
    if isinstance(raw_name, str) and raw_name:
        return raw_name
    return None


def entry_fields(entry: Any) -> dict[str, Any]:
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


def call_enabled_skills_fn(profile: Path, platform: str | None, fn: Any) -> frozenset[str]:
    """Single-line call to ``fn`` so callers can keep their try-body to 1 statement."""
    detected: frozenset[str] = fn(profile, platform=platform)
    return detected
