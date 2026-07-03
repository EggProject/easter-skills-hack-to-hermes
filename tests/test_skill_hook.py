"""Tests for WOW skill hook orchestration."""

from __future__ import annotations

import logging

import pytest

from easter_hermes_sorry_skills import _skill_hook
from easter_hermes_sorry_skills._skill_hook_api import SkillMetadata
from easter_hermes_sorry_skills._skill_hook_config import SkillHookConfig


def _patch_hook_deps(
    monkeypatch: pytest.MonkeyPatch,
    config: SkillHookConfig,
    skills: tuple[SkillMetadata, ...],
) -> None:
    """Patch config and API dependencies for hook tests."""
    monkeypatch.setattr(_skill_hook, "load_skill_hook_config", lambda: config)
    monkeypatch.setattr(_skill_hook, "load_enabled_skills", lambda: skills)


def test_pre_llm_call_returns_context_for_adaptive_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adaptive mode returns Hermes context when matcher finds a skill."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(),
        (SkillMetadata(name="reviewer", description="Review code changes", category="coding"),),
    )

    result = _skill_hook.pre_llm_call(user_message="Please review code changes", is_first_turn=False)

    assert result is not None
    assert result["context"].startswith("Relevant Hermes skills")
    assert "reviewer" in result["context"]


def test_pre_llm_call_marks_already_loaded_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Already loaded matches are weak reminders, not normal recommendations."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(),
        (SkillMetadata(name="reviewer", description="Review code changes", category="coding"),),
    )
    history = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {"name": "skill_view", "arguments": '{"name": "reviewer"}'},
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": '{"success": true, "name": "reviewer", "content": "body"}',
        },
    ]

    result = _skill_hook.pre_llm_call(
        user_message="Please review code changes",
        conversation_history=history,
        is_first_turn=False,
    )

    assert result is not None
    assert "Already loaded relevant Hermes skills" in result["context"]
    assert "Relevant Hermes skills to consider" not in result["context"]
    assert "Follow already loaded skill instructions" in result["context"]


def test_pre_llm_call_splits_loaded_and_new_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """A loaded match does not suppress unrelated new relevant matches."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(top_k=3),
        (
            SkillMetadata(name="docs", description="Write release documentation", category="docs"),
            SkillMetadata(name="reviewer", description="Review code changes", category="coding"),
        ),
    )
    history = [
        {
            "role": "user",
            "content": (
                '[IMPORTANT: The user has invoked the "reviewer" skill, '
                "indicating they want you to follow its instructions. "
                "The full skill content is loaded below.]"
            ),
        },
    ]

    result = _skill_hook.pre_llm_call(
        user_message="Please review code changes and write release documentation",
        conversation_history=history,
        is_first_turn=False,
    )

    assert result is not None
    assert "Relevant Hermes skills to consider" in result["context"]
    assert "- docs:" in result["context"]
    assert "Already loaded relevant Hermes skills" in result["context"]
    assert "- reviewer" in result["context"]


def test_pre_llm_call_off_mode_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off mode never injects context."""
    _patch_hook_deps(monkeypatch, SkillHookConfig(mode="off"), ())

    assert _skill_hook.pre_llm_call(user_message="review code", is_first_turn=True) is None


def test_pre_llm_call_first_mode_only_runs_first_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """First mode is gated by is_first_turn."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(mode="first"),
        (SkillMetadata(name="reviewer", description="Review code changes", category="coding"),),
    )

    later = _skill_hook.pre_llm_call(user_message="Please review code changes", is_first_turn=False)
    first = _skill_hook.pre_llm_call(user_message="Please review code changes", is_first_turn=True)

    assert later is None
    assert first is not None


def test_pre_llm_call_empty_or_unmatched_prompt_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty and unmatched prompts do not inject."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(),
        (SkillMetadata(name="docs", description="Write documentation", category="docs"),),
    )

    assert _skill_hook.pre_llm_call(user_message="", is_first_turn=True) is None
    assert _skill_hook.pre_llm_call(user_message="hello there friend", is_first_turn=False) is None


def test_pre_llm_call_fail_open(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Unexpected errors are logged and swallowed."""
    monkeypatch.setattr(
        _skill_hook,
        "load_skill_hook_config",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with caplog.at_level(logging.WARNING):
        result = _skill_hook.pre_llm_call(user_message="review code", is_first_turn=True)

    assert result is None
    assert "review code" not in caplog.text
    assert "WOW skill hook skipped" in caplog.text


def test_build_pre_llm_context_debug_logs_without_prompt(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug logging includes bounded metadata, not the user prompt."""
    _patch_hook_deps(
        monkeypatch,
        SkillHookConfig(log_level="DEBUG"),
        (SkillMetadata(name="reviewer", description="Review code changes", category="coding"),),
    )

    with caplog.at_level(logging.DEBUG):
        context = _skill_hook.build_pre_llm_context(
            {"user_message": "Please review code changes SECRET", "is_first_turn": False},
        )

    assert context is not None
    assert "skill_hook: mode=adaptive output=shortlist skills=1 matched=1 loaded=0 injected=1" in caplog.text
    assert "matched reviewer" in caplog.text
    assert "SECRET" not in caplog.text
