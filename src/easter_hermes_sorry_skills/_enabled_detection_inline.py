"""src/easter_hermes_sorry_skills/_enabled_detection_inline.py

Inline-form disabled-list parsing helpers.
"""

from __future__ import annotations

_DISABLED_KEY = "disabled"
_DISABLED_PREFIX = "disabled:"
_OPEN_BRACES = "{["
_CLOSE_BRACES = "}]"
_QUOTE_CHARS = ("'", '"')


def split_top_level_commas(text: str) -> list[str]:
    """Split ``text`` on top-level commas (commas outside of brackets)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        depth = _update_brace_depth(ch, depth)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _update_brace_depth(ch: str, depth: int) -> int:
    """Return the new brace depth after consuming ``ch``."""
    if ch in _OPEN_BRACES:
        return depth + 1
    if ch in _CLOSE_BRACES:
        return depth - 1
    return depth


def strip_quotes(text: str) -> str:
    """Strip whitespace and outer quote characters from ``text``."""
    cleaned = text.strip()
    for quote in _QUOTE_CHARS:
        cleaned = cleaned.strip(quote)
    return cleaned


def extract_disabled_from_inline(text: str, out: set[str]) -> None:
    """Populate ``out`` with names from a single ``disabled: [...]`` segment."""
    inner = text.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    for part in split_top_level_commas(inner):
        _extract_name(part, out)


def _extract_name(part: str, out: set[str]) -> None:
    """Add the disabled-name from ``part`` to ``out`` if well-formed."""
    kv = part.strip()
    if not kv.startswith(_DISABLED_PREFIX):
        return
    prefix_len = len(_DISABLED_PREFIX)
    payload = kv[prefix_len:].strip()
    if not (payload.startswith("[") and payload.endswith("]")):
        return
    for raw in split_top_level_commas(payload[1:-1].strip()):
        name = strip_quotes(raw)
        if name:
            out.add(name)
