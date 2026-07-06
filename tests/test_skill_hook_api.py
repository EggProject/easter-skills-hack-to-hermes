"""Tests for the Hermes skills_list adapter."""

from __future__ import annotations

import json
import sys
import types
from collections.abc import Callable
from typing import cast

import pytest

from easter_hermes_sorry_skills._skill_hook_api import (
    SkillMetadata,
    load_enabled_skills,
)
from easter_hermes_sorry_skills._skill_hook_api_normalize import iter_skill_metadata


def _json(payload: object) -> str:
    """Serialize a fake Hermes tool response."""
    return json.dumps(payload)


def test_load_enabled_skills_normalizes_success_payload() -> None:
    """Successful Hermes response becomes typed metadata."""
    result = load_enabled_skills(
        lambda: _json(
            {
                "success": True,
                "skills": [
                    {"name": " review ", "description": " code\nreview ", "category": " coding "},
                    {"name": "", "description": "ignored", "category": "x"},
                    {"name": 7, "description": "ignored", "category": "x"},
                    "bad",
                ],
            },
        ),
    )

    assert result == (SkillMetadata(name="review", description="code review", category="coding"),)


@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "skills": []},
        {"success": True, "skills": {}},
        [],
        {"skills": []},
    ],
)
def test_load_enabled_skills_rejects_unusable_payload(payload: object) -> None:
    """Only success payloads with list skills are accepted."""
    assert load_enabled_skills(lambda: _json(payload)) == ()


@pytest.mark.parametrize("callback", [lambda: "{not-json", lambda: "[]"])
def test_load_enabled_skills_bad_text_responses_fail_open(callback: Callable[[], str]) -> None:
    """Bad text API responses fail open to no skills."""
    assert load_enabled_skills(callback) == ()


def test_load_enabled_skills_non_string_response_fails_open() -> None:
    """Non-string API response fails open."""

    def _bad_response() -> str:
        return cast(str, 123)

    assert load_enabled_skills(_bad_response) == ()


def test_load_enabled_skills_exception_fails_open() -> None:
    """API exceptions fail open."""

    def _boom() -> str:
        raise OSError("boom")

    assert load_enabled_skills(_boom) == ()


def test_load_enabled_skills_imports_runtime_tools_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default path imports ``tools.skills_tool.skills_list``."""
    tools_module = types.ModuleType("tools")
    skills_tool_module = types.ModuleType("tools.skills_tool")
    skills_tool_module.skills_list = lambda: _json(
        {
            "success": True,
            "skills": [{"name": "demo", "description": "", "category": ""}],
        },
    )
    monkeypatch.setitem(sys.modules, "tools", tools_module)
    monkeypatch.setitem(sys.modules, "tools.skills_tool", skills_tool_module)

    assert load_enabled_skills() == (SkillMetadata(name="demo", description="", category=""),)


def test_iter_skill_metadata_ignores_non_list_payload() -> None:
    """The low-level normalizer fails open on bad payload types."""
    assert tuple(iter_skill_metadata({})) == ()
