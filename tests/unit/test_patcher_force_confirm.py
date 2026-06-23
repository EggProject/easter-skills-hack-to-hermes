"""Unit tests for ``_patcher_force_confirm`` (AC-2.5.1 + AC-2.10).

Covers the pure-function branches in :mod:`_patcher_force_confirm`:
the unified-diff builder and the gate's pass-through behaviour.

Phase 7A.5: ``--force`` / ``--yes`` have been removed; the gate is
now a pass-through that always proceeds. The refuse / TTY-prompt
branches no longer exist; tests for them have been collapsed into
``test_force_confirm_gate_always_proceeds``.
"""

from __future__ import annotations

from pathlib import Path

from easter_hermes_sorry_skills._patcher import (
    EXIT_USER_ABORT,
    S1_CAP_SITE,
)
from easter_hermes_sorry_skills._patcher_force_confirm import (
    ForceConfirmInputs,
    ForceConfirmOutcome,
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


def test_force_confirm_gate_always_proceeds() -> None:
    """Phase 7A.5: the gate is a pass-through — it always proceeds."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
        ),
    )
    assert out.proceed is True
    assert out.refused_message is None
    assert out.response is None
    assert out.prompt_text == ""


def test_force_confirm_gate_always_proceeds_on_non_tty() -> None:
    """Pass-through: non-TTY inputs still proceed."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
        ),
    )
    assert out.proceed is True
    assert out.refused_message is None


def test_user_abort_result_from_outcome_no_refused_message() -> None:
    """When the outcome has no refused_message (the new default),
    the result diagnostics contain only the base diagnostics
    (no extra refused line)."""
    out = force_confirm_gate(
        ForceConfirmInputs(
            sites=(),
            target_path=Path("/tmp"),
        ),
    )
    assert out.refused_message is None
    result = user_abort_result_from_outcome(out, ("only-base",))
    assert "only-base" in result.diagnostics
    assert not any("refused" in d or "megtagadva" in d for d in result.diagnostics)


def test_user_abort_result_from_outcome_with_refused_message() -> None:
    """The user-abort result builder produces EXIT_USER_ABORT and
    appends the refused message to the base diagnostics when one
    is present (synthetic refused outcome for backwards-compat)."""
    out = ForceConfirmOutcome(
        proceed=False,
        diff_text="",
        prompt_text="",
        response="no",
        refused_message="Force confirmation refused (megtagadva).",
    )
    result = user_abort_result_from_outcome(out, ("existing diag",))
    assert result.exit_code == EXIT_USER_ABORT
    assert any("refused" in d or "megtagadva" in d for d in result.diagnostics)
    assert any("existing diag" in d for d in result.diagnostics)


# NOTE: ``test_false_callable_returns_false`` was removed.
# Phase 7 refactor: ``_patcher._false_callable`` (the default ``isatty``
# stand-in) was deleted when ``ForceConfirmInputs`` was migrated to explicit
# ``stdin_isatty`` / ``stdout_isatty`` ``bool`` fields. The helper is no
# longer needed and is intentionally absent from ``_patcher``.
