"""Detect already loaded skills from Hermes conversation history."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

_SKILL_INVOCATION_RE = re.compile(
    r'\[IMPORTANT: The user has invoked the "([^"]+)" skill,'
)
_SKILL_PRELOAD_RE = re.compile(
    r'\[IMPORTANT: The user launched this CLI session with the "([^"]+)" skill '
)


def loaded_skill_names_from_history(conversation_history: object) -> frozenset[str]:
    """Return skill names whose main instructions are already in history."""
    if not isinstance(conversation_history, list | tuple):
        return frozenset()

    loaded: set[str] = set()
    pending_skill_view_calls: dict[str, str] = {}
    for message in conversation_history:
        if not isinstance(message, dict):
            continue
        loaded.update(_skill_names_from_text(_message_content_text(message)))
        _record_skill_view_calls(message, pending_skill_view_calls)
        loaded.update(_skill_names_from_tool_result(message, pending_skill_view_calls))
    return frozenset(name for name in loaded if name)


def _record_skill_view_calls(message: dict[str, Any], pending_calls: dict[str, str]) -> None:
    """Record assistant skill_view calls by call id."""
    if message.get("role") != "assistant":
        return
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, Iterable) or isinstance(tool_calls, str | bytes):
        return
    for tool_call in tool_calls:
        call_id = _tool_call_id(tool_call)
        if not call_id or _tool_call_name(tool_call) != "skill_view":
            continue
        name = _skill_view_argument_name(tool_call)
        file_path = _skill_view_argument_file_path(tool_call)
        if name and not file_path:
            pending_calls[call_id] = name


def _skill_names_from_tool_result(
    message: dict[str, Any],
    pending_calls: dict[str, str],
) -> frozenset[str]:
    """Return a loaded skill name from a matching skill_view tool result."""
    if message.get("role") != "tool":
        return frozenset()
    call_id = str(message.get("tool_call_id") or "")
    fallback_name = pending_calls.get(call_id)
    if not fallback_name:
        return frozenset()

    payload = _json_object(_message_content_text(message))
    if payload.get("success") is not True or payload.get("file"):
        return frozenset()
    name = payload.get("name") or fallback_name
    return frozenset((str(name),)) if name else frozenset()


def _skill_names_from_text(content: str) -> frozenset[str]:
    """Return skill names embedded by Hermes slash-skill messages."""
    names = {
        match.group(1)
        for pattern in (_SKILL_INVOCATION_RE, _SKILL_PRELOAD_RE)
        for match in pattern.finditer(content)
    }
    return frozenset(names)


def _message_content_text(message: dict[str, Any]) -> str:
    """Return string content from a Hermes message."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""


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


def _skill_view_argument_name(tool_call: object) -> str:
    """Return skill_view(name=...) from a tool call."""
    args = _tool_call_arguments(tool_call)
    name = args.get("name")
    return str(name) if name else ""


def _skill_view_argument_file_path(tool_call: object) -> str:
    """Return skill_view(file_path=...) from a tool call."""
    args = _tool_call_arguments(tool_call)
    file_path = args.get("file_path")
    return str(file_path) if file_path else ""


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
    return _json_object(arguments)


def _json_object(raw_value: object) -> dict[str, object]:
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
