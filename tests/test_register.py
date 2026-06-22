"""tests/test_register.py — TDD tests for src/hermes_skill_creator_plugin/__init__.py.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.2

TDD list (from plan §TDD test list / register(ctx) wiring):
  test_register_callable_in_package_init
  test_register_calls_ctx_register_hook_once
  test_register_does_not_call_ctx_register_skill
  test_register_silent_when_cap_patched
  test_register_emits_advisory_when_cap_unpatched
  test_register_silent_when_target_unknown
  test_advisory_log_contains_en_and_hu
"""

from __future__ import annotations

import inspect
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from unittest.mock import MagicMock

import pytest

from hermes_skill_creator_plugin import _advisory as _advisory_mod
from hermes_skill_creator_plugin import _register
from hermes_skill_creator_plugin._register import register
from hermes_skill_creator_plugin.i18n.messages_en import ADVISORY_CAP_EN
from hermes_skill_creator_plugin.i18n.messages_hu import ADVISORY_CAP_HU


class _RegisterCtx(Protocol):
    """Minimal contract for the ctx argument passed to register(ctx)."""

    def register_hook(self, name: str, cb: Callable[..., object]) -> object: ...
    def register_skill(self, *args: object, **kwargs: object) -> object: ...
    def log(self, message: str) -> None: ...


def _make_ctx() -> MagicMock:
    """Build a MagicMock that satisfies the ctx protocol used by register()."""
    ctx = MagicMock(spec=_RegisterCtx)
    return ctx


# ---------------------------------------------------------------------------
# Manifest / wiring (AC-1.2)
# ---------------------------------------------------------------------------


def test_register_callable_in_package_init() -> None:
    """`from hermes_skill_creator_plugin import register` resolves to a callable
    taking a single `ctx` argument (the load model: one register(ctx) in __init__.py)."""
    assert callable(register)
    sig = inspect.signature(register)
    params = list(sig.parameters.values())
    assert len(params) == 1, f"register(ctx) must take exactly one argument; got params={[p.name for p in params]}"
    assert params[0].name == "ctx"


def test_register_calls_ctx_register_hook_once() -> None:
    """register(ctx) must call ctx.register_hook('on_session_start', cb) exactly once
    and must not invoke any other ctx.* methods beyond ctx.log / ctx.register_skill /
    ctx.register_hook (which is itself called exactly once)."""
    ctx = _make_ctx()
    register(ctx)
    assert ctx.register_hook.call_count == 1
    args, _kwargs = ctx.register_hook.call_args
    assert args[0] == "on_session_start"
    assert callable(args[1])


def test_register_does_not_call_ctx_register_skill() -> None:
    """The plugin NEVER calls ctx.register_skill (the skill is shipped standalone
    via Script #2, not registered through the plugin loader)."""
    ctx = _make_ctx()
    register(ctx)
    ctx.register_skill.assert_not_called()


# ---------------------------------------------------------------------------
# Cap-state gate (AC-1.2 advisory-only semantics)
# ---------------------------------------------------------------------------


def test_register_silent_when_cap_patched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture: target_dir has patched agent/skill_utils.py. No advisory log,
    no marker write, register returns cleanly."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                MAX_DESCRIPTION_LENGTH = 1024
                if len(desc) > MAX_DESCRIPTION_LENGTH:
                    return desc[:MAX_DESCRIPTION_LENGTH]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    marker = home / ".hermes_skill_creator_advisory_seen"
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))
    monkeypatch.setenv("HERMES_HOME", str(home))

    ctx = _make_ctx()
    register(ctx)

    ctx.log.assert_not_called()
    assert not marker.exists()


def test_register_emits_advisory_when_cap_unpatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture: target_dir has unpatched agent/skill_utils.py. First call emits
    the bilingual advisory and writes the marker; second call is silent."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                if len(desc) > 60:
                    return desc[:60]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    marker = home / ".hermes_skill_creator_advisory_seen"
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))
    monkeypatch.setenv("HERMES_HOME", str(home))

    ctx = _make_ctx()
    register(ctx)

    assert ctx.log.call_count == 1
    log_message = ctx.log.call_args[0][0]
    assert ADVISORY_CAP_EN in log_message
    assert ADVISORY_CAP_HU in log_message
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "advisory shown\n"

    # Second call: marker exists -> no log, no rewrite.
    ctx2 = _make_ctx()
    register(ctx2)
    ctx2.log.assert_not_called()


def test_register_silent_when_target_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing target_dir / agent/skill_utils.py -> no advisory, no marker write."""
    target = tmp_path / "checkout"
    target.mkdir(parents=True, exist_ok=True)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    marker = home / ".hermes_skill_creator_advisory_seen"
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))
    monkeypatch.setenv("HERMES_HOME", str(home))

    ctx = _make_ctx()
    register(ctx)

    ctx.log.assert_not_called()
    assert not marker.exists()


def test_register_emits_advisory_with_default_marker_when_home_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fixture: HERMES_HOME is UNSET, target_dir has unpatched skill_utils.py.
    Exercises the ``if not home:`` fallback in ``_advisory_marker_path``
    (line 41) which resolves the marker to ``~/.hermes/hermes-agent`` via
    ``os.path.expanduser``. The advisory is still emitted and the marker
    is written under the resolved default home.

    CI runs on a fresh Ubuntu runner with no ``HERMES_HOME`` and no live
    ``~/.hermes/hermes-agent``, so this branch is the one that the gate
    actually exercises; without this test the fallback line is uncovered.
    """
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                if len(desc) > 60:
                    return desc[:60]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    # Default home (no live install) so the expanduser fallback lands in
    # a writable, isolated tmp_path subtree instead of touching the host.
    default_home = tmp_path / "default-home"
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("HOME", str(default_home))
    # Pre-create the parent dirs so ``Path.write_text`` inside emit_advisory
    # can land the marker file. ``emit_advisory`` swallows OSError, so a
    # missing parent dir would make the marker-write branch appear covered
    # while silently no-oping — pre-creating keeps the assertion honest.
    (default_home / ".hermes" / "hermes-agent").mkdir(parents=True, exist_ok=True)

    ctx = _make_ctx()
    register(ctx)

    assert ctx.log.call_count == 1
    log_message = ctx.log.call_args[0][0]
    assert ADVISORY_CAP_EN in log_message
    assert ADVISORY_CAP_HU in log_message
    # Marker MUST land under the expanduser-resolved default home, NOT
    # under any caller-supplied HERMES_HOME (which is unset here).
    default_marker = default_home / ".hermes" / "hermes-agent" / ".hermes_skill_creator_advisory_seen"
    assert default_marker.exists()
    assert default_marker.read_text(encoding="utf-8") == "advisory shown\n"


def test_advisory_log_contains_en_and_hu() -> None:
    """Static check: both bilingual halves are present in the i18n constants
    AND the constant pair contains the language tag prefixes."""
    assert ADVISORY_CAP_EN.startswith("[en]")
    assert ADVISORY_CAP_HU.startswith("[hu]")
    assert "60" in ADVISORY_CAP_EN
    assert "60" in ADVISORY_CAP_HU


# ---------------------------------------------------------------------------
# No setattr / no skill import (hard invariant)
# ---------------------------------------------------------------------------


def test_register_module_does_not_call_setattr() -> None:
    """Static check: the package __init__.py AND _register.py do NOT call setattr
    on any Hermes module, do NOT import agent.skill_utils, do NOT import
    prompt_builder. Per the plan: NO setattr, NO runtime monkey-patch."""
    import ast as _ast

    init_path = Path(_advisory_mod.__file__).resolve().parent / "__init__.py"
    register_path = Path(_register.__file__).resolve()
    for path in (init_path, register_path):
        mod = _ast.parse(path.read_text(encoding="utf-8"))
        for node in _ast.walk(mod):
            is_str_const = (
                isinstance(node, _ast.Expr)
                and isinstance(node.value, _ast.Constant)
                and isinstance(node.value.value, str)
            )
            if is_str_const:
                continue
            if isinstance(node, _ast.Call):
                func = node.func
                if isinstance(func, _ast.Name) and func.id == "setattr":
                    pytest.fail(f"{path.name} must not call setattr")
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    if alias.name.startswith("agent.skill_utils"):
                        pytest.fail(f"{path.name} must not import agent.skill_utils")
                    if alias.name.startswith("prompt_builder"):
                        pytest.fail(f"{path.name} must not import prompt_builder")
            if isinstance(node, _ast.ImportFrom):
                if node.module and node.module.startswith("agent.skill_utils"):
                    pytest.fail(f"{path.name} must not import agent.skill_utils")
                if node.module and node.module.startswith("prompt_builder"):
                    pytest.fail(f"{path.name} must not import prompt_builder")
