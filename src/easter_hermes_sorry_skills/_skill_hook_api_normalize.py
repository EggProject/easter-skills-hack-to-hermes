"""Normalize Hermes skills API records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from easter_hermes_sorry_skills._skill_hook_models import SkillMetadata


def iter_skill_metadata(raw_skills: object) -> Iterable[SkillMetadata]:
    """Yield normalized metadata records from a Hermes response."""
    if not isinstance(raw_skills, list):
        return
    for raw_skill in raw_skills:
        normalized = _normalize_skill(raw_skill)
        if normalized is not None:
            yield normalized


def _normalize_skill(raw_skill: object) -> SkillMetadata | None:
    """Normalize one raw skill record."""
    if not isinstance(raw_skill, dict):
        return None
    name = _clean_text(raw_skill.get("name"))
    if not name:
        return None
    return SkillMetadata(
        name=name,
        description=_clean_text(raw_skill.get("description")),
        category=_clean_text(raw_skill.get("category")),
    )


def _clean_text(raw_value: Any) -> str:
    """Return a stripped string or an empty fallback."""
    if not isinstance(raw_value, str):
        return ""
    return " ".join(raw_value.split())
