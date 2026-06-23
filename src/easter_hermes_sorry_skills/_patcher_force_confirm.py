"""--force TTY confirmation gate (AC-2.5.1 + AC-2.10).

Phase 7A.5: ``--force`` / ``--yes`` have been removed. The gate
is now a pass-through that always proceeds (no interactive prompt,
no auto-confirm). It is retained as a function and a
``ForceConfirmInputs`` bundle for call-site stability and
backwards-compatible unit-test surface.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from easter_hermes_sorry_skills._patcher_consts import EXIT_USER_ABORT
from easter_hermes_sorry_skills._patcher_force_confirm_diff import build_diff_text
from easter_hermes_sorry_skills._patcher_sites import Site

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher import PatcherResult


@dataclasses.dataclass(frozen=True)
class ForceConfirmInputs:
    """Inputs for :func:`force_confirm_gate` (bundled for WPS211).

    The ``--yes`` / ``--force`` CLI flags have been removed
    (Phase 7A.5); the gate is now a pass-through. Legacy fields are
    retained for unit-test compatibility only.
    """

    sites: tuple[Site, ...]
    target_path: Path
    yes: bool = False
    stdin_isatty: bool = False
    stdout_isatty: bool = False
    read_input: Callable[[], str] | None = None
    emit_message: Callable[[str], None] | None = None


@dataclasses.dataclass(frozen=True)
class ForceConfirmOutcome:
    """Outcome of :func:`force_confirm_gate`."""

    proceed: bool
    diff_text: str
    prompt_text: str
    response: str | None
    refused_message: str | None


def force_confirm_gate(inputs: ForceConfirmInputs) -> ForceConfirmOutcome:
    """Run the --force TTY confirmation gate.

    Phase 7A.5: ``--force`` / ``--yes`` have been removed; there is
    no auto-confirm path and no interactive prompt. The gate is a
    pass-through that always proceeds. Retained as a function for
    call-site stability and test compatibility.
    """
    diff_text = build_diff_text(inputs.sites, inputs.target_path)
    return ForceConfirmOutcome(
        proceed=True,
        diff_text=diff_text,
        prompt_text="",
        response=None,
        refused_message=None,
    )


def user_abort_result_from_outcome(
    outcome: ForceConfirmOutcome,
    base_diagnostics: tuple[str, ...] = (),
) -> PatcherResult:
    """Build a PatcherResult for a refused --force confirmation."""
    from easter_hermes_sorry_skills._patcher import PatcherResult

    diagnostics = list(base_diagnostics)
    if outcome.refused_message is not None:
        diagnostics.append(outcome.refused_message)
    return PatcherResult(
        exit_code=EXIT_USER_ABORT,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=tuple(diagnostics),
        rejected_path=None,
    )
