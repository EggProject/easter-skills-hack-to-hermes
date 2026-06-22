"""--force TTY confirmation gate (AC-2.5.1 + AC-2.10).

Extracted from the orchestrator to keep module sizes under the
wemake-python-styleguide caps. The gate is invoked by ``run_patch``
ONLY when ``--force --i-accept-line-drift`` are set AND the run has
not been suppressed via ``--yes``.

Flow (per spec AC-2.5.1):

1. Print the unified diff for the planned apply.
2. Print the bilingual confirmation prompt.
3. On a TTY: ``input()`` reads the operator's response; ``"yes"`` =>
   proceed; anything else (incl. EOF / empty / "no") => EXIT_USER_ABORT.
4. On a non-TTY (CI / pipe / CliRunner): the gate proceeds silently
   (the operator could not have replied anyway); ``--yes`` is the
   explicit opt-in marker.

The gate is intentionally a pure function over the dataclass-shaped
``ForceConfirmInputs`` bundle so it can be unit-tested in isolation.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from easter_hermes_sorry_skills._patcher_consts import EXIT_USER_ABORT
from easter_hermes_sorry_skills._patcher_force_confirm_diff import build_diff_text
from easter_hermes_sorry_skills._patcher_sites import Site
from easter_hermes_sorry_skills.i18n.messages_en import (
    FORCE_CONFIRM_PROMPT,
    FORCE_CONFIRM_REFUSED,
)

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher import PatcherResult


@dataclasses.dataclass(frozen=True)
class ForceConfirmInputs:
    """Inputs for :func:`force_confirm_gate` (bundled for WPS211)."""

    sites: tuple[Site, ...]
    target_path: Path
    yes: bool
    stdin_isatty: bool
    stdout_isatty: bool
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


def _stderr_emit(message: str) -> None:
    """Default ``emit_message`` impl: write to stderr."""
    sys.stderr.write(f"{message}\n")


def force_confirm_gate(inputs: ForceConfirmInputs) -> ForceConfirmOutcome:
    """Run the --force TTY confirmation gate."""
    diff_text = build_diff_text(inputs.sites, inputs.target_path)
    prompt_text = FORCE_CONFIRM_PROMPT
    emit = inputs.emit_message or _stderr_emit
    read = inputs.read_input or input
    # ``--yes`` or non-TTY: proceed silently.
    if inputs.yes or not (inputs.stdin_isatty and inputs.stdout_isatty):
        return ForceConfirmOutcome(
            proceed=True,
            diff_text=diff_text,
            prompt_text=prompt_text,
            response=None,
            refused_message=None,
        )
    emit(diff_text)
    emit(prompt_text)
    response = read()
    if response.strip().lower() == "yes":
        return ForceConfirmOutcome(
            proceed=True,
            diff_text=diff_text,
            prompt_text=prompt_text,
            response=response,
            refused_message=None,
        )
    return ForceConfirmOutcome(
        proceed=False,
        diff_text=diff_text,
        prompt_text=prompt_text,
        response=response,
        refused_message=FORCE_CONFIRM_REFUSED,
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
