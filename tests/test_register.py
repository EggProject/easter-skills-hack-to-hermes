"""tests/test_register.py — TDD tests for the single register(ctx) entry point.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.2, AC-1.3, AC-1.4, AC-4.10

TDD list (from plan):
  test_register_calls_ctx_register_hook_once
  test_register_does_not_call_ctx_register_skill
  test_register_silent_when_cap_patched
  test_register_emits_advisory_when_cap_unpatched
  test_register_silent_when_target_unknown
  test_register_silent_when_marker_already_seen
  test_register_warns_when_hermes_home_unset
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest


class _FakeCtx:
    """Captures register_hook / register_skill / log calls for assertions."""

    def __init__(self) -> None:
        self.hook_calls: list[tuple[str, Any]] = []
        self.skill_calls: list[tuple[Any, ...]] = []
        self.log_calls: list[str] = []

    def register_hook(self, hook_name: str, callback: Any) -> None:
        self.hook_calls.append((hook_name, callback))

    def register_skill(self, *args: Any, **kwargs: Any) -> None:
        self.skill_calls.append((args, kwargs))

    def log(self, message: str) -> None:
        self.log_calls.append(message)


def _write_unpatched_skill_utils(target: Path) -> None:
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        textwrap.dedent("""\
            def extract_skill_description(desc):
                if len(desc) > 60:
                    return desc[:60]
                return desc
            """),
        encoding="utf-8",
    )


def _write_patched_skill_utils(target: Path) -> None:
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        textwrap.dedent("""\
            def extract_skill_description(desc):
                MAX_DESCRIPTION_LENGTH = 1024
                if len(desc) > MAX_DESCRIPTION_LENGTH:
                    return desc[:MAX_DESCRIPTION_LENGTH]
                return desc
            """),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# register(ctx) wiring
# ---------------------------------------------------------------------------


def test_register_calls_ctx_register_hook_once() -> None:
    """Single ctx.register_hook('on_session_start', cb) call."""
    from hermes_skill_creator_plugin import register

    ctx = _FakeCtx()
    register(ctx)
    assert len(ctx.hook_calls) == 1
    hook_name, callback = ctx.hook_calls[0]
    assert hook_name == "on_session_start"
    assert callable(callback)


def test_register_does_not_call_ctx_register_skill() -> None:
    """The registered plugin NEVER calls ctx.register_skill."""
    from hermes_skill_creator_plugin import register

    ctx = _FakeCtx()
    register(ctx)
    assert ctx.skill_calls == []


def test_register_silent_when_cap_patched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """fixture: target_dir has patched agent/skill_utils.py; no advisory log, no marker write."""
    from hermes_skill_creator_plugin import register

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    checkout = tmp_path / "checkout"
    _write_patched_skill_utils(checkout)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(checkout))

    ctx = _FakeCtx()
    register(ctx)
    assert ctx.log_calls == []
    # The marker must NOT be created when the cap is already patched.
    assert not (hermes_home / ".hermes_skill_creator_advisory_seen").exists()


def test_register_emits_advisory_when_cap_unpatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fixture: target_dir has unpatched agent/skill_utils.py; HERMES_HERMES_AGENT_TARGET set;
    first call emits; marker written; second call does not."""
    from hermes_skill_creator_plugin import register

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    checkout = tmp_path / "checkout"
    _write_unpatched_skill_utils(checkout)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(checkout))

    ctx = _FakeCtx()
    register(ctx)
    assert len(ctx.log_calls) == 1
    log_line = ctx.log_calls[0]
    assert "[en]" in log_line and "[hu]" in log_line
    assert (hermes_home / ".hermes_skill_creator_advisory_seen").exists()

    # Second call must be silent (one-time semantics).
    ctx2 = _FakeCtx()
    register(ctx2)
    assert ctx2.log_calls == []


def test_register_silent_when_target_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing target_dir; no advisory, no marker write."""
    from hermes_skill_creator_plugin import register

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    checkout = tmp_path / "empty-checkout"
    checkout.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(checkout))

    ctx = _FakeCtx()
    register(ctx)
    assert ctx.log_calls == []
    assert not (hermes_home / ".hermes_skill_creator_advisory_seen").exists()


def test_register_silent_when_marker_already_seen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One-time semantics: if the marker is already present, do not re-emit."""
    from hermes_skill_creator_plugin import register

    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    (hermes_home / ".hermes_skill_creator_advisory_seen").write_text("seen\n", encoding="utf-8")
    checkout = tmp_path / "checkout"
    _write_unpatched_skill_utils(checkout)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(checkout))

    ctx = _FakeCtx()
    register(ctx)
    assert ctx.log_calls == []


def test_register_silent_when_hermes_home_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If HERMES_HOME is not in the env, register(ctx) stays silent (no log) and
    does not raise. Per plan 03 TDD list: test_register_silent_when_hermes_home_unset."""
    from hermes_skill_creator_plugin import register

    checkout = tmp_path / "checkout"
    _write_unpatched_skill_utils(checkout)
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(checkout))
    monkeypatch.delenv("HERMES_HOME", raising=False)

    ctx = _FakeCtx()
    register(ctx)  # must not raise
    # No HERMES_HOME -> marker path is undefined; should not log the advisory.
    assert ctx.log_calls == []
