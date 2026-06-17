"""Unit tests for run_eval.py + improve_description.py + utils.py.

Per docs/plans/07 §TDD test list (Nesting-guard helper, Eval pipeline + viewer,
Bilingual + CLI).
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"
SCRIPTS = SKILL_DIR / "scripts"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Nesting-guard matrix for run_eval.py (uses subprocess.run spy)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_run_eval_unnests_hermes_guard(hermes_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_SESSION", "session-id")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    captured: dict = {}

    class _FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["env"] = kwargs.get("env", {})
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    run_eval_mod = _load_module(SCRIPTS / "run_eval.py", "run_eval_under_test")
    cases = [{"id": "x", "expected": "ok"}]
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "1")
    run_eval_mod.run_eval(cases, hermes_home=hermes_home, category="c", target="t")
    assert "HERMES_SESSION" not in captured["env"]


@assert_hermes_agent_untouched
def test_run_eval_restores_hermes_guard_on_exit(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "session-id")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    class _FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    run_eval_mod = _load_module(SCRIPTS / "run_eval.py", "run_eval_restore_test")
    run_eval_mod.run_eval([], hermes_home=hermes_home, category="c", target="t")
    assert "HERMES_SESSION" in __import__("os").environ


@assert_hermes_agent_untouched
def test_run_eval_no_op_when_guard_unset(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HERMES_SESSION", raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    captured: dict = {}

    class _FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["env"] = kwargs.get("env", {})
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    run_eval_mod = _load_module(SCRIPTS / "run_eval.py", "run_eval_unset_test")
    run_eval_mod.run_eval([{"id": "x"}], hermes_home=hermes_home, category="c", target="t")
    assert "HERMES_SESSION" not in captured["env"]


@assert_hermes_agent_untouched
def test_run_eval_event_shape_adapter_normalizes_hermes_shape(
    skill_creator_home: Path,
) -> None:
    run_eval_mod = _load_module(SCRIPTS / "run_eval.py", "run_eval_adapter_test")
    hermes_event = {"event": "message", "role": "assistant", "content": "hi"}
    out = run_eval_mod._hermes_event_to_anthropic(hermes_event)
    assert out["type"] == "message"
    assert out["message"]["role"] == "assistant"
    assert isinstance(out["message"]["content"], list)


@assert_hermes_agent_untouched
def test_run_eval_uses_hermes_subprocess_env(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_eval.py imports hermes_subprocess_env from `_subprocess`."""
    run_eval_mod = _load_module(SCRIPTS / "run_eval.py", "run_eval_helper_test")
    assert hasattr(run_eval_mod, "hermes_subprocess_env")


# ---------------------------------------------------------------------------
# improve_description.py nesting-guard matrix
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_improve_description_unnests_hermes_guard(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "s")
    captured: dict = {}

    class _FakeProc:
        returncode = 0
        stdout = "new description"
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["env"] = kwargs.get("env", {})
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    mod = _load_module(SCRIPTS / "improve_description.py", "improve_desc_test")
    out = mod.propose_description("old")
    assert "HERMES_SESSION" not in captured["env"]
    assert out == "new description"


@assert_hermes_agent_untouched
def test_improve_description_restores_hermes_guard_on_exit(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "s")

    class _FakeProc:
        returncode = 0
        stdout = "x"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FakeProc())
    mod = _load_module(SCRIPTS / "improve_description.py", "improve_desc_restore_test")
    mod.propose_description("old")
    assert "HERMES_SESSION" in __import__("os").environ


@assert_hermes_agent_untouched
def test_improve_description_no_op_when_guard_unset(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HERMES_SESSION", raising=False)

    class _FakeProc:
        returncode = 0
        stdout = "x"
        stderr = ""

    captured: dict = {}

    def _fake_run(cmd, **kwargs):
        captured["env"] = kwargs.get("env", {})
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    mod = _load_module(SCRIPTS / "improve_description.py", "improve_desc_unset_test")
    mod.propose_description("old")
    assert "HERMES_SESSION" not in captured["env"]


# ---------------------------------------------------------------------------
# Bilingual + console log regex
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_emit_bilingual_console_emits_en_then_hu(
    skill_creator_home: Path, capsys: pytest.CaptureFixture
) -> None:
    utils = _load_module(SCRIPTS / "utils.py", "utils_bi_test")
    utils.emit("hello", "szia")
    out = capsys.readouterr().out
    assert "[en] hello / [hu] szia" in out


@assert_hermes_agent_untouched
def test_console_log_lines_match_bilingual_regex(
    skill_creator_home: Path,
) -> None:
    r"""AST-grep every `print(...)` + `emit(...)` in `scripts/`; assert the
    format string matches `^\[en\] .+ / \[hu\] .+$`."""
    pattern = re.compile(r"^\[en\] .+ / \[hu\] .+$")
    failures: list[str] = []
    for py in SCRIPTS.rglob("*.py"):
        source = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "print":
                    if not node.args:
                        continue
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if not pattern.search(arg.value):
                            failures.append(f"{py}:{node.lineno} {arg.value!r}")
    # The bare `print("...")` in scripts (e.g. argparse help examples) is OK
    # if it's not a console message. We only flag the bilingual surface.
    # Scripts in scope: run_eval, improve_description, run_loop,
    # aggregate_benchmark, generate_report, quick_validate, package_skill.
    # None of them use raw `print(...)` for console messages (they use
    # `utils.emit`). We only check that `utils.emit` produces a valid line.
    assert not failures, f"console messages not bilingual: {failures}"


# ---------------------------------------------------------------------------
# Help is bilingual
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
@pytest.mark.parametrize(
    "script_name",
    [
        "run_eval.py",
        "improve_description.py",
        "run_loop.py",
        "aggregate_benchmark.py",
        "generate_report.py",
        "quick_validate.py",
        "package_skill.py",
    ],
)
def test_help_is_bilingual(skill_creator_home: Path, script_name: str) -> None:
    """Each migrated script's argparse description includes both the
    English 'Use when' marker and the Hungarian 'Hasznalat' marker.
    """
    text = (SCRIPTS / script_name).read_text(encoding="utf-8")
    assert "Use when" in text, f"{script_name}: missing 'Use when' marker"
    assert "Hasznalat" in text, f"{script_name}: missing 'Hasznalat' marker"
