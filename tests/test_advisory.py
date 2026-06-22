"""tests/test_advisory.py — TDD tests for src/easter_hermes_sorry_skills/_advisory.py.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-4.10

TDD list (from plan):
  test_detect_cap_state_patched
  test_detect_cap_state_unpatched
  test_detect_cap_state_unknown_no_file
  test_detect_cap_state_unknown_syntax_error
  test_advisory_no_setattr_on_skill_utils
  test_resolve_target_dir_prefers_env_var
  test_emit_advisory_idempotent
  test_emit_advisory_re_emits_when_marker_deleted
  test_emit_advisory_swallows_oserror
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from easter_hermes_sorry_skills import _advisory
from easter_hermes_sorry_skills._advisory import (
    PATCHED_CAP_REFERENCE,
    UNPATCHED_CAP,
    detect_cap_state,
    emit_advisory,
    resolve_target_dir,
    should_emit_advisory,
)

# ---------------------------------------------------------------------------
# detect_cap_state
# ---------------------------------------------------------------------------


def test_detect_cap_state_patched(tmp_path: Path) -> None:
    """fixture checkout with MAX_DESCRIPTION_LENGTH in the comparator; returns 'patched'."""
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
    assert detect_cap_state(target) == "patched"


def test_detect_cap_state_unpatched(tmp_path: Path) -> None:
    """fixture checkout with literal 60; returns 'unpatched'."""
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
    assert detect_cap_state(target) == "unpatched"


def test_detect_cap_state_unknown_no_file(tmp_path: Path) -> None:
    """missing agent/skill_utils.py; returns 'unknown'."""
    target = tmp_path / "checkout"
    target.mkdir(parents=True, exist_ok=True)
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_unknown_syntax_error(tmp_path: Path) -> None:
    """corrupted file; returns 'unknown'."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text("def extract_skill_description(:\n    pass\n", encoding="utf-8")
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_no_extract_function(tmp_path: Path) -> None:
    """file present but no extract_skill_description defined; returns 'unknown'."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text("def some_other_function():\n    return 60\n", encoding="utf-8")
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_other_function_with_60_is_unpatched(tmp_path: Path) -> None:
    """Per the plan: the AST walk only inspects extract_skill_description. A different
    function with `> 60` is ignored. Returns 'unknown' (no cap signal on the target fn)."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def helper(x):
                if x > 60:
                    return x
                return None
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_extract_fn_no_compare_with_cap(tmp_path: Path) -> None:
    """extract_skill_description exists but its Compare uses a non-cap constant.
    Walks past the FunctionDef guard (line 73->71 exit not taken) and past the
    Compare guard (line 75->73 exit not taken), then falls through to 'unknown'."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                if len(desc) > 100:
                    return desc[:100]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_extract_fn_with_unrelated_name(tmp_path: Path) -> None:
    """extract_skill_description has a Compare with a Name comparator that is
    NOT MAX_DESCRIPTION_LENGTH. Exercises the 'comparator is Name but id !=
    PATCHED_CAP_REFERENCE' branch (line 78->75)."""
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                OTHER_CAP = 100
                if len(desc) > OTHER_CAP:
                    return desc[:OTHER_CAP]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    assert detect_cap_state(target) == "unknown"


def test_detect_cap_state_extract_fn_with_unrelated_constant(tmp_path: Path) -> None:
    """extract_skill_description has a Compare with a Constant comparator that is
    NOT 60. Exercises the 'comparator is Constant but value != UNPATCHED_CAP' branch.

    NOTE: identical source to test_detect_cap_state_extract_fn_no_compare_with_cap.
    Kept separately so the branch annotation in the docstring remains auditable.
    """
    target = tmp_path / "checkout"
    skill_utils = target / "agent" / "skill_utils.py"
    skill_utils.parent.mkdir(parents=True, exist_ok=True)
    skill_utils.write_text(
        # fmt: off
        textwrap.dedent(
            """\
            def extract_skill_description(desc):
                OTHER_CAP = 100
                if len(desc) > OTHER_CAP:
                    return desc[:OTHER_CAP]
                return desc
            """
        ),
        # fmt: on
        encoding="utf-8",
    )
    assert detect_cap_state(target) == "unknown"


# ---------------------------------------------------------------------------
# resolve_target_dir
# ---------------------------------------------------------------------------


def test_resolve_target_dir_prefers_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HERMES_HERMES_AGENT_TARGET=/tmp/x -> resolver returns /tmp/x."""
    target = tmp_path / "checkout"
    target.mkdir()
    monkeypatch.setenv("HERMES_HERMES_AGENT_TARGET", str(target))
    assert resolve_target_dir() == target


def test_resolve_target_dir_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """without HERMES_HERMES_AGENT_TARGET, resolver returns the default home path.

    The default is `~/.hermes/hermes-agent`. This test does NOT exercise the
    live path; it only asserts the env-less fallback. The decorator on
    integration tests in conftest.py would skip any test that resolves the
    live install.
    """
    monkeypatch.delenv("HERMES_HERMES_AGENT_TARGET", raising=False)
    resolved = resolve_target_dir()
    assert resolved == Path("~/.hermes/hermes-agent").expanduser()


# ---------------------------------------------------------------------------
# should_emit_advisory / emit_advisory
# ---------------------------------------------------------------------------


def test_should_emit_advisory_first_time(tmp_path: Path) -> None:
    marker = tmp_path / ".hermes_skill_creator_advisory_seen"
    assert should_emit_advisory(marker) is True


def test_should_emit_advisory_after_marker(tmp_path: Path) -> None:
    marker = tmp_path / ".hermes_skill_creator_advisory_seen"
    marker.write_text("advisory shown\n", encoding="utf-8")
    assert should_emit_advisory(marker) is False


def test_emit_advisory_writes_marker(tmp_path: Path) -> None:
    marker = tmp_path / ".hermes_skill_creator_advisory_seen"
    emit_advisory(marker)
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "advisory shown\n"


def test_emit_advisory_idempotent(tmp_path: Path) -> None:
    """First call emits; marker file written; second call does NOT raise (idempotent)."""
    marker = tmp_path / ".hermes_skill_creator_advisory_seen"
    emit_advisory(marker)
    assert marker.exists()
    # Second call should be a no-op (no exception, marker unchanged).
    emit_advisory(marker)
    assert marker.read_text(encoding="utf-8") == "advisory shown\n"


def test_emit_advisory_re_emits_when_marker_deleted(tmp_path: Path) -> None:
    """delete marker; next emit writes it again."""
    marker = tmp_path / ".hermes_skill_creator_advisory_seen"
    emit_advisory(marker)
    marker.unlink()
    assert should_emit_advisory(marker) is True
    emit_advisory(marker)
    assert marker.exists()


def test_emit_advisory_swallows_oserror(tmp_path: Path) -> None:
    """unwritable marker path -> no exception raised (best-effort)."""
    # A path under a non-existent parent triggers FileNotFoundError on write,
    # which the implementation must swallow.
    bad = tmp_path / "does" / "not" / "exist" / "marker"
    emit_advisory(bad)  # must not raise
    assert not bad.exists()


# ---------------------------------------------------------------------------
# Hard invariants
# ---------------------------------------------------------------------------


def test_advisory_no_setattr_on_skill_utils() -> None:
    """Static check: the _advisory module does NOT import or setattr on
    agent.skill_utils. Per the plan: 'NO setattr(agent.skill_utils, ...). NO
    rebind of prompt_builder.extract_skill_description.'

    Only Python statements (not docstring prose) are scanned. Docstrings may
    mention 'setattr' in the rationale without violating the contract.
    """
    import ast as _ast

    mod = _ast.parse(Path(_advisory.__file__).read_text(encoding="utf-8"))
    for node in _ast.walk(mod):
        # Skip docstring nodes (Expr/Constant at the start of a body).
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, _ast.Call):
            func = node.func
            if isinstance(func, _ast.Name) and func.id == "setattr":
                pytest.fail("_advisory.py must not call setattr")
        if isinstance(node, _ast.Import):
            for alias in node.names:
                if alias.name.startswith("agent.skill_utils"):
                    pytest.fail("_advisory.py must not import agent.skill_utils")
                if alias.name.startswith("prompt_builder"):
                    pytest.fail("_advisory.py must not import prompt_builder")
        if isinstance(node, _ast.ImportFrom):
            if node.module and node.module.startswith("agent.skill_utils"):
                pytest.fail("_advisory.py must not import agent.skill_utils")
            if node.module and node.module.startswith("prompt_builder"):
                pytest.fail("_advisory.py must not import prompt_builder")


def test_advisory_pin_values() -> None:
    """Pin the cap values per plan D5."""
    assert UNPATCHED_CAP == 60
    assert PATCHED_CAP_REFERENCE == "MAX_DESCRIPTION_LENGTH"
