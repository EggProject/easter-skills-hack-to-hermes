"""Apply pipeline helpers for the patcher orchestrator.

The drift-emission helpers (and ``mutate_lines_for_site``) live in
``_patcher_pipeline_emit`` (split to keep this module surface small
under WPS202). The orchestrator (``_patcher.run_patch``) is the
entry point; this module holds the per-site apply loop and the
``--check`` / IO-error helpers. TDD tests reference several private
helpers from ``hermes_skill_creator_plugin._patcher``;
``_patcher.py`` re-exports them so existing imports continue to work.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin import _patcher as _patcher_mod
from hermes_skill_creator_plugin import i18n as _i18n
from hermes_skill_creator_plugin._patcher_apply import AUDIT_LOG
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import now_iso as _now_iso
from hermes_skill_creator_plugin._patcher_pipeline_consts import (
    EXIT_IO,
    EXIT_PERMISSION,
    STATE_DRIFTED,
    STATE_PATCHED,
)
from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    _AuditLogInputs,
    emit_audit_log,
    mutate_lines_for_site,
)
from hermes_skill_creator_plugin._patcher_sites import Site

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult

    WriteStateFn = Any  # Callable[[Path, dict[str, str]], None]


def ok_check_result(
    sites: list[Site],
    state: dict[str, str],
    sites_patched: list[str],
    sites_already: list[str],
    target_path: Path,
    diagnostics: list[str],
    exit_ok_code: int,
    write_state_fn: WriteStateFn,
) -> PatcherResult:
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    for site in sites:
        if site.site_id in sites_already:
            diagnostics.append(_i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id))
        else:
            diagnostics.append(_i18n.OK_PATCHED.format(site_id=site.site_id))
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
    write_state_fn: WriteStateFn,
) -> PatcherResult:
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    audit_path = audit_log_path or (target_path / AUDIT_LOG)
    timestamp = _now_iso()
    for site in sorted(sites, key=lambda site: site.line_for_state, reverse=True):
        if site.site_id in sites_already:
            diagnostics.append(_i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id))
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
        diagnostics.append(_i18n.OK_PATCHED.format(site_id=site.site_id))
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
) -> PatcherResult | None:
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    path = target_path / site.file_path
    payload = _build_site_payload(path, site)
    io_result = _try_atomic_write(path, payload.after_bytes)
    if io_result is not None:
        return io_result
    if force:
        _emit_site_audit(
            site=site,
            target_path=target_path,
            audit_path=audit_path,
            timestamp=timestamp,
            before=payload.before,
            after_bytes=payload.after_bytes,
        )
    return None


@dataclasses.dataclass(frozen=True)
class _SitePayload:
    """Before/after byte pair for one site's atomic write."""

    before: bytes
    after_bytes: bytes


def _build_site_payload(path: Path, site: Site) -> _SitePayload:
    """Read ``path`` and return the (before, after) byte pair for ``site``."""
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = mutate_lines_for_site(site, text)
    return _SitePayload(before=before, after_bytes="".join(new_lines).encode("utf-8"))


def _emit_site_audit(
    *,
    site: Site,
    target_path: Path,
    audit_path: Path,
    timestamp: str,
    before: bytes,
    after_bytes: bytes,
) -> None:
    emit_audit_log(
        _AuditLogInputs(
            audit_path=audit_path,
            timestamp=timestamp,
            site_id=site.site_id,
            before=before,
            after_bytes=after_bytes,
            target_path=target_path,
        ),
    )


def _try_atomic_write(path: Path, after_bytes: bytes) -> PatcherResult | None:
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
    exc: OSError | PermissionError,
) -> PatcherResult:
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


def _build_result(
    *,
    exit_code: int,
    sites_patched: tuple[str, ...],
    sites_already: tuple[str, ...],
    state: dict[str, str],
    diagnostics: tuple[str, ...],
    rejected_path: Path | None = None,
) -> PatcherResult:
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
