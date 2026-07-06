"""Text normalization helpers for the WOW skill reminder matcher."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
_MIN_TOKEN_LENGTH = 3
_STOPWORDS = frozenset(
    (
        "about",
        "and",
        "are",
        "az",
        "egy",
        "for",
        "hogy",
        "into",
        "kell",
        "meg",
        "the",
        "this",
        "use",
        "van",
        "with",
    ),
)


def content_tokens(text: str) -> frozenset[str]:
    """Tokenize text and drop low-signal tokens."""
    return frozenset(token for token in raw_tokens(text) if _is_content_token(token))


def raw_tokens(text: str) -> tuple[str, ...]:
    """Return normalized lexical tokens."""
    tokens: list[str] = []
    for found in _TOKEN_RE.finditer(text):
        tokens.append(found.group(0).lower())
    return tuple(tokens)


def normalized_text(text: str) -> str:
    """Return whitespace-normalized lowercase text."""
    return " ".join(raw_tokens(text))


def _is_content_token(token: str) -> bool:
    """Return whether a token carries enough signal for matching."""
    return len(token) >= _MIN_TOKEN_LENGTH and token not in _STOPWORDS
