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

from ._patcher_apply import AUDIT_LOG
from ._patcher_apply import REJECTED_SIDECAR
from ._patcher_apply import STATE_SIDECAR
from ._patcher_apply import _append_audit_log
from ._patcher_apply import _atomic_write_bytes
from ._patcher_apply import _diff_sha
from ._patcher_apply import load_state
from ._patcher_apply import write_rejected
from ._patcher_apply import write_state
from ._patcher_helpers import cross_filesystem as _cross_filesystem
from ._patcher_helpers import file_has_circular_import
from ._patcher_helpers import hermes_agent_path
from ._patcher_helpers import is_hermes_agent
from ._patcher_helpers import locate_anchor
from ._patcher_helpers import site_already_patched
from ._patcher_helpers import site_in_state
from ._patcher_helpers import now_iso as _now_iso
from ._patcher_migration import _render_cap_row
from ._patcher_migration import _render_task_e_row
from ._patcher_migration import generate_migration_note
from ._patcher_migration import migration_rows_for_mode
from ._patcher_sites import ALL_TASK_E_SITES
from ._patcher_sites import E1_SKILLS_GUIDANCE
from ._patcher_sites import E2_MEMORY_GUIDANCE
from ._patcher_sites import E3_BUILD_SKILLS_PROMPT
from ._patcher_sites import E4_SKILL_REVIEW_PROMPT
from ._patcher_sites import E5_COMBINED_REVIEW_PROMPT
from ._patcher_sites import E6_SKILL_MANAGE_SCHEMA_DESC
from ._patcher_sites import E7_SKILLS_DOC_SECTION
from ._patcher_sites import S1_CAP_SITE
from ._patcher_sites import SKILL_CREATOR_CONSULT_RULE
from ._patcher_sites import TOOLS_SKILL_UTILS_REL
from ._patcher_sites import Anchor
from ._patcher_sites import Site
from ._patcher_sites import sites_for_mode
from .i18n.messages_en import CIRCULAR_IMPORT_PREFLIGHT
from .i18n.messages_en import CROSS_FS_WARN
from .i18n.messages_en import FORCE_AUDIT_LOG
from .i18n.messages_en import FORCE_REQUIRES_I_ACCEPT
from .i18n.messages_en import IO_ERROR
from .i18n.messages_en import LINE_DRIFT
from .i18n.messages_en import OK_ALREADY_PATCHED
from .i18n.messages_en import OK_PATCHED
from .i18n.messages_en import PERMISSION_DENIED
from .i18n.messages_en import TARGET_IS_HERMES_AGENT
from .i18n.messages_en import TARGET_MISSING_SKILL_UTILS
from .i18n.messages_en import TARGET_REQUIRED
from .i18n.messages_en import TEXT_DRIFT
from .i18n.messages_en import VALIDATION_FAILED

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

PUBLIC_NAMES = [
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
    "AUDIT_LOG",
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
    "write_rejected",
    "generate_migration_note",
    "migration_rows_for_mode",
    # re-exported private helpers (for unit tests + cross-module use)
    "_atomic_write_bytes",
    "_cross_filesystem",
    "_now_iso",
    "_diff_sha",
    "_append_audit_log",
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
    target_path = Path(target).resolve()
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if file_has_circular_import(skill_utils):
        diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
        return _empty_result(diagnostics, EXIT_IO)
    sites = sites_for_mode(task_e_redirect=task_e_redirect, no_schema_redirect=no_schema_redirect)
    state = load_state(target_path)
    sites_patched: list[str] = []
    sites_already: list[str] = []
    validation = _validate_sites(sites, target_path, state, sites_already)
    if validation.failures:
        return _fail_with_drift(
            target_path, validation.failures, state, sites_already,
            diagnostics, git_head,
        )
    if check or not apply:
        return _ok_check_result(sites, state, sites_patched, sites_already,
                                target_path, diagnostics)
    return _apply_sites(
        sites, target_path, state, sites_patched, sites_already,
        diagnostics, force, audit_log_path,
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
    path = target_path / site.file
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


def _fail_with_drift(
    target_path: Path,
    failures: list[dict[str, Any]],
    state: dict[str, str],
    sites_already: list[str],
    diagnostics: list[str],
    git_head: str,
) -> PatcherResult:
    """Build the EXIT_DRIFT result, write rejected sidecar, append diagnostics."""
    rejected_path = write_rejected(
        target_path,
        failures=failures,
        remediation_en="Re-run with --force --i-accept-line-drift "
        "after reviewing the diff.",
        remediation_hu="Futtassa újra --force --i-accept-line-drift "
        "kapcsolóval a diff átnézése után.",
        git_head=git_head,
    )
    for failure in failures:
        _append_drift_diagnostic(failure, diagnostics)
    return PatcherResult(
        exit_code=EXIT_DRIFT,
        sites_patched=(),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
        rejected_path=rejected_path,
    )


def _append_drift_diagnostic(
    failure: dict[str, Any],
    diagnostics: list[str],
) -> None:
    """Append the right i18n diagnostic for one failure entry."""
    if failure.get("reason") == _REASON_LINE_DRIFT:
        diagnostics.append(LINE_DRIFT.format(site_id=failure["site_id"], line=failure["anchor_line"]))
    else:
        diagnostics.append(
            TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            )
        )
    diagnostics.append(VALIDATION_FAILED.format(site_id=failure["site_id"]))


# --- check-mode result ---------------------------------------------------


def _ok_check_result(
    sites: list[Site],
    state: dict[str, str],
    sites_patched: list[str],
    sites_already: list[str],
    target_path: Path,
    diagnostics: list[str],
) -> PatcherResult:
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    for site in sites:
        if site.site_id in sites_already:
            diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
        else:
            diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    write_state(target_path, state)
    return PatcherResult(
        exit_code=EXIT_OK,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


# --- apply-mode loop ------------------------------------------------------


def _apply_sites(
    sites: list[Site],
    target_path: Path,
    state: dict[str, str],
    sites_patched: list[str],
    sites_already: list[str],
    diagnostics: list[str],
    force: bool,
    audit_log_path: Path | None,
) -> PatcherResult:
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    audit_path = audit_log_path or (target_path / AUDIT_LOG)
    timestamp = _now_iso()
    apply_sites = sorted(sites, key=lambda s: s.line_for_state, reverse=True)
    for site in apply_sites:
        if site.site_id in sites_already:
            diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        outcome = _apply_one_site(site, target_path, force, audit_path, timestamp)
        if outcome is not None:
            state[site.site_id] = _STATE_DRIFTED
            write_state(target_path, state)
            return outcome
        sites_patched.append(site.site_id)
        state[site.site_id] = _STATE_PATCHED
        diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    if _cross_filesystem(target_path):
        diagnostics.append(CROSS_FS_WARN)
    write_state(target_path, state)
    return PatcherResult(
        exit_code=EXIT_OK,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


def _apply_one_site(
    site: Site,
    target_path: Path,
    force: bool,
    audit_path: Path,
    timestamp: str,
) -> PatcherResult | None:
    """Apply one site. Return ``None`` on success, or a PatcherResult on IO error."""
    path = target_path / site.file
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = _mutate_lines_for_site(site, text)
    after_bytes = "".join(new_lines).encode("utf-8")
    try:
        _atomic_write_bytes(path, after_bytes)
    except (PermissionError, OSError) as exc:
        if isinstance(exc, PermissionError):
            diag = PERMISSION_DENIED.format(path=str(path))
        else:
            diag = IO_ERROR.format(path=str(path), error=str(exc))
        return PatcherResult(
            exit_code=EXIT_PERMISSION,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=(diag,),
        )
    if force:
        _emit_audit_log(audit_path, timestamp, site.site_id, before, after_bytes, target_path)
    return None


def _mutate_lines_for_site(site: Site, text: str) -> list[str]:
    """Return the post-mutation line list for ``site`` (cap replace or append)."""
    lines = text.splitlines(keepends=True)
    idx = site.primary_anchor().line - 1
    if site.kind == "cap":
        new_pair_lines = site.insertion.splitlines(keepends=True)
        return lines[:idx] + new_pair_lines + lines[idx + 2:]
    lines.insert(idx + 1, site.insertion)
    return lines


def _emit_audit_log(
    audit_path: Path,
    timestamp: str,
    site_id: str,
    before: bytes,
    after_bytes: bytes,
    target_path: Path,
) -> None:
    """Append one FORCE_AUDIT_LOG line for a successful ``--force`` site."""
    diff_sha = _diff_sha(before, after_bytes)
    audit_line = FORCE_AUDIT_LOG.format(
        timestamp=timestamp,
        site_id=site_id,
        diff_sha=diff_sha,
        target=str(target_path),
    )
    _append_audit_log(audit_path, audit_line)
