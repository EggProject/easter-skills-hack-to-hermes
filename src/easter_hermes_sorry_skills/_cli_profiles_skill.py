"""Skill-row dataclass + token-count wrapper for the ``profiles`` CLI.

TDD test cases for this module (see tests/unit/test_cli_profiles_skill.py):
  test_count_skill_token_uses_estimate_tokens
  test_count_skill_token_fallback_when_tokenizer_unavailable
  test_enabled_skill_row_is_frozen_dataclass

The wrapper around ``_tokenizer.estimate_tokens`` returns a ``(count, source)``
pair so the table renderer can stamp a ``(est.)`` badge when the chars/4
fallback path was used. The decision is made by inspecting
``_encode_via_protocol`` directly so tests can patch that helper to
exercise both branches deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from easter_hermes_sorry_skills import _tokenizer

TokenSource = Literal["tokenizer", "chars_div_4"]


@dataclass(frozen=True)
class EnabledSkillRow:
    """A single enabled-skill row rendered into the per-profile table."""

    name: str
    description: str
    token_count: int
    token_source: TokenSource


def count_skill_token(name: str, description: str) -> tuple[int, TokenSource]:
    """Count tokens for one skill + return the source that produced the count.

    Mirrors ``_tokenizer.estimate_tokens`` semantics: tokenize the rendered
    ``"name description"`` string via the model tokenizer; on failure fall
    back to ``chars // 4``. The returned ``source`` lets downstream
    renderers stamp a ``(est.)`` badge when the fallback was used.

    The ``_encode_via_protocol`` helper is reached through the module
    object so ``unittest.mock.patch(..., "_tokenizer._encode_via_protocol")``
    can intercept the call from tests without breaking the import binding.
    """
    rendered = f"{name} {description}"
    encoded_count = _tokenizer._encode_via_protocol(None, rendered)
    if encoded_count is None:
        return _tokenizer.chars_div_four(rendered), "chars_div_4"
    return encoded_count, "tokenizer"
