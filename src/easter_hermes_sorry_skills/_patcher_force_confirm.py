"""--force TTY confirmation gate (AC-2.5.1 + AC-2.10).

.. deprecated::
    DEPRECATED for production use. The ``--force`` / ``--yes`` CLI
    flags have been removed (Phase 7 refactor). This module is
    retained ONLY for the backwards-compatible unit-test surface:
    no production code path imports or invokes
    :func:`force_confirm_gate` anymore (the canonical
    :func:`easter_hermes_sorry_skills._patcher._drive_pipeline`
    no longer calls it). The gate is now an unconditional
    pass-through that always proceeds (no interactive prompt,
    no auto-confirm). Do not add new callers; if you need a
    pre-apply confirmation in production, build it at the call
    site, not by reviving this module.
"""

from __future__ import annotations

import dataclasses
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
    (Phase 7A.5); the gate is now a pass-through.
    """

    sites: tuple[Site, ...]
    target_path: Path


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

    .. deprecated::
        DEPRECATED for production use. The ``--force`` / ``--yes``
        CLI flags have been removed (Phase 7 refactor); there is no
        auto-confirm path and no interactive prompt. The function is
        a pass-through that always proceeds and is invoked ONLY by
        the backwards-compatible unit-test surface
        (``tests/unit/test_patcher_force_confirm.py``). The canonical
        production pipeline
        (:func:`easter_hermes_sorry_skills._patcher._drive_pipeline`)
        no longer imports or calls this function. Do not introduce
        new production callers.
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
