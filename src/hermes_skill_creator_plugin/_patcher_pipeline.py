"""Apply pipeline helpers for the patcher orchestrator.

The drift-emission helpers (and ``mutate_lines_for_site``) live in
``_patcher_pipeline_emit`` (split to keep this module surface small
under WPS202). The per-site payload + the audit emitter live in
``_patcher_pipeline_payload`` and ``_patcher_pipeline_audit``. The
parameter-object dataclasses live in ``_patcher_pipeline_args``.
The orchestrator (``_patcher.run_patch``) is the entry point; this
module holds the per-site apply loop and the ``--check`` / IO-error
helpers. TDD tests reference several private helpers from
``hermes_skill_creator_plugin._patcher``; ``_patcher.py`` re-exports
them so existing imports continue to work.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult

from hermes_skill_creator_plugin import _patcher as _patcher_mod
from hermes_skill_creator_plugin import i18n as _i18n
from hermes_skill_creator_plugin._patcher_apply import AUDIT_LOG
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import now_iso as _now_iso
from hermes_skill_creator_plugin._patcher_pipeline_args import (
    _ApplySitesArgs,
    _BuildResultArgs,
    _OkCheckArgs,
)
from hermes_skill_creator_plugin._patcher_pipeline_audit import (
    _emit_site_audit,
    _EmitSiteAuditArgs,
)
from hermes_skill_creator_plugin._patcher_pipeline_consts import (
    EXIT_IO,
    EXIT_PERMISSION,
    STATE_DRIFTED,
    STATE_PATCHED,
)
from hermes_skill_creator_plugin._patcher_pipeline_payload import (
    _build_site_payload,
)
from hermes_skill_creator_plugin._patcher_sites import Site


def ok_check_result(args: _OkCheckArgs) -> PatcherResult:
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    for site in args.sites:
        if site.site_id in args.sites_already:
            args.diagnostics.append(_i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id))
        else:
            args.diagnostics.append(_i18n.OK_PATCHED.format(site_id=site.site_id))
    args.write_state_fn(args.target_path, args.state)
    return _build_result(
        _BuildResultArgs(
            exit_code=args.exit_ok_code,
            sites_patched=tuple(args.sites_patched),
            sites_already=tuple(args.sites_already),
            state=args.state,
            diagnostics=tuple(args.diagnostics),
        ),
    )


def apply_sites(args: _ApplySitesArgs) -> PatcherResult:
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    audit_path = args.audit_log_path or (args.target_path / AUDIT_LOG)
    timestamp = _now_iso()
    for site in sorted(args.sites, key=lambda site: site.line_for_state, reverse=True):
        if site.site_id in args.sites_already:
            args.diagnostics.append(_i18n.OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        outcome = _apply_one_site(
            site=site,
            target_path=args.target_path,
            force=args.force,
            audit_path=audit_path,
            timestamp=timestamp,
        )
        if outcome is not None:
            args.state[site.site_id] = STATE_DRIFTED
            args.write_state_fn(args.target_path, args.state)
            return outcome
        args.sites_patched.append(site.site_id)
        args.state[site.site_id] = STATE_PATCHED
        args.diagnostics.append(_i18n.OK_PATCHED.format(site_id=site.site_id))
    if _cross_filesystem(args.target_path):
        args.diagnostics.append(_i18n.CROSS_FS_WARN)
    args.write_state_fn(args.target_path, args.state)
    return _build_result(
        _BuildResultArgs(
            exit_code=args.exit_ok_code,
            sites_patched=tuple(args.sites_patched),
            sites_already=tuple(args.sites_already),
            state=args.state,
            diagnostics=tuple(args.diagnostics),
        ),
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
            _EmitSiteAuditArgs(
                site=site,
                target_path=target_path,
                audit_path=audit_path,
                timestamp=timestamp,
                before=payload.before,
                after_bytes=payload.after_bytes,
            ),
        )
    return None


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
        _BuildResultArgs(
            exit_code=exit_code,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=(diag,),
        ),
    )


def _build_result(args: _BuildResultArgs) -> PatcherResult:
    """Build a ``PatcherResult`` (lazy import to avoid the cycle)."""
    # Runtime import: the cycle is real, so TYPE_CHECKING isn't enough.
    from hermes_skill_creator_plugin._patcher import PatcherResult

    return PatcherResult(
        exit_code=args.exit_code,
        sites_patched=args.sites_patched,
        sites_already=args.sites_already,
        state=args.state,
        diagnostics=args.diagnostics,
        rejected_path=args.rejected_path,
    )
