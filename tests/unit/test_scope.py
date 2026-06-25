"""Unit tests for ``easter_hermes_sorry_skills._scope`` (TDD test list, plan 06).

TDD list (plan 06 §TDD test list → hermes_home_scope):
- test_set_hermes_home_override_called
- test_env_var_mirrored_into_os_environ
- test_hub_install_reads_mirrored_env
- test_scope_restores_on_normal_exit
- test_scope_restores_on_exception
- test_scope_restores_when_env_was_unset_before

The dual-mirror contract: ``hermes_home_scope(path)`` sets BOTH
``hermes_constants.set_hermes_home_override(str(path))`` AND
``os.environ['HERMES_HOME']=str(path)`` and restores BOTH on exit
(try/finally), even when an exception propagates.

The tests inject a fake ``hermes_constants`` module via ``monkeypatch``
into ``easter_hermes_sorry_skills._scope`` so they do NOT depend on the
real ``hermes_constants`` being importable. This is consistent with the
project rule that Script #2 tests run against tmp_path fixtures only and
must never touch the live ``~/.hermes`` install.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Test-injected fake hermes_constants module.
# ---------------------------------------------------------------------------


class _FakeOverrideToken:
    """Token returned by ``set_hermes_home_override``. Carries the prior path
    so ``reset_hermes_home_override`` can restore the state captured at
    set-time (mirroring the real contextvars-backed token)."""

    __slots__ = ("prev",)

    def __init__(self, prev: str | None) -> None:
        self.prev = prev


def _make_fake_hermes_constants(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str = "_hermes_constants_fake_for_scope_tests",
) -> types.ModuleType:
    """Build and register a fake ``hermes_constants`` module.

    Records each call so tests can assert the override token and env var
    were both set and both restored.
    """
    state: dict[str, object] = {
        "current": None,  # the active override path
        "set_calls": [],
        "reset_calls": [],
        "get_calls": 0,
    }

    def get_hermes_home_override() -> str | None:
        state["get_calls"] = int(state["get_calls"]) + 1
        return state["current"]

    def set_hermes_home_override(path: str | Path | None) -> _FakeOverrideToken:
        prev = state["current"]
        state["set_calls"].append(path)
        state["current"] = str(path) if path is not None else None
        return _FakeOverrideToken(prev)

    def reset_hermes_home_override(token: _FakeOverrideToken) -> None:
        state["reset_calls"].append(token)
        state["current"] = token.prev

    fake = types.ModuleType(module_name)
    fake.get_hermes_home_override = get_hermes_home_override
    fake.set_hermes_home_override = set_hermes_home_override
    fake.reset_hermes_home_override = reset_hermes_home_override
    fake._state = state
    monkeypatch.setitem(sys.modules, module_name, fake)
    return fake


# ---------------------------------------------------------------------------
# Import path under test.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_hermes_constants(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Patch ``hermes_constants`` import in ``_scope`` to a fake module.

    Registers the fake under the REAL name ``hermes_constants`` BEFORE the
    ``_scope`` module is imported so the ``from hermes_constants import ...``
    line in ``_scope.hermes_home_scope`` resolves against the fake.
    """
    fake = _make_fake_hermes_constants(monkeypatch, module_name="hermes_constants")
    return fake


@pytest.fixture
def scope_module(fake_hermes_constants: types.ModuleType, monkeypatch: pytest.MonkeyPatch):
    """Import the ``_scope`` module with its ``hermes_constants`` import patched.

    The production module does ``from hermes_constants import ...`` at the top
    of ``hermes_home_scope``. To intercept that without importing the real
    module, we register a fake ``hermes_constants`` in ``sys.modules`` BEFORE
    the import and use ``importlib.reload`` if the module was already cached.
    """
    # Ensure hermes_constants is the fake before importing _scope.
    import importlib

    mod_name = "easter_hermes_sorry_skills._scope"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


@pytest.fixture
def scope_path(tmp_path: Path) -> Path:
    """A scratch directory used as the scoped HERMES_HOME."""
    p = tmp_path / "scoped-home"
    p.mkdir()
    return p


# ---------------------------------------------------------------------------
# TDD list — hermes_home_scope.
# ---------------------------------------------------------------------------


def test_set_hermes_home_override_called(scope_module, fake_hermes_constants, scope_path: Path) -> None:
    """Entering the scope calls ``set_hermes_home_override(str(path))``."""
    state = fake_hermes_constants._state
    with scope_module.hermes_home_scope(scope_path):
        # While inside the scope the override should match the path.
        assert state["current"] == str(scope_path)
        assert len(state["set_calls"]) == 1
        assert str(state["set_calls"][0]) == str(scope_path)


def test_env_var_mirrored_into_os_environ(scope_module, scope_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``os.environ['HERMES_HOME']`` is set to ``str(path)`` inside the scope."""
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with scope_module.hermes_home_scope(scope_path):
        assert os.environ["HERMES_HOME"] == str(scope_path)


def test_hub_install_reads_mirrored_env(scope_module, scope_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake hub call inside the scope sees the mirrored env var (D7)."""
    monkeypatch.delenv("HERMES_HOME", raising=False)
    seen: list[str | None] = []

    def fake_hub(*args: object, **kwargs: object) -> None:
        seen.append(os.environ.get("HERMES_HOME"))

    with scope_module.hermes_home_scope(scope_path):
        fake_hub("skill-creator")
    assert seen == [str(scope_path)]


def test_scope_restores_on_normal_exit(
    scope_module,
    fake_hermes_constants,
    scope_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On normal exit both the override token AND env var are restored."""
    state = fake_hermes_constants._state
    prev_env = "/prev/hermes/home"
    monkeypatch.setenv("HERMES_HOME", prev_env)
    state["current"] = prev_env

    with scope_module.hermes_home_scope(scope_path):
        # Inside: both are set to the scoped path.
        assert os.environ["HERMES_HOME"] == str(scope_path)
        assert state["current"] == str(scope_path)

    # After: both restored to the prior values.
    assert os.environ["HERMES_HOME"] == prev_env
    assert state["current"] == prev_env
    assert len(state["reset_calls"]) == 1


def test_scope_restores_on_exception(
    scope_module,
    fake_hermes_constants,
    scope_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception inside the scope still restores both values."""
    state = fake_hermes_constants._state
    prev_env = "/prev/hermes/home"
    monkeypatch.setenv("HERMES_HOME", prev_env)
    state["current"] = prev_env

    with pytest.raises(RuntimeError, match="boom"):
        with scope_module.hermes_home_scope(scope_path):
            raise RuntimeError("boom")

    assert os.environ["HERMES_HOME"] == prev_env
    assert state["current"] == prev_env
    assert len(state["reset_calls"]) == 1


def test_scope_restores_when_env_was_unset_before(
    scope_module,
    fake_hermes_constants,
    scope_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the env var was unset before, it is unset after exit (not left as str(path))."""
    state = fake_hermes_constants._state
    monkeypatch.delenv("HERMES_HOME", raising=False)
    state["current"] = None

    with scope_module.hermes_home_scope(scope_path):
        assert os.environ["HERMES_HOME"] == str(scope_path)

    assert "HERMES_HOME" not in os.environ
    assert state["current"] is None
