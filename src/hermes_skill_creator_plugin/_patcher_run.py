"""Inner run helpers for the patcher orchestrator.

Split from ``_patcher`` (WPS202 module surface budget). The
``_drive_pipeline`` driver and the ``_check_circular_import`` pre-flight
hook live here so the top-level orchestrator stays under the module
surface cap.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult

from hermes_skill_creator_plugin._patcher_apply_state import (
    load_state,
    write_state,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_DRIFT,
    EXIT_IO,
    EXIT_OK,
    EXIT_PERMISSION,
)
from hermes_skill_creator_plugin._patcher_helpers import file_has_circular_import
from hermes_skill_creator_plugin._patcher_inputs import PatchRunInputs
from hermes_skill_creator_plugin._patcher_pipeline import (
    apply_sites as _apply_sites_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    ok_check_result as _ok_check_result_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline_args import (
    _ApplySitesArgs,
    _OkCheckArgs,
)
from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    _FailDriftInputs,
)
from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    fail_with_drift as _fail_with_drift_pipeline,
)
from hermes_skill_creator_plugin._patcher_sites import (
    TOOLS_SKILL_UTILS_REL,
    sites_for_mode,
)
from hermes_skill_creator_plugin._patcher_validation import (
    validate_sites as _validate_sites,
)


@dataclasses.dataclass
class _PatchBodyState:
    """Mutable per-run state passed between pipeline helpers."""

    diagnostics: list[str] = dataclasses.field(default_factory=list)
    sites_patched: list[str] = dataclasses.field(default_factory=list)
    sites_already: list[str] = dataclasses.field(default_factory=list)


def _drive_pipeline(
    inputs: PatchRunInputs,
    target_path: Path,
    state: _PatchBodyState,
) -> PatcherResult:
    sites = list(
        sites_for_mode(
            task_e_redirect=inputs.task_e_redirect,
            no_schema_redirect=inputs.no_schema_redirect,
        )
    )
    persisted = load_state(target_path)
    validation = _validate_sites(sites, target_path, persisted, state.sites_already)
    if validation.failures:
        return _fail_with_drift_pipeline(
            _FailDriftInputs(
                target_path=target_path,
                failures=validation.failures,
                state=persisted,
                sites_already=state.sites_already,
                diagnostics=state.diagnostics,
                git_head=inputs.git_head,
                exit_codes=(EXIT_DRIFT, EXIT_PERMISSION),
            ),
        )
    if inputs.check or not inputs.apply:
        return _ok_check_result_pipeline(
            _OkCheckArgs(
                sites=sites,
                state=persisted,
                sites_patched=state.sites_patched,
                sites_already=state.sites_already,
                target_path=target_path,
                diagnostics=state.diagnostics,
                exit_ok_code=EXIT_OK,
                write_state_fn=write_state,
            ),
        )
    return _apply_sites_pipeline(
        _ApplySitesArgs(
            sites=sites,
            target_path=target_path,
            state=persisted,
            sites_patched=state.sites_patched,
            sites_already=state.sites_already,
            diagnostics=state.diagnostics,
            force=inputs.force,
            audit_log_path=inputs.audit_log_path,
            exit_ok_code=EXIT_OK,
            write_state_fn=write_state,
        ),
    )


def _check_circular_import(
    target_path: Path,
    state: _PatchBodyState,
) -> PatcherResult | None:
    from hermes_skill_creator_plugin._patcher import _empty_result
    from hermes_skill_creator_plugin.i18n.messages_en import (
        CIRCULAR_IMPORT_PREFLIGHT,
    )

    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not file_has_circular_import(skill_utils):
        return None
    state.diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
    return _empty_result(state.diagnostics, EXIT_IO)
