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

from ._patcher_apply import (
    AUDIT_LOG,
    REJECTED_SIDECAR,
    STATE_SIDECAR,
    _append_audit_log,
    _atomic_write_bytes,
    _diff_sha,
    load_state,
    write_rejected,
    write_state,
)
from ._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from ._patcher_helpers import (
    file_has_circular_import,
    hermes_agent_path,
    is_hermes_agent,
    locate_anchor,
    site_already_patched,
    site_in_state,
)
from ._patcher_helpers import (
    now_iso as _now_iso,
)
from ._patcher_migration import (
    _render_cap_row,
    _render_task_e_row,
    generate_migration_note,
    migration_rows_for_mode,
)
from ._patcher_sites import (
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
from .i18n.messages_en import (
    CIRCULAR_IMPORT_PREFLIGHT,
    CROSS_FS_WARN,
    FORCE_AUDIT_LOG,
    FORCE_REQUIRES_I_ACCEPT,
    IO_ERROR,
    LINE_DRIFT,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
    PERMISSION_DENIED,
    TARGET_IS_HERMES_AGENT,
    TARGET_MISSING_SKILL_UTILS,
    TARGET_REQUIRED,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)

# --- exit codes (per plans/04-script-1-patch.md §Exit code matrix) --------
EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_DRIFT = 2
EXIT_PERMISSION = 3
EXIT_IO = 4
EXIT_USER_ABORT = 5

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


# --- the main entry point -------------------------------------------------


def run_patch(*,
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

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible for
    translating ``exit_code`` into a ``SystemExit``. This function never
    raises SystemExit; it returns a result.
    """
    diagnostics: list[str] = []

    if target is None:
        diagnostics.append(TARGET_REQUIRED)
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    target_path = Path(target).resolve()
    if is_hermes_agent(target_path):
        diagnostics.append(TARGET_IS_HERMES_AGENT.format(resolved=str(target_path)))
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not skill_utils.exists():
        diagnostics.append(TARGET_MISSING_SKILL_UTILS.format(path=str(skill_utils)))
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    if force and not i_accept_line_drift:
        diagnostics.append(FORCE_REQUIRES_I_ACCEPT)
        return PatcherResult(
            exit_code=EXIT_USER_ABORT,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    if file_has_circular_import(skill_utils):
        diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    sites = sites_for_mode(task_e_redirect=task_e_redirect, no_schema_redirect=no_schema_redirect)
    state = load_state(target_path)
    sites_patched: list[str] = []
    sites_already: list[str] = []

    # --- pre-validate every site in a single pass -----------------------
    failures: list[dict[str, Any]] = []
    for site in sites:
        path = target_path / site.file
        if not path.exists():
            failures.append(
                {
                    "site_id": site.site_id,
                    "reason": "TEXT_DRIFT",
                    "expected": site.primary_anchor().text,
                    "actual_at_line_<missing>": "<file missing>",
                }
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if site_already_patched(text, site):
            sites_already.append(site.site_id)
            state[site.site_id] = "patched"
            continue
        for anchor in site.anchors:
            line_no = locate_anchor(text, anchor)
            if line_no == 0:
                failures.append(
                    {
                        "site_id": site.site_id,
                        "anchor_line": anchor.line,
                        "reason": "TEXT_DRIFT",
                        "expected": anchor.text,
                        "actual_at_line_<missing>": "<not found>",
                    }
                )
                break
            if line_no != anchor.line:
                failures.append(
                    {
                        "site_id": site.site_id,
                        "anchor_line": anchor.line,
                        "found_at_line": line_no,
                        "reason": "LINE_DRIFT",
                        "expected": anchor.text,
                        "actual_at_line_<n>": (
                            text.splitlines()[line_no - 1] if line_no <= len(text.splitlines()) else "<out of range>"
                        ),
                    }
                )
                break
        else:
            state[site.site_id] = "matched"

    if failures:
        rejected_path = write_rejected(
            target_path,
            failures=failures,
            remediation_en=("Re-run with --force --i-accept-line-drift after reviewing the diff."),
            remediation_hu=("Futtassa újra --force --i-accept-line-drift kapcsolóval a diff " "átnézése után."),
            git_head=git_head,
        )
        for f in failures:
            if f.get("reason") == "LINE_DRIFT":
                diagnostics.append(LINE_DRIFT.format(site_id=f["site_id"], line=f["anchor_line"]))
            else:
                diagnostics.append(
                    TEXT_DRIFT.format(
                        site_id=f["site_id"],
                        expected=f.get("expected", ""),
                        actual=f.get("actual_at_line_<missing>", ""),
                    )
                )
            diagnostics.append(VALIDATION_FAILED.format(site_id=f["site_id"]))
        return PatcherResult(
            exit_code=EXIT_DRIFT,
            sites_patched=(),
            sites_already=tuple(sites_already),
            state=state,
            diagnostics=tuple(diagnostics),
            rejected_path=rejected_path,
        )

    # --- check mode: emit OK and return ---------------------------------
    if check or not apply:
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

    # --- apply mode: atomic write per file ------------------------------
    audit_path = audit_log_path or (target_path / AUDIT_LOG)
    timestamp = _now_iso()
    # Apply sites in DESCENDING line order so that an insertion at a
    # lower line number does NOT shift the post-patch line number of a
    # site at a higher pre-patch line number. Pre-validation uses the
    # ORIGINAL file bytes; the apply pass mutates them in reverse.
    apply_sites = sorted(sites, key=lambda s: s.line_for_state, reverse=True)
    for site in apply_sites:
        if site.site_id in sites_already:
            diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        path = target_path / site.file
        before = path.read_bytes()
        text = before.decode("utf-8", errors="replace")
        anchor = site.primary_anchor()
        lines = text.splitlines(keepends=True)
        # 1-based line number -> 0-based index
        idx = anchor.line - 1
        # Branch on the site kind:
        #   "cap"          — REPLACE the primary anchor (and the sibling
        #                    secondary anchor) with the new replacement
        #                    text in-place.
        #   "schema_append"— INSERT a new line right after the primary
        #                    anchor (inside the multi-line implicit-concat
        #                    value of a `description` field).
        #   "append"       — INSERT a new line right after the primary
        #                    anchor (Task E additive-only spec).
        if site.kind == "cap":
            # The S1.cap site is a pair (a, b) at two consecutive lines.
            # We replace BOTH anchor lines with the new text. ``insertion``
            # is the new pair as a single string with newlines.
            new_pair_lines = site.insertion.splitlines(keepends=True)
            # Replace lines[idx:idx+2] with new_pair_lines. The pre-validation
            # pass guarantees both anchors match; this is a no-arg slice.
            lines = lines[:idx] + new_pair_lines + lines[idx + 2 :]
        else:
            # append / schema_append: insert one new line right after
            # the primary anchor.
            lines.insert(idx + 1, site.insertion)
        after_bytes = "".join(lines).encode("utf-8")
        try:
            _atomic_write_bytes(path, after_bytes)
        except (PermissionError, OSError) as exc:
            # PermissionError is a subclass of OSError; a single handler
            # covers both "permission denied" (explicit) and other I/O
            # failures (full disk, fs error, etc.) — all map to exit 3.
            if isinstance(exc, PermissionError):
                diagnostics.append(PERMISSION_DENIED.format(path=str(path)))
            else:
                diagnostics.append(IO_ERROR.format(path=str(path), error=str(exc)))
            state[site.site_id] = "drifted"
            write_state(target_path, state)
            return PatcherResult(
                exit_code=EXIT_PERMISSION,
                sites_patched=tuple(sites_patched),
                sites_already=tuple(sites_already),
                state=state,
                diagnostics=tuple(diagnostics),
            )
        # audit log on --force (FORCE_AUDIT_LOG). Non-force runs do NOT
        # append to the audit log; the .patch.state.json sidecar is the
        # durable record for normal apply runs.
        if force:
            diff_sha = _diff_sha(before, after_bytes)
            audit_line = FORCE_AUDIT_LOG.format(
                timestamp=timestamp,
                site_id=site.site_id,
                diff_sha=diff_sha,
                target=str(target_path),
            )
            _append_audit_log(audit_path, audit_line)
        sites_patched.append(site.site_id)
        state[site.site_id] = "patched"
        diagnostics.append(OK_PATCHED.format(site_id=site.site_id))

    # cross-filesystem warn (best-effort)
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
