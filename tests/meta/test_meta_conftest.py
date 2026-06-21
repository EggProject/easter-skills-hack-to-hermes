"""tests/meta/test_meta_conftest.py — meta-tests for tests/conftest.py.

Implements the TDD test list declared at the top of tests/conftest.py:

  test_assert_hermes_agent_untouched_skips_when_path_live
  test_assert_hermes_agent_untouched_runs_when_path_inside_tmp
  test_hermes_home_fixture_resolves_under_tmp
  test_hermes_checkout_fixture_provides_a_6_file_synthetic_repo
  test_seed_minimal_creates_known_layout
  test_hermes_subprocess_env_never_pops_hermes_session
  test_decorator_preserves_test_return_value
  test_decorator_propagates_assertion_errors
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

from tests import conftest
from tests.conftest import (
    MINIMAL_HERMES_FILES,
    hermes_subprocess_env,
    seed_minimal,
)


def test_assert_hermes_agent_untouched_skips_when_path_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Decorator MUST pytest.skip when HERMES_HOME resolves to a live install path.

    The ``skipif`` guards the test against running on hosts with NO live
    install: without the live path the decorator does NOT skip (it
    passes through), so a strict ``pytest.raises(skip.Exception)`` would
    fail. Skipping the test entirely is the correct, host-independent
    behavior: on hosts WITH a live install we exercise the skip branch;
    on hosts WITHOUT one we mark the test as N/A rather than fail.
    """
    live_path = Path("~/.hermes/hermes-agent").expanduser()
    if not live_path.exists():
        pytest.skip("no live Hermes install on this host — skip-branch untestable")

    # Force HERMES_HOME back to its default (no monkeypatched override).
    monkeypatch.delenv("HERMES_HOME", raising=False)
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def would_touch_live() -> str:
        return "TOUCHED"

    # The decorator MUST skip when the live path is present.
    with pytest.raises(pytest.skip.Exception):
        would_touch_live()


def test_assert_hermes_agent_untouched_runs_when_path_inside_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Decorator MUST let a test run when HERMES_HOME is monkey-patched to tmp_path."""
    fake = tmp_path / "fake-hermes-agent"
    fake.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def safe_test() -> str:
        return "RAN"

    assert safe_test() == "RAN"


def test_hermes_home_fixture_resolves_under_tmp(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hermes_home fixture MUST place HERMES_HOME under tmp_path."""
    # Resolve the fixture via FixtureRequest so pytest does not warn about direct calls.
    fixture = request.getfixturevalue("hermes_home")
    assert fixture.exists()
    assert fixture.is_relative_to(tmp_path)
    assert os.environ["HERMES_HOME"] == str(fixture)


def test_hermes_checkout_fixture_provides_a_6_file_synthetic_repo(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hermes_checkout fixture MUST seed exactly MINIMAL_HERMES_FILES (6 files)."""
    fake = request.getfixturevalue("hermes_home")
    # seed_minimal is what the fixture calls.
    checkout = seed_minimal(fake)
    assert checkout == fake
    # Every relative path in MINIMAL_HERMES_FILES MUST exist on disk.
    for rel in MINIMAL_HERMES_FILES:
        assert (fake / rel).exists(), f"seed_minimal missing {rel}"


def test_seed_minimal_creates_known_layout(tmp_path: Path) -> None:
    """seed_minimal MUST produce the documented 6-file synthetic Hermes checkout."""
    seed_minimal(tmp_path)
    expected = {
        "pyproject.toml",
        "README.md",
        "src/hermes_agent/__init__.py",
        "src/hermes_agent/cli.py",
        "src/hermes_agent/skills.py",
        "skills/.gitkeep",
    }
    actual = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file() and ".venv" not in p.parts}
    assert actual == expected


def test_hermes_subprocess_env_never_pops_hermes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hermes_subprocess_env MUST return a copy without HERMES_SESSION; parent env untouched."""
    monkeypatch.setenv("HERMES_SESSION", "sentinel-value")
    parent_before = os.environ.get("HERMES_SESSION")
    child_env = hermes_subprocess_env()
    parent_after = os.environ.get("HERMES_SESSION")
    assert parent_before == "sentinel-value"
    assert parent_after == "sentinel-value"  # parent untouched
    assert "HERMES_SESSION" not in child_env  # child copy stripped


def test_decorator_preserves_test_return_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Decorator MUST forward the wrapped function's return value verbatim."""
    fake = tmp_path / "fake-hermes-agent"
    fake.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def returns_a_dict() -> dict[str, int]:
        return {"key": 42}

    assert returns_a_dict() == {"key": 42}


def test_decorator_propagates_assertion_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Decorator MUST NOT swallow AssertionError raised inside the wrapped test."""
    fake = tmp_path / "fake-hermes-agent"
    fake.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def raises_assertion() -> None:
        raise AssertionError("intentional")

    with pytest.raises(AssertionError, match="intentional"):
        raises_assertion()


def test_hermes_checkout_fixture_calls_seed_minimal(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hermes_checkout fixture MUST call seed_minimal and return the seeded root."""
    fake = request.getfixturevalue("hermes_home")
    checkout = request.getfixturevalue("hermes_checkout")
    assert checkout == fake
    # All 6 files from MINIMAL_HERMES_FILES MUST be present.
    for rel in MINIMAL_HERMES_FILES:
        assert (fake / rel).exists()


def test_ensure_agent_stub_handles_existing_agent_module() -> None:
    """_ensure_agent_stub MUST be a no-op when ``agent`` is already in sys.modules.

    Exercises the ``agent_mod is None`` FALSE branch (line 120) AND the
    pre-existing ``agent.skill_utils`` early-return at line 117/118.
    """
    import types

    import tests.conftest as conftest_mod

    saved_agent = sys.modules.get("agent")
    saved_skill_utils = sys.modules.get("agent.skill_utils")
    try:
        # Install a sentinel ``agent`` package without skill_utils so the
        # stub function actually executes the body (not the early return).
        sentinel_agent = types.ModuleType("agent")
        sentinel_agent.__path__ = []  # mark as package
        sys.modules["agent"] = sentinel_agent
        sys.modules.pop("agent.skill_utils", None)

        conftest_mod._ensure_agent_stub()

        # After the stub ran, skill_utils MUST be registered and reachable.
        assert "agent.skill_utils" in sys.modules
        skill_utils_mod = sys.modules["agent.skill_utils"]
        # Calling the registered stub MUST return [] (covers line 127).
        assert skill_utils_mod.get_disabled_skill_names() == []
        # And the stub MUST be wired under sentinel_agent.
        assert sentinel_agent.skill_utils is skill_utils_mod
    finally:
        # Restore sys.modules to avoid polluting other tests.
        if saved_agent is None:
            sys.modules.pop("agent", None)
        else:
            sys.modules["agent"] = saved_agent
        if saved_skill_utils is None:
            sys.modules.pop("agent.skill_utils", None)
        else:
            sys.modules["agent.skill_utils"] = saved_skill_utils
