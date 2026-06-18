"""src/hermes_skill_creator_plugin/_cli_report_rows.py

Row construction for the reporter: usage rows, profile rows, json-path safety.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._cli_report_helpers import (
    EMPTY_USAGE,
    emit_tokenizer_warning,
    load_skill_description,
)
from ._reporter import SkillRow, make_row


class EnabledDetectionUnavailable(Exception):
    """Raised when get_enabled_skills is unavailable."""


def build_usage_rows(
    curator: Any | None,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    """Build a name -> usage-fields map. None values when not persisted."""
    out: dict[str, dict[str, Any]] = {}
    if curator is None:
        for n in enabled_names:
            out[n] = {**EMPTY_USAGE, "_persisted": False}
        return out
    try:
        report = curator.usage_report(skills_dir=skills_dir)
    except Exception:
        report = []
    for entry in report or []:
        name = getattr(entry, "name", None)
        if name is None or name not in enabled_names:
            continue
        persisted = bool(getattr(entry, "_persisted", False))
        out[name] = {
            "use_count": (
                getattr(entry, "use_count", 0) if persisted else None
            ),
            "view_count": (
                getattr(entry, "view_count", 0) if persisted else None
            ),
            "patch_count": (
                getattr(entry, "patch_count", 0) if persisted else None
            ),
            "last_used_at": (
                getattr(entry, "last_used_at", None) if persisted else None
            ),
            "last_viewed_at": (
                getattr(entry, "last_viewed_at", None) if persisted else None
            ),
            "last_patched_at": (
                getattr(entry, "last_patched_at", None)
                if persisted
                else None
            ),
            "_persisted": persisted,
        }
    for n in enabled_names:
        if n not in out:
            out[n] = {**EMPTY_USAGE, "_persisted": False}
    return out


def build_rows_for_profile(
    profile: Path,
    *,
    platform: str | None,
    curator: Any | None,
    estimate_tokens_fn: Any,
    enabled_skills_fn: Any,
) -> tuple[list[SkillRow], int]:
    """Build the SkillRow list and total_tokens for `profile`."""
    try:
        enabled = enabled_skills_fn(profile, platform=platform)
    except Exception as exc:
        raise EnabledDetectionUnavailable(str(exc)) from exc
    skills_dir = profile / "skills"
    usage = build_usage_rows(curator, skills_dir, enabled)
    rows: list[SkillRow] = []
    total = 0
    for name in sorted(enabled):
        description = load_skill_description(skills_dir, name)
        tokens = estimate_tokens_fn(
            name, description, warning=emit_tokenizer_warning
        )
        total += tokens
        u = usage.get(name, EMPTY_USAGE)
        rows.append(
            make_row(
                profile=profile.name,
                name=name,
                description=description,
                tokens=tokens,
                use_count=u["use_count"],
                view_count=u["view_count"],
                patch_count=u["patch_count"],
                last_used_at=u["last_used_at"],
                last_viewed_at=u["last_viewed_at"],
                last_patched_at=u["last_patched_at"],
            )
        )
    return rows, total


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