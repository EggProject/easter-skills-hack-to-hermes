"""Unit tests for ``_cli_profiles_skill`` (Phase B).

TDD list:
- test_count_skill_token_uses_estimate_tokens
- test_count_skill_token_fallback_when_tokenizer_unavailable
- test_enabled_skill_row_is_frozen_dataclass

The module wraps ``_tokenizer.estimate_tokens`` to return a ``(count, source)``
pair so the table renderer can stamp a ``(est.)`` badge when the fallback
path was used.
"""

from __future__ import annotations

import dataclasses
from unittest.mock import patch

import pytest

from easter_hermes_sorry_skills._cli_profiles_skill import (
    EnabledSkillRow,
    count_skill_token,
)
from easter_hermes_sorry_skills._tokenizer import chars_div_four


def test_count_skill_token_uses_estimate_tokens() -> None:
    """``count_skill_token("name", "desc")`` returns ``(N, "tokenizer")``.

    With no real tokenizer wired, ``_encode_via_protocol`` returns None
    which would normally trigger the chars/4 fallback — so we patch it
    to return a deterministic count to exercise the tokenizer-success path.
    """
    with patch(
        "easter_hermes_sorry_skills._tokenizer._encode_via_protocol",
        return_value=42,
    ):
        count, source = count_skill_token("alpha", "a skill")
    assert count == 42
    assert source == "tokenizer"


def test_count_skill_token_fallback_when_tokenizer_unavailable() -> None:
    """When ``_encode_via_protocol`` returns None, source is ``"chars_div_4"``.

    Patches the protocol helper to force the fallback branch and asserts
    the count matches ``chars_div_four("name desc")`` exactly.
    """
    from easter_hermes_sorry_skills import _tokenizer

    _tokenizer.reset_warning_state()
    with patch(
        "easter_hermes_sorry_skills._tokenizer._encode_via_protocol",
        return_value=None,
    ):
        count, source = count_skill_token("alpha", "beta")
    _tokenizer.reset_warning_state()

    assert source == "chars_div_4"
    assert count == chars_div_four("alpha beta")


def test_enabled_skill_row_is_frozen_dataclass() -> None:
    """``EnabledSkillRow`` is constructable + frozen (assignments raise)."""
    row = EnabledSkillRow(
        name="x",
        description="y",
        token_count=1,
        token_source="tokenizer",
    )
    assert row.name == "x"
    assert row.description == "y"
    assert row.token_count == 1
    assert row.token_source == "tokenizer"
    # Frozen dataclass — assigning to a field raises FrozenInstanceError.
    with pytest.raises(dataclasses.FrozenInstanceError):
        row.name = "mutated"  # type: ignore[misc]
