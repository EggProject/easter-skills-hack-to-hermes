"""Internal helpers for the patcher orchestrator.

Extracted from ``_patcher.py`` to keep that orchestrator module under
wemake WPS202 (≤7 module members). Contains the per-run mutable state,
the preflight + circular-import short-circuit checks, and the
empty-result builder.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_skill_creator_plugin import _patcher_imports as _imps
from hermes_skill_creator_plugin._patcher_preflight import run_preflight as _run_preflight

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult, PatchRunInputs


@dataclasses.dataclass
class _PatchBodyState:
    """Mutable per-run state passed between pipeline helpers."""

    diagnostics: list[str] = dataclasses.field(default_factory=list)
    sites_patched: list[str] = dataclasses.field(default_factory=list)
    sites_already: list[str] = dataclasses.field(default_factory=list)


def _empty_result(diagnostics: list[str], exit_code: int) -> PatcherResult:
    """Build a PatcherResult with no sites touched and the given diagnostics."""
    from hermes_skill_creator_plugin._patcher import PatcherResult

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
    preflight = _run_preflight(inputs.target, inputs.force, inputs.i_accept_line_drift)
    if preflight is None:
        return None
    return _empty_result([*state.diagnostics, preflight[1]], preflight[0])


def _check_circular_import(
    target_path: Path,
    state: _PatchBodyState,
) -> PatcherResult | None:
    skill_utils = target_path / _imps.TOOLS_SKILL_UTILS_REL
    if not _imps.file_has_circular_import(skill_utils):
        return None
    from hermes_skill_creator_plugin.i18n.messages_en import CIRCULAR_IMPORT_PREFLIGHT

    state.diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
    return _empty_result(state.diagnostics, _imps.EXIT_IO)


def _run_patch_with_inputs(inputs: PatchRunInputs) -> PatcherResult:
    """Run the patcher using a prebuilt ``PatchRunInputs`` struct."""
    from hermes_skill_creator_plugin._patcher import _run_patch_body

    return _run_patch_body(inputs)
