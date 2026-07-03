"""Tool-call parsing helpers for loaded-skill detection."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TypeGuard


def skill_view_main_calls(tool_calls: object) -> tuple[tuple[str, str], ...]:
    """Return call id and skill name for main skill_view calls."""
    if not _is_tool_call_sequence(tool_calls):
        return ()
    calls: list[tuple[str, str]] = []
    for tool_call in tool_calls:
        call = _main_skill_view_call(tool_call)
        if call:
            calls.append(call)
    return tuple(calls)


def json_object(raw_value: object) -> dict[str, object]:
    """Parse a JSON object, returning an empty dict on malformed input."""
    if isinstance(raw_value, dict):
        return raw_value
    if not isinstance(raw_value, str):
        return {}
    try:
        parsed = json.loads(raw_value)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_tool_call_sequence(tool_calls: object) -> TypeGuard[Iterable[object]]:
    """Return whether an object can be iterated as tool calls."""
    if isinstance(tool_calls, str | bytes):
        return False
    return isinstance(tool_calls, Iterable)


def _main_skill_view_call(tool_call: object) -> tuple[str, str] | None:
    """Return call id and skill name for a main skill_view call."""
    call_id = _tool_call_id(tool_call)
    if not call_id or _tool_call_name(tool_call) != "skill_view":
        return None
    arguments = _tool_call_arguments(tool_call)
    skill_name = arguments.get("name")
    if not skill_name or arguments.get("file_path"):
        return None
    return call_id, str(skill_name)


def _tool_call_id(tool_call: object) -> str:
    """Return a tool call id from dict-like Hermes tool calls."""
    if not isinstance(tool_call, dict):
        return ""
    return str(tool_call.get("id") or tool_call.get("call_id") or "")


def _tool_call_name(tool_call: object) -> str:
    """Return the called function name."""
    if not isinstance(tool_call, dict):
        return ""
    function = tool_call.get("function")
    if not isinstance(function, dict):
        return ""
    return str(function.get("name") or "")


def _tool_call_arguments(tool_call: object) -> dict[str, object]:
    """Parse a tool call's JSON arguments object."""
    if not isinstance(tool_call, dict):
        return {}
    function = tool_call.get("function")
    if not isinstance(function, dict):
        return {}
    arguments = function.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    return json_object(arguments)
