"""Unit tests for skills/skill-creator/_subprocess.py.

These tests cover the TDD contract for the single source of truth helper
that strips nesting-guard vars from the subprocess env.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"


def _import_helper():
    """Import hermes_subprocess_env from the skill dir (NOT the plugin)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "skill_creator_subprocess", SKILL_DIR / "_subprocess.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@assert_hermes_agent_untouched
def test_hermes_subprocess_env_strips_hermes_session(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "active-session-id")
    monkeypatch.setenv("PATH", "/usr/bin")
    helper = _import_helper()
    env = helper.hermes_subprocess_env()
    assert "HERMES_SESSION" not in env
    assert env["PATH"] == "/usr/bin"


@assert_hermes_agent_untouched
def test_hermes_subprocess_env_strips_claudecode(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("HOME", "/home/test")
    helper = _import_helper()
    env = helper.hermes_subprocess_env()
    assert "CLAUDECODE" not in env
    assert env["HOME"] == "/home/test"


@assert_hermes_agent_untouched
def test_hermes_subprocess_env_preserves_other_vars(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "x")
    monkeypatch.setenv("CLAUDECODE", "y")
    monkeypatch.setenv("PATH", "/bin")
    monkeypatch.setenv("HOME", "/home/u")
    monkeypatch.setenv("USER", "u")
    helper = _import_helper()
    env = helper.hermes_subprocess_env()
    assert env["PATH"] == "/bin"
    assert env["HOME"] == "/home/u"
    assert env["USER"] == "u"


@assert_hermes_agent_untouched
def test_hermes_subprocess_env_does_not_mutate_parent(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SESSION", "kept")
    monkeypatch.setenv("CLAUDECODE", "kept")
    helper = _import_helper()
    helper.hermes_subprocess_env()
    import os as _os

    assert _os.environ.get("HERMES_SESSION") == "kept"
    assert _os.environ.get("CLAUDECODE") == "kept"


@assert_hermes_agent_untouched
def test_nesting_guard_var_constant_is_hermes_session(hermes_home: Path) -> None:
    helper = _import_helper()
    assert helper.NESTING_GUARD_VAR == "HERMES_SESSION"


@assert_hermes_agent_untouched
def test_hermes_subprocess_env_when_guard_unset(
    hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HERMES_SESSION", raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("PATH", "/bin")
    helper = _import_helper()
    env = helper.hermes_subprocess_env()
    assert "HERMES_SESSION" not in env
    assert "CLAUDECODE" not in env
    assert env["PATH"] == "/bin"


@assert_hermes_agent_untouched
def test_helper_is_single_source_of_truth(hermes_home: Path) -> None:
    """The `HERMES_SESSION` constant is defined in EXACTLY ONE place
    (`NESTING_GUARD_VAR` in `skills/skill-creator/_subprocess.py`).

    Other files (run_eval.py, SKILL.md, agents/*.md) may MENTION
    `HERMES_SESSION` in docstrings / comments (provenance) but they must
    NOT redeclare or hardcode the var name in code.

    The test walks the AST for `ast.Assign` targets named `NESTING_GUARD_VAR`
    and asserts exactly one such assignment exists, located in `_subprocess.py`.
    """
    import ast

    assignments: list[tuple[Path, int, str]] = []
    for py in SKILL_DIR.rglob("*.py"):
        source = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            target: ast.expr | None = None
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        target = t
                        break
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target = node.target
            if target is not None and target.id == "NESTING_GUARD_VAR":
                assignments.append((py, node.lineno, target.id))
    assert (
        len(assignments) == 1
    ), f"NESTING_GUARD_VAR must be assigned exactly once (got {len(assignments)}: {assignments})"
    assert assignments[0][0].name == "_subprocess.py"
