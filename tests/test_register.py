"""tests/test_register.py — TDD tests for src/easter_hermes_sorry_skills/__init__.py.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.2

TDD list (from plan §TDD test list / register(ctx) wiring):
  test_register_callable_in_package_init
  test_register_calls_ctx_register_hook_once
  test_register_does_not_call_ctx_register_skill
  test_register_silent_when_cap_patched
  test_register_emits_advisory_when_cap_unpatched
  test_register_silent_when_target_unknown
  test_register_emits_advisory_every_time
"""

from __future__ import annotations

import inspect
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from unittest.mock import MagicMock

import pytest

from easter_hermes_sorry_skills import _register
from easter_hermes_sorry_skills._i18n_pick import pick
from easter_hermes_sorry_skills._register import register


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
    """`from easter_hermes_sorry_skills import register` resolves to a callable
    taking `ctx` and `lang` arguments (the load model: register(ctx, lang))."""
    assert callable(register)
    sig = inspect.signature(register)
    params = list(sig.parameters.values())
    param_names = [p.name for p in params]
    expected = ["ctx", "lang"]
    assert param_names == expected, f"register must take exactly {expected}; got params={param_names}"


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
    register returns cleanly."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                _MAX_DESCRIPTION_LENGTH = 1024
                if len(desc) > _MAX_DESCRIPTION_LENGTH:
                    return desc[:_MAX_DESCRIPTION_LENGTH]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))

    ctx = _make_ctx()
    register(ctx)

    ctx.log.assert_not_called()


@pytest.mark.parametrize("lang", ["en", "hu"])
def test_register_emits_advisory_when_cap_unpatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lang: str) -> None:
    """Fixture: target_dir has unpatched agent/skill_utils.py. register emits
    the PLAIN language-specific advisory (no [en].../[hu]... bilingual format)."""
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
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))

    ctx = _make_ctx()
    register(ctx, lang=lang)

    assert ctx.log.call_count == 1
    log_message = ctx.log.call_args[0][0]
    # PLAIN english or PLAIN hungarian — NO "[en] ... / [hu] ..." format.
    assert log_message == pick(lang).ADVISORY_CAP


def test_register_silent_when_target_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing target_dir / agent/skill_utils.py -> no advisory."""
    target = tmp_path / "checkout"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))

    ctx = _make_ctx()
    register(ctx)

    ctx.log.assert_not_called()


@pytest.mark.parametrize("lang", ["en", "hu"])
def test_register_emits_advisory_every_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lang: str) -> None:
    """The register logs the advisory EVERY TIME the cap is un-raised. There is
    no marker-file gating: two back-to-back register() calls on the same target
    both emit ctx.log exactly once each (no second-call silencing)."""
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
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))

    ctx1 = _make_ctx()
    register(ctx1, lang=lang)
    ctx2 = _make_ctx()
    register(ctx2, lang=lang)

    assert ctx1.log.call_count == 1
    assert ctx2.log.call_count == 1
    expected = pick(lang).ADVISORY_CAP
    assert ctx1.log.call_args[0][0] == expected
    assert ctx2.log.call_args[0][0] == expected


# ---------------------------------------------------------------------------
# No setattr / no skill import (hard invariant)
# ---------------------------------------------------------------------------


def test_register_module_does_not_call_setattr() -> None:
    """Static check: the package __init__.py AND _register.py do NOT call setattr
    on any Hermes module, do NOT import agent.skill_utils, do NOT import
    prompt_builder. Per the plan: NO setattr, NO runtime monkey-patch."""
    import ast as _ast

    init_path = Path(_register.__file__).resolve().parent / "__init__.py"
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
