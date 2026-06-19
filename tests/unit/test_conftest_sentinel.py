"""Direct unit tests for the conftest ``assert_hermes_agent_untouched_sentinel``
function and the helper functions. These exist to cover lines that are
otherwise only reachable via conditional branches in the conftest fixture.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

import pytest

conftest = importlib.import_module("tests.conftest")


def test_assert_sentinel_no_op_when_pre_is_none() -> None:
    """``assert_hermes_agent_untouched_sentinel(None)`` must be a no-op."""
    conftest.assert_hermes_agent_untouched_sentinel(None)


def test_assert_sentinel_no_op_when_no_live_install(tmp_path, monkeypatch) -> None:
    """When the live install does not exist, the sentinel is a no-op."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Should not raise.
    conftest.assert_hermes_agent_untouched_sentinel("any-pre-hash")


def test_assert_sentinel_raises_on_mutation(tmp_path, monkeypatch) -> None:
    """When the live install hash differs from pre, the sentinel raises."""
    hermes_dir = tmp_path / ".hermes" / "hermes-agent" / "agent"
    hermes_dir.mkdir(parents=True)
    (hermes_dir / "skill_utils.py").write_text("# content", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(AssertionError):
        conftest.assert_hermes_agent_untouched_sentinel("not-the-real-hash")


def test_no_live_install_sentinel_helper() -> None:
    """The no-live-install helper returns the documented token."""
    assert conftest._no_live_install_sentinel() == "sentinel-no-live-install"


def test_install_sentinel_finalizer_registers_check(tmp_path) -> None:
    """The finalizer helper registers a finalizer on the request and runs it."""
    import hashlib

    target = tmp_path / "skill_utils.py"
    target.write_text("# content", encoding="utf-8")
    pre_hash = hashlib.sha256(target.read_bytes()).hexdigest()

    registered: list[Callable[[], None]] = []

    class FakeRequest:
        def addfinalizer(self, fn: Callable[[], None]) -> None:
            registered.append(fn)

    conftest._install_sentinel_finalizer(FakeRequest(), target, pre_hash)
    assert len(registered) == 1
    # Run the finalizer against the same content: should not raise.
    registered[0]()
    # Mutate the file: finalizer should raise.
    target.write_text("# changed", encoding="utf-8")
    with pytest.raises(AssertionError):
        registered[0]()
    # Mutate to delete: finalizer returns silently.
    target.unlink()
    registered[0]()


def test_real_hermes_agent_sentinel_via_fixture(tmp_path, monkeypatch, real_hermes_agent_sentinel: str) -> None:
    """End-to-end: requesting the fixture returns the no-op token
    (when no live install exists) or "sentinel-ok" (when one does).
    Exercises line 240 (no-live-install return)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # We can't reliably force the no-install branch from a test that
    # requests the fixture, but at least we exercise the fixture's
    # overall flow. The branch is covered by direct helper test above.
    assert real_hermes_agent_sentinel in {"sentinel-no-live-install", "sentinel-ok"}


def test_real_hermes_agent_sentinel_no_install_branch(tmp_path, monkeypatch) -> None:
    """Cover the no-live-install branch (line 240) by directly invoking the
    implementation with a path that has no live install."""
    monkeypatch.setenv("HOME", str(tmp_path))
    finalizers: list[Callable[[], None]] = []

    class StubRequest:
        def addfinalizer(self, fn: Callable[[], None]) -> None:
            finalizers.append(fn)

    result = conftest._real_hermes_agent_sentinel_impl(request=StubRequest())
    assert result == "sentinel-no-live-install"
    # No finalizer was registered (early return).
    assert finalizers == []


def test_ensure_hermes_cli_profiles_stub_idempotent_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``hermes_cli.profiles`` is already in ``sys.modules``, the helper
    is a no-op (early return)."""
    import sys

    pre = sys.modules.get("hermes_cli.profiles")
    conftest._ensure_hermes_cli_profiles_stub()
    assert sys.modules.get("hermes_cli.profiles") is pre


def test_ensure_hermes_cli_profiles_stub_creates_when_hermes_cli_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``hermes_cli`` is already in sys.modules but ``profiles`` isn't,
    the helper adds ``profiles`` to the existing module rather than replacing it."""
    import sys
    import types

    fake_parent = types.ModuleType("hermes_cli")
    monkeypatch.setitem(sys.modules, "hermes_cli", fake_parent)
    monkeypatch.delitem(sys.modules, "hermes_cli.profiles", raising=False)
    conftest._ensure_hermes_cli_profiles_stub()
    assert sys.modules["hermes_cli.profiles"].ProfileInfo is not None
    assert sys.modules["hermes_cli"].profiles is sys.modules["hermes_cli.profiles"]
