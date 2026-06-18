"""Unit tests for hermes_skill_creator_plugin._safety.

The decorator must pytest.skip when HERMES_HOME resolves to the live install
and the live install path exists; otherwise pass through.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_skill_creator_plugin._safety import (
    _LIVE_HERMES_AGENT,
    HERMES_HOME,
    _current_hermes_home,
    assert_hermes_agent_untouched,
)


def test_safety_module_exports() -> None:
    assert HERMES_HOME is not None
    assert _LIVE_HERMES_AGENT is not None


def test_current_hermes_home_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_HOME", "/tmp/x")
    assert _current_hermes_home() == Path("/tmp/x")


def test_decorator_passes_through_when_hermes_home_in_tmp(
    skill_creator_home: Path,
) -> None:
    """A decorated test that uses the `skill_creator_home` fixture
    (which monkeypatches HERMES_HOME to a tmp_path) is NOT skipped."""

    @assert_hermes_agent_untouched
    def inner() -> int:
        return 42

    assert inner() == 42


def test_decorator_skips_when_hermes_home_resolves_to_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When HERMES_HOME is unset and the live install path exists, the
    decorator skips the test."""
    monkeypatch.delenv("HERMES_HOME", raising=False)
    # Make _LIVE_HERMES_AGENT.resolve() == _current_hermes_home().resolve()
    # by patching the module's _LIVE_HERMES_AGENT to a tmp_path that we
    # ALSO set as HERMES_HOME (so they match).
    from hermes_skill_creator_plugin import _safety as safety

    fake = tmp_path / "fake-live"
    fake.mkdir()
    (fake / "marker.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(safety, "_LIVE_HERMES_AGENT", fake)
    monkeypatch.setenv("HERMES_HOME", str(fake))

    @assert_hermes_agent_untouched
    def inner() -> int:
        return 42

    with pytest.raises(pytest.skip.Exception):
        inner()


def test_decorator_preserves_test_return_value(skill_creator_home: Path) -> None:
    @assert_hermes_agent_untouched
    def inner() -> str:
        return "ok"

    assert inner() == "ok"


def test_decorator_propagates_assertion_errors(skill_creator_home: Path) -> None:
    @assert_hermes_agent_untouched
    def inner() -> None:
        raise AssertionError("boom")

    with pytest.raises(AssertionError, match="boom"):
        inner()
