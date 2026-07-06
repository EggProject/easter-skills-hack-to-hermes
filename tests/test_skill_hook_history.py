"""Tests for loaded-skill detection from Hermes conversation history."""

from __future__ import annotations

import json

from easter_hermes_sorry_skills._skill_hook_history import (
    loaded_skill_names_from_history,
)
from easter_hermes_sorry_skills._skill_hook_history_tool import (
    _tool_call_arguments,
    _tool_call_name,
    json_object,
)


def _assistant_skill_view_call(
    call_id: str,
    name: str,
    *,
    file_path: str | None = None,
    arguments_as_dict: bool = False,
) -> dict[str, object]:
    """Build a Hermes assistant tool call message."""
    arguments: dict[str, object] = {"name": name}
    if file_path:
        arguments["file_path"] = file_path
    return {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call_id,
                "function": {
                    "name": "skill_view",
                    "arguments": arguments if arguments_as_dict else json.dumps(arguments),
                },
            },
        ],
    }


def _tool_result(call_id: str, payload: dict[str, object]) -> dict[str, object]:
    """Build a Hermes tool result message."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(payload),
    }


def test_loaded_skill_names_from_history_detects_successful_skill_view() -> None:
    """A successful main skill_view result marks the skill as loaded."""
    history = [
        _assistant_skill_view_call("call-1", "reviewer"),
        _tool_result("call-1", {"success": True, "name": "reviewer", "content": "body"}),
    ]

    assert loaded_skill_names_from_history(history) == frozenset(("reviewer",))


def test_loaded_skill_names_from_history_uses_requested_name_as_fallback() -> None:
    """Old skill_view payloads without name still count via call arguments."""
    history = [
        _assistant_skill_view_call("call-1", "reviewer", arguments_as_dict=True),
        _tool_result("call-1", {"success": True, "content": "body"}),
    ]

    assert loaded_skill_names_from_history(history) == frozenset(("reviewer",))


def test_loaded_skill_names_from_history_detects_slash_skill_messages() -> None:
    """Slash skill and preloaded skill messages also mean instructions are loaded."""
    history = [
        {
            "role": "user",
            "content": (
                '[IMPORTANT: The user has invoked the "reviewer" skill, '
                "indicating they want you to follow its instructions. "
                "The full skill content is loaded below.]"
            ),
        },
        {
            "role": "user",
            "content": (
                '[IMPORTANT: The user launched this CLI session with the "planner" skill '
                "preloaded. Treat its instructions as active guidance.]"
            ),
        },
    ]

    assert loaded_skill_names_from_history(history) == frozenset(("planner", "reviewer"))


def test_loaded_skill_names_from_history_ignores_linked_file_reads() -> None:
    """Reading a linked file is not the same as loading main skill instructions."""
    history = [
        _assistant_skill_view_call("call-1", "reviewer", file_path="references/details.md"),
        _tool_result("call-1", {"success": True, "name": "reviewer", "file": "references/details.md"}),
    ]

    assert loaded_skill_names_from_history(history) == frozenset()


def test_loaded_skill_names_from_history_ignores_file_payload_without_argument_file_path() -> None:
    """A result payload for a linked file is ignored even if args were truncated."""
    history = [
        _assistant_skill_view_call("call-1", "reviewer"),
        _tool_result("call-1", {"success": True, "name": "reviewer", "file": "references/details.md"}),
    ]

    assert loaded_skill_names_from_history(history) == frozenset()


def test_loaded_skill_names_from_history_ignores_malformed_or_unmatched_entries() -> None:
    """Malformed history must fail open and avoid false positives."""
    history = [
        "not a message",
        {"role": "assistant", "tool_calls": "not-a-list"},
        {
            "role": "assistant",
            "tool_calls": [
                "not a tool call",
                {"id": "call-1", "function": {"name": "terminal", "arguments": "{}"}},
                {"id": "call-2", "function": {"name": "skill_view", "arguments": "{"}},
                {"function": {"name": "skill_view", "arguments": '{"name": "missing-id"}'}},
                {"id": "call-3", "function": "bad-shape"},
                {"id": "call-4", "function": {"name": "skill_view", "arguments": '["bad"]'}},
            ],
        },
        _tool_result("call-1", {"success": True, "name": "terminal-name"}),
        _tool_result("call-2", {"success": True, "name": "bad-json-args"}),
        _tool_result("call-4", {"success": False, "name": "failed"}),
        {"role": "tool", "tool_call_id": "missing", "content": '{"success": true, "name": "orphan"}'},
        {"role": "tool", "tool_call_id": "call-4", "content": "{"},
        {"role": "user", "content": ["not", "a", "string"]},
    ]

    assert loaded_skill_names_from_history(history) == frozenset()


def test_loaded_skill_names_from_history_ignores_non_history_payload() -> None:
    """Only list-like Hermes history payloads are scanned."""
    assert loaded_skill_names_from_history(None) == frozenset()
    assert loaded_skill_names_from_history({"role": "user"}) == frozenset()


def test_private_json_and_tool_call_shape_guards() -> None:
    """Shape guards return empty values for non-Hermes objects."""
    assert _tool_call_name("not a dict") == ""
    assert _tool_call_arguments("not a dict") == {}
    assert _tool_call_arguments({"function": "not a dict"}) == {}
    assert json_object({"success": True}) == {"success": True}
    assert json_object(123) == {}
