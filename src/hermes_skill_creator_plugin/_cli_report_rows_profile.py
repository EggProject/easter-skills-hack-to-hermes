"""Profile-row builders for the reporter rows module.

Split from ``_cli_report_rows`` (WPS202 module surface budget). Each
function takes the same keyword-only ``profile``/``skills_dir`` pair
plus the relevant per-row kwargs.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin._cli_report_helpers import (
    EMPTY_USAGE,
    emit_tokenizer_warning,
)
from hermes_skill_creator_plugin._cli_report_helpers_paths import (
    load_skill_description,
)
from hermes_skill_creator_plugin._reporter import SkillRow
from hermes_skill_creator_plugin._reporter_sort import _RowFields, make_row

if TYPE_CHECKING:
    pass


def _enabled_skills_safe(*, profile: Path, platform: str | None, fn: Any) -> frozenset[str]:
    """Call ``enabled_skills_fn`` and raise :class:`EnabledDetectionUnavailable`."""
    try:
        return _call_enabled_skills(profile, platform, fn)
    except Exception as exc:
        from hermes_skill_creator_plugin._cli_report_rows import (
            EnabledDetectionUnavailable,
        )

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
