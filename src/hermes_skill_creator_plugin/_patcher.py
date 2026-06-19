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
from typing import Any

from hermes_skill_creator_plugin._patcher_apply import (
    REJECTED_SIDECAR,
    STATE_SIDECAR,
    _atomic_write_bytes,
    load_state,
    write_rejected,
    write_state,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import file_has_circular_import
from hermes_skill_creator_plugin._patcher_helpers import hermes_agent_path
from hermes_skill_creator_plugin._patcher_helpers import is_hermes_agent
from hermes_skill_creator_plugin._patcher_helpers import locate_anchor
from hermes_skill_creator_plugin._patcher_helpers import site_already_patched
from hermes_skill_creator_plugin._patcher_helpers import site_in_state
from hermes_skill_creator_plugin._patcher_migration import (
    _render_cap_row,
    _render_task_e_row,
    generate_migration_note,
    migration_rows_for_mode,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    apply_sites as _apply_sites_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    fail_with_drift as _fail_with_drift_pipeline,
)
from hermes_skill_creator_plugin._patcher_pipeline import (
    ok_check_result as _ok_check_result_pipeline,
)
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
from hermes_skill_creator_plugin.i18n.messages_en import (
    CIRCULAR_IMPORT_PREFLIGHT,
    FORCE_REQUIRES_I_ACCEPT,
    TARGET_IS_HERMES_AGENT,
    TARGET_MISSING_SKILL_UTILS,
    TARGET_REQUIRED,
)

# --- exit codes (per plans/04-script-1-patch.md §Exit code matrix) --------
EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_DRIFT = 2
EXIT_PERMISSION = 3
EXIT_IO = 4
EXIT_USER_ABORT = 5

# State strings used in the ``state`` dict (also referenced in tests).
_STATE_MATCHED = "matched"
_STATE_PATCHED = "patched"
_STATE_DRIFTED = "drifted"

# Failure-reason strings emitted to the rejected sidecar.
_REASON_LINE_DRIFT = "LINE_DRIFT"
_REASON_TEXT_DRIFT = "TEXT_DRIFT"

# Sentinel placeholder text for missing-file / out-of-range line drift.
_MISSING_FILE = "<file missing>"
_NOT_FOUND = "<not found>"
_OUT_OF_RANGE = "<out of range>"

__all__ = [
    # exit codes
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


# --- the main entry point -------------------------------------------------


def run_patch(*, target: Path | None, check: bool, apply: bool,
              force: bool, i_accept_line_drift: bool,
              task_e_redirect: bool, no_schema_redirect: bool,
              yes: bool = False, verbose: bool = False,
              audit_log_path: Path | None = None,
              git_head: str = "") -> PatcherResult:
    """Run the patcher.

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible
    for translating ``exit_code`` into a ``SystemExit``. This function
    never raises SystemExit; it returns a result.
    """
    diagnostics: list[str] = []
    preflight = _run_preflight(target, force, i_accept_line_drift)
    if preflight is not None:
        return _empty_result([*diagnostics, preflight[1]], preflight[0])
    assert target is not None  # narrowed by preflight
    target_path = target.resolve()
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if file_has_circular_import(skill_utils):
        diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
        return _empty_result(diagnostics, EXIT_IO)
    sites = list(sites_for_mode(
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
    ))
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
            git_head,
            exit_drift_code=EXIT_DRIFT,
            exit_permission_code=EXIT_PERMISSION,
        )
    if check or not apply:
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
        force,
        audit_log_path,
        exit_ok_code=EXIT_OK,
        write_state_fn=write_state,
    )


# --- preflight ------------------------------------------------------------


def _run_preflight(
    target: Path | None,
    force: bool,
    i_accept_line_drift: bool,
) -> tuple[int, str] | None:
    """Return ``(exit_code, diagnostic)`` on failure, ``None`` to continue.

    Encodes the refusal rules: no target, target is the hermes-agent
    checkout, missing skill_utils, force without --i-accept-line-drift.
    """
    if target is None:
        return (EXIT_IO, TARGET_REQUIRED)
    target_path = Path(target).resolve()
    if is_hermes_agent(target_path):
        msg = TARGET_IS_HERMES_AGENT.format(resolved=str(target_path))
        return (EXIT_IO, msg)
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not skill_utils.exists():
        msg = TARGET_MISSING_SKILL_UTILS.format(path=str(skill_utils))
        return (EXIT_IO, msg)
    if force and not i_accept_line_drift:
        return (EXIT_USER_ABORT, FORCE_REQUIRES_I_ACCEPT)
    return None


# --- validation -----------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _ValidationResult:
    """Outcome of pre-validation across all sites."""

    failures: list[dict[str, Any]]
    matched_count: int


def _validate_sites(
    sites: list[Site],
    target_path: Path,
    state: dict[str, str],
    sites_already: list[str],
) -> _ValidationResult:
    """Pre-validate every site and update ``state`` / ``sites_already``."""
    failures: list[dict[str, Any]] = []
    for site in sites:
        outcome = _validate_one_site(site, target_path, state, sites_already)
        if outcome is not None:
            failures.append(outcome)
    return _ValidationResult(failures=failures, matched_count=0)


def _validate_one_site(
    site: Site,
    target_path: Path,
    state: dict[str, str],
    sites_already: list[str],
) -> dict[str, Any] | None:
    """Validate one site; return a failure dict or ``None``."""
    path = target_path / site.file_path
    if not path.exists():
        return _missing_file_failure(site)
    text = path.read_text(encoding="utf-8", errors="replace")
    if site_already_patched(text, site):
        sites_already.append(site.site_id)
        state[site.site_id] = _STATE_PATCHED
        return None
    failure = _validate_site_anchors(site, text)
    if failure is not None:
        return failure
    state[site.site_id] = _STATE_MATCHED
    return None


def _missing_file_failure(site: Site) -> dict[str, Any]:
    """Build a TEXT_DRIFT failure for a site whose file is missing."""
    return {
        "site_id": site.site_id,
        "reason": _REASON_TEXT_DRIFT,
        "expected": site.primary_anchor().text,
        "actual_at_line_<missing>": _MISSING_FILE,
    }


def _validate_site_anchors(
    site: Site,
    text: str,
) -> dict[str, Any] | None:
    """Return a drift failure dict for ``site`` if any anchor drifted."""
    for anchor in site.anchors:
        line_no = locate_anchor(text, anchor)
        if line_no == 0:
            return _text_drift_failure(site, anchor)
        if line_no != anchor.line:
            return _line_drift_failure(site, anchor, line_no, text)
    return None


def _text_drift_failure(site: Site, anchor: Anchor) -> dict[str, Any]:
    """Build a TEXT_DRIFT failure (anchor not found)."""
    return {
        "site_id": site.site_id,
        "anchor_line": anchor.line,
        "reason": _REASON_TEXT_DRIFT,
        "expected": anchor.text,
        "actual_at_line_<missing>": _NOT_FOUND,
    }


def _line_drift_failure(
    site: Site,
    anchor: Anchor,
    line_no: int,
    text: str,
) -> dict[str, Any]:
    """Build a LINE_DRIFT failure (anchor at wrong line)."""
    lines = text.splitlines()
    actual = lines[line_no - 1] if line_no <= len(lines) else _OUT_OF_RANGE
    return {
        "site_id": site.site_id,
        "anchor_line": anchor.line,
        "found_at_line": line_no,
        "reason": _REASON_LINE_DRIFT,
        "expected": anchor.text,
        "actual_at_line_<n>": actual,
    }
