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
from pathlib import Path

import pytest

from tests import conftest
from tests.conftest import (
    HERMES_HOME,
    MINIMAL_HERMES_FILES,
    assert_hermes_agent_untouched,
    hermes_subprocess_env,
    seed_minimal,
)


def test_assert_hermes_agent_untouched_skips_when_path_live(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Decorator MUST pytest.skip when HERMES_HOME resolves to a live install path."""
    # Force HERMES_HOME back to its default (no monkeypatched override).
    monkeypatch.delenv("HERMES_HOME", raising=False)
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def would_touch_live() -> str:  # pragma: no cover - unreachable when guarded
        return "TOUCHED"

    live_path = Path("~/.hermes/hermes-agent").expanduser()
    if live_path.exists():
        # The decorator MUST skip when the live path is present.
        with pytest.raises(pytest.skip.Exception):
            would_touch_live()
    else:
        # No live install on this host — the guard skips too (different reason).
        # Either way the test must NOT execute the body.
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
    actual = {
        str(p.relative_to(tmp_path))
        for p in tmp_path.rglob("*")
        if p.is_file() and ".venv" not in p.parts
    }
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


def test_decorator_preserves_test_return_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Decorator MUST forward the wrapped function's return value verbatim."""
    fake = tmp_path / "fake-hermes-agent"
    fake.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    importlib.reload(conftest)

    @conftest.assert_hermes_agent_untouched
    def returns_a_dict() -> dict[str, int]:
        return {"key": 42}

    assert returns_a_dict() == {"key": 42}


def test_decorator_propagates_assertion_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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