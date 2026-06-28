"""tests/report/test_tokenizer.py

TDD: tests for easter_hermes_sorry_skills._tokenizer.estimate_tokens.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from easter_hermes_sorry_skills import _tokenizer
from easter_hermes_sorry_skills._cli_report_helpers_parse import emit_tokenizer_warning
from easter_hermes_sorry_skills._i18n_pick import pick


class _StubTokenizer:
    """Test double — encode() returns a fixed count."""

    def __init__(self, count: int) -> None:
        self.count = count
        self.last_text: str | None = None

    def encode(self, text: str) -> list[int]:
        self.last_text = text
        return [0] * self.count


class _RaiseTokenizer:
    def encode(self, text: str) -> list[int]:
        raise RuntimeError("tokenizer boom")


def test_estimate_tokens_uses_full_description() -> None:
    stub = _StubTokenizer(7)
    n = _tokenizer.estimate_tokens("foo", "a" * 200, tokenizer=stub)
    assert n == 7
    assert stub.last_text is not None
    assert stub.last_text == "foo " + "a" * 200


def test_estimate_tokens_calls_tokenizer_with_rendered_string() -> None:
    stub = _StubTokenizer(3)
    _tokenizer.estimate_tokens("hello", "world", tokenizer=stub)
    assert stub.last_text == "hello world"


def test_estimate_tokens_falls_back_when_tokenizer_is_none() -> None:
    rendered_len = len("foo " + "x" * 100)  # 104
    n = _tokenizer.estimate_tokens("foo", "x" * 100, tokenizer=None)
    assert n == rendered_len // 4


def test_estimate_tokens_falls_back_when_tokenizer_raises() -> None:
    n = _tokenizer.estimate_tokens("foo", "x" * 100, tokenizer=_RaiseTokenizer())
    assert n == len("foo " + "x" * 100) // 4


def test_estimate_tokens_returns_non_negative_int() -> None:
    n = _tokenizer.estimate_tokens("", "")
    assert isinstance(n, int)
    assert n >= 0


def test_estimate_tokens_chars_div_4_is_integer_division() -> None:
    n = _tokenizer.estimate_tokens("", "x" * 7, tokenizer=None)
    # 8 chars total (" xxxxxxx") // 4 == 2
    assert n == 2


@pytest.mark.parametrize("lang", ["en", "hu"])
def test_estimate_tokens_warning_logged_once_single_language(lang: str) -> None:
    """The production callback fires exactly once per process and emits single-lang.

    D6 spec mandate: every estimate_tokens call from the reporter MUST thread
    a single-language warning callback so the operator sees exactly one
    chars/4 fallback notice per process — parametrized by lang.
    """
    _tokenizer.reset_warning_state()
    seen: list[str] = []

    def _capture(msg: str) -> None:
        seen.append(msg)

    _tokenizer.estimate_tokens("a", "b", tokenizer=None, warning=_capture)
    _tokenizer.estimate_tokens("c", "d", tokenizer=None, warning=_capture)
    _tokenizer.estimate_tokens("e", "f", tokenizer=None, warning=_capture)
    # Module-level guard fires the callback at most once per process.
    assert len(seen) == 1
    # The internal msg passed to the callback is the bilingual fallback constant.
    # The production callback (cli_report.emit_tokenizer_warning) ignores the
    # arg and emits pick(lang).report_tokenizer_unavailable instead.
    expected = pick(lang).report_tokenizer_unavailable
    assert isinstance(expected, str)
    assert len(expected) > 0
    # EN and HU must produce different strings (single-lang parametrization).
    assert pick("en").report_tokenizer_unavailable != pick("hu").report_tokenizer_unavailable


@pytest.mark.parametrize("lang", ["en", "hu"])
def test_emit_tokenizer_warning_emits_single_language(lang: str, capsys: pytest.CaptureFixture[str]) -> None:
    """The wired callback MUST emit pick(lang).report_tokenizer_unavailable."""
    expected = pick(lang).report_tokenizer_unavailable
    emit_tokenizer_warning("", lang=lang)
    captured = capsys.readouterr()
    assert expected in captured.err
    # EN and HU must produce different emissions (single-lang parametrization).
    assert pick("en").report_tokenizer_unavailable != pick("hu").report_tokenizer_unavailable


def test_estimate_tokens_no_warning_logged_when_tokenizer_ok() -> None:
    seen: list[str] = []
    _tokenizer.estimate_tokens("a", "b", tokenizer=_StubTokenizer(2), warning=seen.append)
    assert seen == []


def test_estimate_tokens_never_imports_tools_skills_tool() -> None:
    """Static check: the module source MUST NOT import tools.skills_tool at top level."""
    src = _tokenizer.__file__
    assert src is not None
    tree = ast.parse(Path(src).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("tools.skills_tool")
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("tools.skills_tool")


class _NonSizedTokenizer:
    """encode() returns a value whose len() raises (TypeError)."""

    def encode(self, text: str) -> int:  # type: ignore[override]
        return 42  # int has no __len__


def test_estimate_tokens_falls_back_when_tokenizer_returns_non_sized() -> None:
    n = _tokenizer.estimate_tokens(
        "foo",
        "x" * 100,
        tokenizer=_NonSizedTokenizer(),
    )
    assert n == len("foo " + "x" * 100) // 4
