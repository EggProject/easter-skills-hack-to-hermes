"""Internal helpers for the patcher orchestrator.

Extracted from ``_patcher.py`` to keep that orchestrator module under
wemake WPS202 (≤7 module members). Contains the per-run mutable state,
the preflight + circular-import short-circuit checks, and the
empty-result builder.

AC-2.11 fallback: when :func:`_check_circular_import` detects a cycle,
the patcher does NOT exit; instead it returns a ``_CircularImportInfo``
signal so the pipeline can swap S1.cap for S1.cap_fallback and proceed
with the local ``_MAX_DESCRIPTION_LENGTH = 1024`` constant.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from easter_hermes_sorry_skills import _patcher_imports as _imps
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult
from easter_hermes_sorry_skills._patcher_preflight import run_preflight as _run_preflight

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher import PatchRunInputs


@dataclasses.dataclass
class _PatchBodyState:
    """Mutable per-run state passed between pipeline helpers."""

    diagnostics: list[str] = dataclasses.field(default_factory=list)
    sites_patched: list[str] = dataclasses.field(default_factory=list)
    sites_already: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class _CircularImportInfo:
    """AC-2.11: signal that a cycle was detected so the caller can swap sites."""

    detected: bool


_NO_CIRCULAR_IMPORT = _CircularImportInfo(detected=False)


def _empty_result(diagnostics: list[str], exit_code: int) -> PatcherResult:
    """Build a PatcherResult with no sites touched and the given diagnostics."""
    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=tuple(diagnostics),
    )


def _check_preflight(
    inputs: PatchRunInputs,
    state: _PatchBodyState,
) -> PatcherResult | None:
    # ``--force`` and ``--i-accept-line-drift`` were removed from
    # ``PatchRunInputs`` (Phase 7A.5). Preflight rule 4 ("force without
    # i_accept_line_drift -> EXIT_USER_ABORT") was dropped along with
    # those flags; ``run_preflight`` now accepts only ``target`` plus
    # the ``dry_run`` keyword (used to soften the hermes-agent refusal
    # under audit-only runs).
    preflight = _run_preflight(inputs.target, dry_run=inputs.dry_run)
    if preflight is None:
        return None
    if preflight.severity == "warning":
        # Soft safety: append the bilingual WARNING diagnostic and let
        # the pipeline continue. ``EXIT_OK`` here means the run
        # succeeded as a dry-run audit; the actual exit code for an
        # apply run is determined downstream by ``_drive_pipeline``.
        state.diagnostics.append(preflight.diagnostic)
        return None
    return _empty_result([*state.diagnostics, preflight.diagnostic], preflight.exit_code)


def _check_circular_import(
    target_path: Path,
    state: _PatchBodyState,
) -> _CircularImportInfo:
    """AC-2.11: return ``_CircularImportInfo(detected=True)`` when the
    cycle pre-flight fires. The orchestrator swaps S1.cap for
    S1.cap_fallback (which uses a local ``_MAX_DESCRIPTION_LENGTH = 1024``)
    instead of aborting the run.
    """
    skill_utils = target_path / _imps.TOOLS_SKILL_UTILS_REL
    if not _imps.file_has_circular_import(skill_utils):
        return _NO_CIRCULAR_IMPORT
    from easter_hermes_sorry_skills.i18n.messages_en import CIRCULAR_IMPORT_PREFLIGHT

    state.diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
    return _CircularImportInfo(detected=True)


def _run_patch_with_inputs(inputs: PatchRunInputs) -> PatcherResult:
    """Run the patcher using a prebuilt ``PatchRunInputs`` struct."""
    from easter_hermes_sorry_skills._patcher import _run_patch_body

    return _run_patch_body(inputs)
