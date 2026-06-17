"""src/hermes_skill_creator_plugin/_tokenizer.py

Real model tokenizer with a deterministic `chars // 4` fallback.

TDD test cases for this module:
  test_estimate_tokens_uses_full_description
  test_estimate_tokens_calls_tokenizer_with_rendered_string
  test_estimate_tokens_falls_back_when_tokenizer_is_none
  test_estimate_tokens_falls_back_when_tokenizer_raises
  test_estimate_tokens_returns_non_negative_int
  test_estimate_tokens_chars_div_4_is_integer_division
  test_estimate_tokens_never_imports_tools_skills_tool
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

# Local cap constant — same as tools/skills_tool.py: MAX_DESCRIPTION_LENGTH.
# We keep a local copy to avoid an agent<->tools circular import (the same
# direction-check the cap-raise patch in 04 uses).
_REPORTER_MAX_DESCRIPTION_LENGTH = 1024

# Public, imported by the reporter.
MAX_DESCRIPTION_LENGTH = _REPORTER_MAX_DESCRIPTION_LENGTH


class Tokenizer(Protocol):
    """Protocol for a tokenizer. Implementations return an int >= 0."""

    def encode(self, text: str) -> list[int]: ...


def _chars_div_4(text: str) -> int:
    return max(0, len(text) // 4)


def _try_tokenize(tokenizer: Tokenizer | None, text: str) -> int | None:
    """Call the tokenizer if available; return None on any failure.

    Returns the number of tokens (>= 0) on success, or None when the
    tokenizer is None OR raises OR returns a value whose `len()` raises.
    """
    if tokenizer is None:
        return None
    try:
        result = tokenizer.encode(text)
    except Exception:
        return None
    # Real tokenizers (tiktoken, transformers) return a list of token ids.
    # We honor the count semantics: len() of the result.
    try:
        n = len(result)
    except TypeError:
        return None
    return n


def estimate_tokens(
    name: str,
    description: str,
    *,
    tokenizer: Tokenizer | None = None,
    warning: Callable[[str], None] | None = None,
    warned: bool = False,
) -> int:
    """Tokenize `f"{name} {description}"` with the configured model's tokenizer.

    The tokenizer is loaded from the active model in `~/.hermes/config.yaml`
    (or the `HERMES_MODEL` env var) via the standard transformers / tiktoken
    loader that Hermes already uses for its own prompt-budget reports. When
    the loader is unavailable (or raises on every call), the reporter falls
    back to `len(rendered) // 4` — the same approximation used elsewhere in
    Hermes for budget planning.

    Args:
        name: skill name.
        description: full skill description (NOT the truncated index form).
        tokenizer: optional tokenizer (any object with an `encode(str) -> Iterable[int]`
            method). When None or raising, the chars/4 fallback is used.
        warning: optional callback invoked ONCE when the fallback is used
            (a single-line bilingual warning).
        warned: state flag — set True after the warning has been emitted so
            the warning is logged once per run, not once per skill.

    Returns:
        Non-negative int. Token count of the rendered name+description string.
    """
    rendered = f"{name} {description}"
    n = _try_tokenize(tokenizer, rendered)
    if n is None:
        if warning is not None and not warned:
            warning(
                "[en] tokenizer unavailable, falling back to chars/4 "
                "/ [hu] a tokenizer nem elérhető, chars/4 becslés"
            )
        return _chars_div_4(rendered)
    return n


__all__ = ["estimate_tokens", "MAX_DESCRIPTION_LENGTH"]
