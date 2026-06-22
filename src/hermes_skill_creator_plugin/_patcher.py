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
import sys
from pathlib import Path

from hermes_skill_creator_plugin import _patcher_imports as _imps
from hermes_skill_creator_plugin import _patcher_internals as _patcher_internals
from hermes_skill_creator_plugin import _patcher_sites as _sites
from hermes_skill_creator_plugin._patcher_pipeline import (
    ApplySitesInputs,
    OkCheckInputs,
    apply_sites,
    ok_check_result,
)
from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    _FailDriftInputs,
    fail_with_drift,
)
from hermes_skill_creator_plugin._patcher_validation import validate_sites

# Local re-bindings.
_apply_sites_pipeline = apply_sites
_ok_check_result_pipeline = ok_check_result
_fail_with_drift_pipeline = fail_with_drift
_validate_sites = validate_sites

# Local bindings matching the previous top-level import names. The
# actual imports live in :mod:`._patcher_imports` to keep this
# orchestrator under wemake WPS201 (<=12 imports per module).
REJECTED_SIDECAR = _imps.REJECTED_SIDECAR
write_rejected = _imps.write_rejected
_atomic_write_bytes = _imps._atomic_write_bytes
STATE_SIDECAR = _imps.STATE_SIDECAR
STATE_DRIFTED = _imps.STATE_DRIFTED
load_state = _imps.load_state
write_state = _imps.write_state
EXIT_DRIFT = _imps.EXIT_DRIFT
EXIT_IO = _imps.EXIT_IO
EXIT_OK = _imps.EXIT_OK
EXIT_PERMISSION = _imps.EXIT_PERMISSION
EXIT_USER_ABORT = _imps.EXIT_USER_ABORT
EXIT_VALIDATION = _imps.EXIT_VALIDATION
_cross_filesystem = _imps._cross_filesystem
file_has_circular_import = _imps.file_has_circular_import
hermes_agent_path = _imps.hermes_agent_path
is_hermes_agent = _imps.is_hermes_agent
locate_anchor = _imps.locate_anchor
site_already_patched = _imps.site_already_patched
site_in_state = _imps.site_in_state
generate_migration_note = _imps.generate_migration_note
migration_rows_for_mode = _imps.migration_rows_for_mode
_render_cap_row = _imps._render_cap_row
_render_task_e_row = _imps._render_task_e_row
ALL_TASK_E_SITES = _imps.ALL_TASK_E_SITES
E1_SKILLS_GUIDANCE = _imps.E1_SKILLS_GUIDANCE
E2_MEMORY_GUIDANCE = _imps.E2_MEMORY_GUIDANCE
E3_BUILD_SKILLS_PROMPT = _imps.E3_BUILD_SKILLS_PROMPT
E4_SKILL_REVIEW_PROMPT = _imps.E4_SKILL_REVIEW_PROMPT
E5_COMBINED_REVIEW_PROMPT = _imps.E5_COMBINED_REVIEW_PROMPT
E6_SKILL_MANAGE_SCHEMA_DESC = _imps.E6_SKILL_MANAGE_SCHEMA_DESC
E7_SKILLS_DOC_SECTION = _imps.E7_SKILLS_DOC_SECTION
S1_CAP_SITE = _imps.S1_CAP_SITE
SKILL_CREATOR_CONSULT_RULE = _imps.SKILL_CREATOR_CONSULT_RULE
TOOLS_SKILL_UTILS_REL = _imps.TOOLS_SKILL_UTILS_REL
sites_for_mode = _imps.sites_for_mode
Anchor = _sites.Anchor
Site = _sites.Site

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


def run_patch(inputs: PatchRunInputs) -> PatcherResult:
    """Run the patcher.

    Accepts a single :class:`PatchRunInputs` struct (WPS211-bundled)
    whose fields are the operational parameters plus optional
    side-effects (yes/verbose/audit_log_path/git_head) that carry safe
    defaults (False/False/None/'').

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible
    for translating ``exit_code`` into a ``SystemExit``. This function
    never raises SystemExit; it returns a result.
    """
    return _run_patch_with_inputs(inputs)


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


# --- internal pipeline state (re-exported for tests) --------------------

_PatchBodyState = _patcher_internals._PatchBodyState
_empty_result = _patcher_internals._empty_result
_check_preflight = _patcher_internals._check_preflight
_check_circular_import = _patcher_internals._check_circular_import
_run_patch_with_inputs = _patcher_internals._run_patch_with_inputs


def _run_patch_body(inputs: PatchRunInputs) -> PatcherResult:
    """Internal: actually run the patcher pipeline."""
    state = _PatchBodyState()
    early = _check_preflight(inputs, state)
    if early is not None:
        return early
    assert inputs.target is not None  # narrowed by preflight
    target_path = inputs.target.resolve()
    circular = _check_circular_import(target_path, state)
    if circular is not None:
        return circular
    return _drive_pipeline(inputs, target_path, state)


def _select_sites_for_run(
    all_sites: list[_sites.Site],
    persisted: dict[str, str],
    *,
    force: bool,
) -> list[_sites.Site]:
    """Return the sites that should be APPLIED for this invocation.

    AC-2.5: ``--force`` retries ONLY sites with ``LINE_DRIFT`` diagnostic.
    Already-matched / already-patched sites are NOT re-applied. The
    LINE_DRIFT sites are determined by the persisted state
    (``.patch.state.json``); a fresh line-drift detection in the current
    validation pass is folded in via :func:`_drive_pipeline`.

    Non-``--force`` runs apply every site.
    """
    if not force:
        return all_sites
    return [site for site in all_sites if persisted.get(site.site_id) == STATE_DRIFTED]


def _false_callable() -> bool:
    """Stand-in ``isatty`` for streams that lack the attribute."""
    return False


def _drive_pipeline(
    inputs: PatchRunInputs,
    target_path: Path,
    state: _PatchBodyState,
) -> PatcherResult:
    all_sites = list(
        sites_for_mode(
            task_e_redirect=inputs.task_e_redirect,
            no_schema_redirect=inputs.no_schema_redirect,
        )
    )
    persisted = load_state(target_path)
    # Validation always runs on every site so a fresh LINE_DRIFT is
    # detected and either EXIT_DRIFT (default) or absorbed into the
    # apply-time filter (when ``--force``). AC-2.5: ``--force`` retries
    # ONLY drifted sites; already-matched sites are skipped at apply
    # time (see :func:`_select_sites_for_run`).
    validation = _validate_sites(all_sites, target_path, persisted, state.sites_already)
    # AC-2.4: any drift on a default run EXITS 2 (no auto-bypass). AC-2.5:
    # ``--force`` retries ONLY drifted sites at apply time, but a fresh
    # LINE_DRIFT or TEXT_DRIFT still EXITS 2 because ``--force`` is a
    # retry, not a bypass — the operator must manually fix the line and
    # then re-run with ``--force``.
    if validation.failures:
        return _fail_with_drift_pipeline(
            _FailDriftInputs(
                target_path=target_path,
                failures=validation.failures,
                state=persisted,
                sites_already=list(state.sites_already),
                diagnostics=list(state.diagnostics),
                git_head=inputs.git_head,
                exit_codes=(EXIT_DRIFT, EXIT_PERMISSION),
            ),
        )
    # AC-2.5: when ``--force`` is set, only LINE_DRIFT sites (per
    # persisted state) are retried; already-matched / already-patched
    # sites are NOT re-applied.
    sites = _select_sites_for_run(all_sites, persisted, force=inputs.force)
    # AC-2.5.1: --force --i-accept-line-drift triggers a TTY pause +
    # diff-print + bilingual confirmation gate. ``--yes`` suppresses
    # the gate (CI / non-TTY runs). EXIT_USER_ABORT (5) on refusal.
    if inputs.force and inputs.i_accept_line_drift and not inputs.check:
        from hermes_skill_creator_plugin._patcher_force_confirm import (
            ForceConfirmInputs,
            force_confirm_gate,
            user_abort_result_from_outcome,
        )

        outcome = force_confirm_gate(
            ForceConfirmInputs(
                sites=tuple(sites),
                target_path=target_path,
                yes=inputs.yes,
                stdin_isatty=bool(getattr(sys.stdin, "isatty", _false_callable)()),
                stdout_isatty=bool(getattr(sys.stdout, "isatty", _false_callable)()),
            ),
        )
        if not outcome.proceed:
            return user_abort_result_from_outcome(outcome, tuple(state.diagnostics))
    if inputs.check or not inputs.apply:
        return _ok_check_result_pipeline(
            OkCheckInputs(
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
        ApplySitesInputs(
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
