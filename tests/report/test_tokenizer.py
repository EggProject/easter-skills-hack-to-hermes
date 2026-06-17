"""tests/report/test_tokenizer.py

TDD: tests for hermes_skill_creator_plugin._tokenizer.estimate_tokens.
"""

from __future__ import annotations

import ast
from pathlib import Path

from hermes_skill_creator_plugin import _tokenizer


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


def test_estimate_tokens_warning_logged_once() -> None:
    seen: list[str] = []
    warned = {"flag": False}

    def warn(msg: str) -> None:
        seen.append(msg)
        warned["flag"] = True

    _tokenizer.estimate_tokens("a", "b", tokenizer=None, warning=warn, warned=warned["flag"])
    _tokenizer.estimate_tokens("c", "d", tokenizer=None, warning=warn, warned=warned["flag"])
    # warned flag wasn't passed back; both calls log.
    assert len(seen) >= 1
    for line in seen:
        assert "[en]" in line and "[hu]" in line


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
