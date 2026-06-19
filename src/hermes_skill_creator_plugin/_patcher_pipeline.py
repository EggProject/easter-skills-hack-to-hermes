"""Apply + drift-emission pipeline helpers for the patcher orchestrator.

The orchestrator (``_patcher.run_patch``) is the entry point; this
module holds the per-site apply loop, the drift-failure diagnostic
emitter, and the ``--force`` audit log writer. TDD tests reference
several private helpers from ``hermes_skill_creator_plugin._patcher``;
``_patcher.py`` re-exports them so existing imports continue to work.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin._patcher_apply import (
    AUDIT_LOG,
    _append_audit_log,
    _diff_sha,
    write_rejected,
    write_state,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from hermes_skill_creator_plugin._patcher import PatcherResult

    WriteStateFn = Callable[[Path, dict[str, str]], None]  # noqa: WPS462
# Imported lazily inside the helper so monkeypatch.setattr on the
# ``_patcher`` module's ``_atomic_write_bytes`` (test seam) takes effect.
# (See ``tests/unit/test_patcher.py::test_apply_permission_error_branch``.)
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import now_iso as _now_iso
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import (
    CROSS_FS_WARN,
    FORCE_AUDIT_LOG,
    IO_ERROR,
    LINE_DRIFT,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
    PERMISSION_DENIED,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)

# State strings used in the ``state`` dict (mirrored in ``_patcher``).
_STATE_PATCHED = "patched"
_STATE_DRIFTED = "drifted"

# Failure-reason strings emitted to the rejected sidecar.
_REASON_LINE_DRIFT = "LINE_DRIFT"
_REASON_TEXT_DRIFT = "TEXT_DRIFT"


def fail_with_drift(
    target_path: Path,
    failures: list[dict[str, Any]],
    state: dict[str, str],
    sites_already: list[str],
    diagnostics: list[str],
    git_head: str,
    exit_drift_code: int,
    exit_permission_code: int,
) -> "PatcherResult":
    """Build the EXIT_DRIFT result, write rejected sidecar, append diagnostics.

    The two exit-code constants are passed in (not imported) so this
    helper has no compile-time cycle with ``_patcher``. The caller
    (``_patcher.run_patch``) supplies the canonical values from
    ``EXIT_DRIFT`` and ``EXIT_PERMISSION``.
    """
    rejected_path = write_rejected(
        target_path,
        failures=failures,
        remediation_en=(
            "Re-run with --force --i-accept-line-drift "
            "after reviewing the diff."
        ),
        remediation_hu=(
            "Futtassa újra --force --i-accept-line-drift "
            "kapcsolóval a diff átnézése után."
        ),
        git_head=git_head,
    )
    for failure in failures:
        _append_drift_diagnostic(failure, diagnostics)
    return _build_result(
        exit_code=exit_drift_code,
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
        diagnostics.append(
            LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            )
        )
    else:
        diagnostics.append(
            TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            )
        )
    diagnostics.append(VALIDATION_FAILED.format(site_id=failure["site_id"]))


def ok_check_result(
    sites: list[Site],
    state: dict[str, str],
    sites_patched: list[str],
    sites_already: list[str],
    target_path: Path,
    diagnostics: list[str],
    exit_ok_code: int,
    write_state_fn: "WriteStateFn",
) -> "PatcherResult":
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    for site in sites:
        if site.site_id in sites_already:
            diagnostics.append(
                OK_ALREADY_PATCHED.format(site_id=site.site_id)
            )
        else:
            diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    write_state_fn(target_path, state)
    return _build_result(
        exit_code=exit_ok_code,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


def apply_sites(
    sites: list[Site],
    target_path: Path,
    state: dict[str, str],
    sites_patched: list[str],
    sites_already: list[str],
    diagnostics: list[str],
    force: bool,
    audit_log_path: Path | None,
    exit_ok_code: int,
    write_state_fn: "WriteStateFn",
) -> "PatcherResult":
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    audit_path = audit_log_path or (target_path / AUDIT_LOG)
    timestamp = _now_iso()
    apply_sites_sorted = sorted(
        sites, key=lambda site: site.line_for_state, reverse=True
    )
    for site in apply_sites_sorted:
        if site.site_id in sites_already:
            diagnostics.append(
                OK_ALREADY_PATCHED.format(site_id=site.site_id)
            )
            continue
        outcome = _apply_one_site(
            site, target_path, force, audit_path, timestamp
        )
        if outcome is not None:
            state[site.site_id] = _STATE_DRIFTED
            write_state_fn(target_path, state)
            return outcome
        sites_patched.append(site.site_id)
        state[site.site_id] = _STATE_PATCHED
        diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    if _cross_filesystem(target_path):
        diagnostics.append(CROSS_FS_WARN)
    write_state_fn(target_path, state)
    return _build_result(
        exit_code=exit_ok_code,
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
) -> "PatcherResult | None":
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    path = target_path / site.file
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = mutate_lines_for_site(site, text)
    after_bytes = "".join(new_lines).encode("utf-8")
    try:
        # Lazy import so monkeypatch.setattr on the ``_patcher`` module
        # (the test seam) is picked up.
        from hermes_skill_creator_plugin import _patcher

        _patcher._atomic_write_bytes(path, after_bytes)
    except (PermissionError, OSError) as exc:
        if isinstance(exc, PermissionError):
            diag = PERMISSION_DENIED.format(path=str(path))
            exit_code = 3  # EXIT_PERMISSION
        else:
            diag = IO_ERROR.format(path=str(path), error=str(exc))
            exit_code = 4  # EXIT_IO
        return _build_result(
            exit_code=exit_code,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=(diag,),
        )
    if force:
        emit_audit_log(
            audit_path, timestamp, site.site_id, before, after_bytes,
            target_path,
        )
    return None


def mutate_lines_for_site(site: Site, text: str) -> list[str]:
    """Return the post-mutation line list for ``site`` (cap replace or append)."""
    lines = text.splitlines(keepends=True)
    idx = site.primary_anchor().line - 1
    if site.kind == "cap":
        new_pair_lines = site.insertion.splitlines(keepends=True)
        return lines[:idx] + new_pair_lines + lines[idx + 2:]
    lines.insert(idx + 1, site.insertion)
    return lines


def emit_audit_log(
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


def _build_result(
    *,
    exit_code: int,
    sites_patched: tuple[str, ...],
    sites_already: tuple[str, ...],
    state: dict[str, str],
    diagnostics: tuple[str, ...],
    rejected_path: Path | None = None,
) -> "PatcherResult":
    """Build a ``PatcherResult`` (lazy import to avoid the cycle)."""
    # Runtime import: the cycle is real, so TYPE_CHECKING isn't enough.
    from hermes_skill_creator_plugin._patcher import PatcherResult

    return PatcherResult(
        exit_code=exit_code,
        sites_patched=sites_patched,
        sites_already=sites_already,
        state=state,
        diagnostics=diagnostics,
        rejected_path=rejected_path,
    )


__all__ = [
    "apply_sites",
    "emit_audit_log",
    "fail_with_drift",
    "mutate_lines_for_site",
    "ok_check_result",
]
