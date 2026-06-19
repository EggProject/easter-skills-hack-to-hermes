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

from hermes_skill_creator_plugin import _patcher as _patcher_mod
from hermes_skill_creator_plugin import i18n as _i18n
from hermes_skill_creator_plugin._patcher_apply import (
    AUDIT_LOG,
    _append_audit_log,
    _diff_sha,
    write_rejected,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import now_iso as _now_iso
from hermes_skill_creator_plugin._patcher_pipeline_consts import (
    EXIT_IO,
    EXIT_PERMISSION,
    REASON_LINE_DRIFT,
    REMEDIATION_EN,
    REMEDIATION_HU,
    STATE_DRIFTED,
    STATE_PATCHED,
)
from hermes_skill_creator_plugin._patcher_sites import Site

__all__ = [
    "apply_sites",
    "emit_audit_log",
    "fail_with_drift",
    "mutate_lines_for_site",
    "ok_check_result",
]

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult

    WriteStateFn = Any  # Callable[[Path, dict[str, str]], None]


def fail_with_drift(
    target_path: Path,
    failures: list[dict[str, Any]],
    state: dict[str, str],
    sites_already: list[str],
    diagnostics: list[str],
    git_head: str,
    exit_codes: tuple[int, int],
) -> "PatcherResult":
    """Build the EXIT_DRIFT result, write rejected sidecar, append diagnostics.

    The two exit-code constants are passed in (not imported) so this
    helper has no compile-time cycle with ``_patcher``. The caller
    (``_patcher.run_patch``) supplies the canonical values from
    ``EXIT_DRIFT`` and ``EXIT_PERMISSION``.
    """
    exit_drift_code, _ = exit_codes
    rejected_path = write_rejected(
        target_path,
        failures=failures,
        remediation_en=REMEDIATION_EN,
        remediation_hu=REMEDIATION_HU,
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
    if failure.get("reason") == REASON_LINE_DRIFT:
        diagnostics.append(
            _i18n.LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            )
        )
    else:
        diagnostics.append(
            _i18n.TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            )
        )
    diagnostics.append(
        _i18n.VALIDATION_FAILED.format(site_id=failure["site_id"])
    )


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
                _i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id)
            )
        else:
            diagnostics.append(
                _i18n.OK_PATCHED.format(site_id=site.site_id)
            )
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
                _i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id)
            )
            continue
        outcome = _apply_one_site(
            site=site,
            target_path=target_path,
            force=force,
            audit_path=audit_path,
            timestamp=timestamp,
        )
        if outcome is not None:
            state[site.site_id] = STATE_DRIFTED
            write_state_fn(target_path, state)
            return outcome
        sites_patched.append(site.site_id)
        state[site.site_id] = STATE_PATCHED
        diagnostics.append(
            _i18n.OK_PATCHED.format(site_id=site.site_id)
        )
    if _cross_filesystem(target_path):
        diagnostics.append(_i18n.CROSS_FS_WARN)
    write_state_fn(target_path, state)
    return _build_result(
        exit_code=exit_ok_code,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


def _apply_one_site(
    *,
    site: Site,
    target_path: Path,
    force: bool,
    audit_path: Path,
    timestamp: str,
) -> "PatcherResult | None":
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    path = target_path / site.file_path
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = mutate_lines_for_site(site, text)
    after_bytes = "".join(new_lines).encode("utf-8")
    io_result = _try_atomic_write(path, after_bytes)
    if io_result is not None:
        return io_result
    if force:
        emit_audit_log(
            audit_path, timestamp, site.site_id, before, after_bytes,
            target_path,
        )
    return None


def _try_atomic_write(path: Path, after_bytes: bytes) -> "PatcherResult | None":
    """Atomic-write wrapper that converts IO errors to a PatcherResult.

    Returns ``None`` on success, or a PatcherResult on handled error.
    Lazy-imports ``_patcher`` so monkeypatch.setattr on the test seam
    is picked up. (See ``tests/unit/test_patcher.py::test_apply_permission_error_branch``.)
    """
    try:
        _patcher_mod._atomic_write_bytes(path, after_bytes)
    except (PermissionError, OSError) as exc:
        return _io_error_result(path, exc)
    return None


def _io_error_result(
    path: Path,
    exc: "OSError | PermissionError",
) -> "PatcherResult":
    """Build the IO-error PatcherResult for the given exception."""
    if isinstance(exc, PermissionError):
        diag = _i18n.PERMISSION_DENIED.format(path=str(path))
        exit_code = EXIT_PERMISSION
    else:
        diag = _i18n.IO_ERROR.format(path=str(path), error=str(exc))
        exit_code = EXIT_IO
    return _build_result(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=(diag,),
    )


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
    audit_line = _i18n.FORCE_AUDIT_LOG.format(
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
