"""Script #1 patcher orchestrator: cap-raise + opt-in Task E sites.

Idempotent, all-or-nothing patcher for a user-owned Hermes checkout.
This module is the ORCHESTRATOR; the site table, the apply-side
primitives, the migration note renderer, and the pure-function
helpers live in sibling modules to keep each file under the 500-line
hard cap (plans/10 D1):

- :mod:`._patcher_sites` — Site dataclass, the S1.cap two-anchor
  atomic pair, the 7 Task E sites, and the shared
  ``SKILL_CREATOR_CONSULT_RULE`` constant.
- :mod:`._patcher_apply` — atomic write (``<file>.patch.tmp`` +
  ``os.replace``), the state / rejected / audit sidecars.
- :mod:`._patcher_migration` — ``MIGRATION.hermes-patch.md`` and
  ``MIGRATION.md`` rendering.
- :mod:`._patcher_helpers` — pure-function helpers (anchor locator,
  circular-import pre-flight, cross-FS detector, ISO timestamp).
- :mod:`._patcher_consts` — exit codes, state strings, drift reasons.
- :mod:`._patcher_preflight` — refusal-rule preflight.
- :mod:`._patcher_validation` — per-site drift detection.

The orchestrator's public API (``run_patch``, ``PatcherResult``, the
``Anchor`` / ``Site`` dataclasses, the site constants, exit codes,
``_atomic_write_bytes`` for tests, ``_render_cap_row`` /
``_render_task_e_row`` for tests) is re-exported from this module so
existing imports (``from hermes_skill_creator_plugin._patcher import
...``) keep working.

The patcher:

1. Refuses to run when ``--target`` resolves to ``~/.hermes/hermes-agent``
   (exit code 4, bilingual diagnostic).
2. Pre-validates every site in a single pass against the file's raw bytes
   (multi-signal targeting: 8+ char anchor + 1-based line number).
3. On a cycle-detection pre-flight against ``agent/skill_utils.py``'s
   existing imports from ``tools.skills_tool``, refuses to write and exits
   with code 4.
4. On validation failure for ANY site, writes a ``.patch.rejected`` JSON
   sidecar and exits non-zero with ZERO bytes touched on the target.
5. On success, performs the atomic-write protocol
   (``<file>.patch.tmp`` + ``os.replace``), preserves file mode bits,
   and updates ``.patch.state.json``.
6. Emits a ``.patch.audit.log`` line on every successful ``--force`` run.

See also: plans/04-script-1-patch.md, plans/05-script-1-task-e-toggle.md,
plans/08-migration-note-format.md, plans/10-toolchain-and-conventions.md,
plans/09-test-strategy.md.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hermes_skill_creator_plugin._patcher_apply import (
    REJECTED_SIDECAR,
    write_rejected,
)
from hermes_skill_creator_plugin._patcher_apply_atomic import _atomic_write_bytes
from hermes_skill_creator_plugin._patcher_apply_state import (
    STATE_SIDECAR,
    load_state,
    write_state,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_DRIFT,
    EXIT_IO,
    EXIT_OK,
    EXIT_PERMISSION,
    EXIT_USER_ABORT,
    EXIT_VALIDATION,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    file_has_circular_import,
    hermes_agent_path,
    is_hermes_agent,
    locate_anchor,
    site_already_patched,
    site_in_state,
)
from hermes_skill_creator_plugin._patcher_migration import (
    generate_migration_note,
    migration_rows_for_mode,
)
from hermes_skill_creator_plugin._patcher_migration_render import (
    _render_cap_row,
    _render_task_e_row,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    apply_sites as _apply_sites_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    ok_check_result as _ok_check_result_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    fail_with_drift as _fail_with_drift_pipeline,
)
from hermes_skill_creator_plugin._patcher_preflight import run_preflight as _run_preflight
from hermes_skill_creator_plugin._patcher_sites import (
    ALL_TASK_E_SITES,
    E1_SKILLS_GUIDANCE,
    E2_MEMORY_GUIDANCE,
    E3_BUILD_SKILLS_PROMPT,
    E4_SKILL_REVIEW_PROMPT,
    E5_COMBINED_REVIEW_PROMPT,
    E6_SKILL_MANAGE_SCHEMA_DESC,
    E7_SKILLS_DOC_SECTION,
    S1_CAP_SITE,
    SKILL_CREATOR_CONSULT_RULE,
    TOOLS_SKILL_UTILS_REL,
    Anchor,
    Site,
    sites_for_mode,
)
from hermes_skill_creator_plugin._patcher_validation import validate_sites as _validate_sites
from hermes_skill_creator_plugin.i18n.messages_en import CIRCULAR_IMPORT_PREFLIGHT

# --- result type ---------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PatcherResult:
    """Outcome of a patcher run.

    ``exit_code`` follows the matrix in plans/04 (0..5).
    ``sites_patched`` is the list of site_ids touched by THIS run.
    ``sites_already`` is the list of site_ids that were already patched
    BEFORE this run (idempotency).
    ``state`` is the updated ``.patch.state.json`` mapping
    ``{site_id: "matched" | "drifted" | "patched" | "already"}``.
    ``diagnostics`` is the list of bilingual messages emitted.
    """

    exit_code: int
    sites_patched: tuple[str, ...]
    sites_already: tuple[str, ...]
    state: dict[str, str]
    diagnostics: tuple[str, ...]
    rejected_path: Path | None = None


def _empty_result(diagnostics: list[str], exit_code: int) -> PatcherResult:
    """Build a PatcherResult with no sites touched and the given diagnostics."""
    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=tuple(diagnostics),
    )


def run_patch(
    *,
    target: Path | None,
    check: bool,
    apply: bool,
    force: bool,
    i_accept_line_drift: bool,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    yes: bool = False,
    verbose: bool = False,
    audit_log_path: Path | None = None,
    git_head: str = "",
) -> PatcherResult:
    """Run the patcher.

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible
    for translating ``exit_code`` into a ``SystemExit``. This function
    never raises SystemExit; it returns a result.
    """
    return _run_patch_with_inputs(
        PatchRunInputs(
            target=target,
            check=check,
            apply=apply,
            force=force,
            i_accept_line_drift=i_accept_line_drift,
            task_e_redirect=task_e_redirect,
            no_schema_redirect=no_schema_redirect,
            yes=yes,
            verbose=verbose,
            audit_log_path=audit_log_path,
            git_head=git_head,
        )
    )


@dataclasses.dataclass(frozen=True)
class PatchRunInputs:
    """All keyword inputs for :func:`run_patch`.

    Bundles the 11 CLI kwargs into a single struct so the public
    function signature stays keyword-only and wemake WPS211 / WPS210
    stay below threshold.
    """

    target: Path | None = None
    check: bool = False
    apply: bool = False
    force: bool = False
    i_accept_line_drift: bool = False
    task_e_redirect: bool = False
    no_schema_redirect: bool = False
    yes: bool = False
    verbose: bool = False
    audit_log_path: Path | None = None
    git_head: str = ""


def _run_patch_with_inputs(inputs: PatchRunInputs) -> PatcherResult:
    """Run the patcher using a prebuilt ``PatchRunInputs`` struct."""
    return _run_patch_body(inputs)


def _run_patch_body(inputs: PatchRunInputs) -> PatcherResult:
    """Internal: actually run the patcher pipeline."""
    diagnostics: list[str] = []
    preflight = _run_preflight(inputs.target, inputs.force, inputs.i_accept_line_drift)
    if preflight is not None:
        return _empty_result([*diagnostics, preflight[1]], preflight[0])
    assert inputs.target is not None  # narrowed by preflight
    target_path = inputs.target.resolve()
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if file_has_circular_import(skill_utils):
        diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
        return _empty_result(diagnostics, EXIT_IO)
    sites = list(
        sites_for_mode(
            task_e_redirect=inputs.task_e_redirect,
            no_schema_redirect=inputs.no_schema_redirect,
        )
    )
    state = load_state(target_path)
    sites_patched: list[str] = []
    sites_already: list[str] = []
    validation = _validate_sites(sites, target_path, state, sites_already)
    if validation.failures:
        return _fail_with_drift_pipeline(
            target_path,
            validation.failures,
            state,
            sites_already,
            diagnostics,
            inputs.git_head,
            exit_codes=(EXIT_DRIFT, EXIT_PERMISSION),
        )
    if inputs.check or not inputs.apply:
        return _ok_check_result_pipeline(
            sites,
            state,
            sites_patched,
            sites_already,
            target_path,
            diagnostics,
            exit_ok_code=EXIT_OK,
            write_state_fn=write_state,
        )
    return _apply_sites_pipeline(
        sites,
        target_path,
        state,
        sites_patched,
        sites_already,
        diagnostics,
        inputs.force,
        inputs.audit_log_path,
        exit_ok_code=EXIT_OK,
        write_state_fn=write_state,
    )


__all__ = [
    # exit codes (re-exported from _patcher_consts)
    "EXIT_OK",
    "EXIT_VALIDATION",
    "EXIT_DRIFT",
    "EXIT_PERMISSION",
    "EXIT_IO",
    "EXIT_USER_ABORT",
    # constants
    "SKILL_CREATOR_CONSULT_RULE",
    "STATE_SIDECAR",
    "REJECTED_SIDECAR",
    # site table
    "Anchor",
    "Site",
    "S1_CAP_SITE",
    "E1_SKILLS_GUIDANCE",
    "E2_MEMORY_GUIDANCE",
    "E3_BUILD_SKILLS_PROMPT",
    "E4_SKILL_REVIEW_PROMPT",
    "E5_COMBINED_REVIEW_PROMPT",
    "E6_SKILL_MANAGE_SCHEMA_DESC",
    "E7_SKILLS_DOC_SECTION",
    "ALL_TASK_E_SITES",
    # result type
    "PatcherResult",
    # public API
    "run_patch",
    "hermes_agent_path",
    "is_hermes_agent",
    "file_has_circular_import",
    "locate_anchor",
    "site_already_patched",
    "site_in_state",
    "load_state",
    "write_state",
    "generate_migration_note",
    "migration_rows_for_mode",
    "write_rejected",
    # test seam: monkeypatched in tests/unit/test_patcher.py.
    "_atomic_write_bytes",
    "_cross_filesystem",
    "_render_cap_row",
    "_render_task_e_row",
]
