"""Unit tests for ``_patcher_force_confirm`` (AC-2.5.1 + AC-2.10).

Covers the pure-function branches in :mod:`_patcher_force_confirm`:
the unified-diff builder, the gate's proceed/refuse logic across TTY /
non-TTY / ``--yes`` permutations, and the user-abort result builder.
"""

from __future__ import annotations

from pathlib import Path

from hermes_skill_creator_plugin._patcher import (
    EXIT_USER_ABORT,
    S1_CAP_SITE,
)
from hermes_skill_creator_plugin._patcher_force_confirm import (
    ForceConfirmInputs,
    build_diff_text,
    force_confirm_gate,
    user_abort_result_from_outcome,
)


def test_build_diff_text_empty_sites(tmp_path: Path) -> None:
    """With no sites the diff body is empty (just the header)."""
    text = build_diff_text((), tmp_path)
    assert "tervezett diff" in text or "planned diff" in text


def test_build_diff_text_with_one_site(tmp_path: Path) -> None:
    """A single site produces a non-empty unified-diff body."""
    target_file = tmp_path / "agent" / "skill_utils.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# placeholder\n", encoding="utf-8")
    text = build_diff_text((S1_CAP_SITE,), tmp_path)
    # The header is bilingual; the diff body references the file path.
    assert "skill_utils.py" in text


def test_build_diff_text_missing_source_file(tmp_path: Path) -> None:
    """When the source file is missing, the diff still produces a body
    (treated as empty before-text)."""
    text = build_diff_text((S1_CAP_SITE,), tmp_path)
    # Header present.
    assert "tervezett diff" in text or "planned diff" in text


def test_force_confirm_gate_yes_proceeds() -> None:
    """``--yes`` short-circuits the gate to proceed without prompt."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=True,
            stdin_isatty=True,
            stdout_isatty=True,
        ),
    )
    assert out.proceed is True
    assert out.refused_message is None


def test_force_confirm_gate_non_tty_proceeds_without_yes() -> None:
    """Non-TTY without ``--yes`` proceeds silently (CI / CliRunner)."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=False,
            stdout_isatty=False,
        ),
    )
    assert out.proceed is True
    assert out.refused_message is None


def test_force_confirm_gate_tty_yes_reply_proceeds() -> None:
    """TTY prompt with ``"yes"`` reply proceeds."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=True,
            stdout_isatty=True,
            read_input=lambda: "yes",
            emit_message=lambda _msg: None,
        ),
    )
    assert out.proceed is True
    assert out.response == "yes"
    assert out.refused_message is None


def test_force_confirm_gate_tty_non_yes_reply_refuses() -> None:
    """TTY prompt with anything other than ``"yes"`` refuses (exit 5)."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=True,
            stdout_isatty=True,
            read_input=lambda: "no",
            emit_message=lambda _msg: None,
        ),
    )
    assert out.proceed is False
    assert out.refused_message is not None
    assert "refused" in out.refused_message or "megtagadva" in out.refused_message


def test_force_confirm_gate_tty_empty_reply_refuses() -> None:
    """TTY prompt with empty reply refuses."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=True,
            stdout_isatty=True,
            read_input=lambda: "",
            emit_message=lambda _msg: None,
        ),
    )
    assert out.proceed is False
    assert out.refused_message is not None


def test_user_abort_result_from_outcome_basic() -> None:
    """The user-abort result builder produces a PatcherResult with
    EXIT_USER_ABORT and the refused message in diagnostics."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=True,
            stdout_isatty=True,
            read_input=lambda: "no",
            emit_message=lambda _msg: None,
        ),
    )
    result = user_abort_result_from_outcome(out, ("existing diag",))
    assert result.exit_code == EXIT_USER_ABORT
    assert any("refused" in d or "megtagadva" in d for d in result.diagnostics)
    assert any("existing diag" in d for d in result.diagnostics)


def test_force_confirm_gate_tty_only_stdin_not_enough() -> None:
    """The gate requires BOTH stdin AND stdout to be TTYs."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=False,
            stdin_isatty=True,
            stdout_isatty=False,
        ),
    )
    assert out.proceed is True  # treated as non-interactive, proceeds silently


def test_user_abort_result_from_outcome_no_refused_message() -> None:
    """When the outcome has no refused_message, the result diagnostics
    contain only the base diagnostics (no extra refused line)."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
            yes=True,  # --yes → no refused_message
            stdin_isatty=True,
            stdout_isatty=True,
        ),
    )
    assert out.refused_message is None
    result = user_abort_result_from_outcome(out, ("only-base",))
    # Even though the gate proceeded, the builder still produces a
    # PatcherResult with the base diagnostics.
    assert "only-base" in result.diagnostics
    assert not any("refused" in d or "megtagadva" in d for d in result.diagnostics)


def test_false_callable_returns_false() -> None:
    """The ``_false_callable`` helper used as the default ``isatty``
    stand-in returns ``False``."""
    from hermes_skill_creator_plugin._patcher import _false_callable

    assert _false_callable() is False
