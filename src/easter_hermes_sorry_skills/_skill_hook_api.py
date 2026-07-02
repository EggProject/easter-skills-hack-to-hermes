"""Hermes skills API adapter for the WOW skill reminder hook."""

from __future__ import annotations

import json
from collections.abc import Callable

from easter_hermes_sorry_skills._skill_hook_api_normalize import iter_skill_metadata
from easter_hermes_sorry_skills._skill_hook_models import SkillMetadata

SkillsListFn = Callable[[], str]


def load_enabled_skills(skills_list_fn: SkillsListFn | None = None) -> tuple[SkillMetadata, ...]:
    """Load enabled skill metadata via Hermes ``skills_list()``.

    The adapter deliberately delegates discovery to Hermes. It never scans
    profiles, skill directories, or config files by itself.
    """
    raw_response = _safe_call_skills_list(skills_list_fn)
    if raw_response is None:
        return ()
    raw_skills = _skill_list(payload=_parse_json_response(raw_response))
    if raw_skills is None:
        return ()
    return tuple(iter_skill_metadata(raw_skills))


def _safe_call_skills_list(skills_list_fn: SkillsListFn | None) -> str | None:
    """Call Hermes skills_list and fail open."""
    try:
        return _call_skills_list(skills_list_fn)
    except (ImportError, OSError, TypeError):
        return None


def _call_skills_list(skills_list_fn: SkillsListFn | None) -> str:
    """Call injected or runtime Hermes ``skills_list``."""
    if skills_list_fn is not None:
        return skills_list_fn()
    from tools.skills_tool import skills_list

    return skills_list()


def _parse_json_response(raw_response: str) -> object:
    """Parse a Hermes JSON response and fail open."""
    try:
        return json.loads(raw_response)
    except (TypeError, ValueError):
        return None


def _skill_list(payload: object) -> list[object] | None:
    """Return raw skills list from a usable response."""
    if not isinstance(payload, dict):
        return None
    raw_skills = payload.get("skills")
    if payload.get("success") is not True or not isinstance(raw_skills, list):
        return None
    return raw_skills
