"""Detect already loaded skills from Hermes conversation history."""

from __future__ import annotations

import re
from typing import Any

from easter_hermes_sorry_skills._skill_hook_history_tool import json_object, skill_view_main_calls

_SKILL_INVOCATION_RE = re.compile(r'\[IMPORTANT: The user has invoked the "([^"]+)" skill,')
_SKILL_PRELOAD_RE = re.compile(r'\[IMPORTANT: The user launched this CLI session with the "([^"]+)" skill ')


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
    for call_id, name in skill_view_main_calls(message.get("tool_calls")):
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

    payload = json_object(_message_content_text(message))
    if payload.get("success") is not True or payload.get("file"):
        return frozenset()
    name = payload.get("name") or fallback_name
    return frozenset((str(name),)) if name else frozenset()


def _skill_names_from_text(text: str) -> frozenset[str]:
    """Return skill names embedded by Hermes slash-skill messages."""
    names = {
        match.group(1) for pattern in (_SKILL_INVOCATION_RE, _SKILL_PRELOAD_RE) for match in pattern.finditer(text)
    }
    return frozenset(names)


def _message_content_text(message: dict[str, Any]) -> str:
    """Return string content from a Hermes message."""
    raw_content = message.get("content")
    if isinstance(raw_content, str):
        return raw_content
    return ""
