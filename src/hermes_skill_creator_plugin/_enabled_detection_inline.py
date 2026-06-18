"""src/hermes_skill_creator_plugin/_enabled_detection_inline.py

Inline-form disabled-list parsing helpers.
"""
from __future__ import annotations


_DISABLED_KEY = "disabled"
_DISABLED_PREFIX = _DISABLED_KEY + ":"
_OPEN_BRACES = "{["
_CLOSE_BRACES = "}]"
_QUOTE_CHARS = ("'", '"')


def split_top_level_commas(text: str) -> list[str]:
    """Split ``text`` on top-level commas (commas outside of brackets)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch in _OPEN_BRACES:
            depth += 1
        elif ch in _CLOSE_BRACES:
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def strip_quotes(text: str) -> str:
    """Strip whitespace and outer quote characters from ``text``."""
    result = text.strip()
    for quote in _QUOTE_CHARS:
        result = result.strip(quote)
    return result


def extract_disabled_from_inline(text: str, out: set[str]) -> None:
    """Populate ``out`` with names from a single ``disabled: [...]`` segment."""
    inner = text.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    for part in split_top_level_commas(inner):
        kv = part.strip()
        if not kv.startswith(_DISABLED_PREFIX):
            continue
        value = kv[len(_DISABLED_PREFIX):].strip()
        if not (value.startswith("[") and value.endswith("]")):
            continue
        items = split_top_level_commas(value[1:-1].strip())
        for item in items:
            name = strip_quotes(item)
            if name:
                out.add(name)