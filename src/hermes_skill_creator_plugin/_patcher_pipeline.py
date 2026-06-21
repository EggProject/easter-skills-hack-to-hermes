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

from hermes_skill_creator_plugin import _patcher_pipeline_imports as _imps
from hermes_skill_creator_plugin._patcher_pipeline_emit import _AuditLogInputs
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import (
    CROSS_FS_WARN,
    IO_ERROR,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
    PERMISSION_DENIED,
)

# Local bindings matching the previous top-level import names. The
# actual imports live in :mod:`._patcher_pipeline_imports` to keep
# this orchestrator under wemake WPS201 (<=12 imports per module).
# ``_patcher_mod`` is intentionally NOT bound here: importing
# :mod:`._patcher` at module top creates a cycle with
# :mod:`._patcher` -> :mod:`._patcher_pipeline`. The single user
# (``_try_atomic_write``) lazy-imports it via the runtime path.
# ``Site`` is kept as a direct class import so mypy preserves its
# concrete type (vs ``Site = _imps.Site`` which becomes ``Site?``).
AUDIT_LOG = _imps.AUDIT_LOG
_cross_filesystem = _imps._cross_filesystem
_now_iso = _imps._now_iso
EXIT_IO = _imps.EXIT_IO
EXIT_PERMISSION = _imps.EXIT_PERMISSION
STATE_DRIFTED = _imps.STATE_DRIFTED
STATE_PATCHED = _imps.STATE_PATCHED
emit_audit_log = _imps.emit_audit_log
mutate_lines_for_site = _imps.mutate_lines_for_site

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult

    WriteStateFn = Any  # Callable[[Path, dict[str, str]], None]


@dataclasses.dataclass(frozen=True)
class OkCheckInputs:
    """Inputs for :func:`ok_check_result` (bundled to keep the function small)."""

    sites: list[Site]
    state: dict[str, str]
    sites_patched: list[str]
    sites_already: list[str]
    target_path: Path
    diagnostics: list[str]
    exit_ok_code: int
    write_state_fn: WriteStateFn


@dataclasses.dataclass(frozen=True)
class ApplySitesInputs:
    """Inputs for :func:`apply_sites` (bundled to keep the function small)."""

    sites: list[Site]
    target_path: Path
    state: dict[str, str]
    sites_patched: list[str]
    sites_already: list[str]
    diagnostics: list[str]
    force: bool
    audit_log_path: Path | None
    exit_ok_code: int
    write_state_fn: WriteStateFn


@dataclasses.dataclass(frozen=True)
class _ApplyOneSiteInputs:
    """Inputs for :func:`_apply_one_site` (bundled to keep the function small)."""

    site: Site
    target_path: Path
    force: bool
    audit_path: Path
    timestamp: str


@dataclasses.dataclass(frozen=True)
class _EmitSiteAuditInputs:
    """Inputs for :func:`_emit_site_audit` (bundled to keep the function small)."""

    site: Site
    target_path: Path
    audit_path: Path
    timestamp: str
    before: bytes
    after_bytes: bytes


def ok_check_result(inputs: OkCheckInputs) -> PatcherResult:
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    diagnostics = inputs.diagnostics
    sites_patched = inputs.sites_patched
    sites_already = inputs.sites_already
    for site in inputs.sites:
        if site.site_id in sites_already:
            diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
        else:
            diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    inputs.write_state_fn(inputs.target_path, inputs.state)
    return _build_result(
        exit_code=inputs.exit_ok_code,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=inputs.state,
        diagnostics=tuple(diagnostics),
    )


def _finalize_apply(
    inputs: ApplySitesInputs,
    sites_patched: list[str],
    sites_already: list[str],
    state: dict[str, str],
    diagnostics: list[str],
) -> PatcherResult:
    """Write state + cross-FS warning, then build the EXIT_OK result."""
    target_path = inputs.target_path
    if _cross_filesystem(target_path):
        diagnostics.append(CROSS_FS_WARN)
    inputs.write_state_fn(target_path, state)
    return _build_result(
        exit_code=inputs.exit_ok_code,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


@dataclasses.dataclass(frozen=True)
class _ApplyLoop:
    """Per-iteration bindings for the descending-line ``apply_sites`` loop.

    Bundling these in a frozen dataclass keeps ``apply_sites`` under the
    wemake WPS210 local-variable cap (5).
    """

    inputs: ApplySitesInputs
    audit_path: Path
    timestamp: str
    sites_patched: list[str]
    state: dict[str, str]
    diagnostics: list[str]


def _apply_one_in_loop(site: Site, loop: _ApplyLoop) -> PatcherResult | None:
    """Apply one site inside the descending-line-order loop.

    Returns ``None`` on success (caller continues the loop) or a
    ``PatcherResult`` on IO error or drift.
    """
    outcome = _apply_one_site(
        _ApplyOneSiteInputs(
            site=site,
            target_path=loop.inputs.target_path,
            force=loop.inputs.force,
            audit_path=loop.audit_path,
            timestamp=loop.timestamp,
        ),
    )
    if outcome is not None:
        loop.state[site.site_id] = STATE_DRIFTED
        loop.inputs.write_state_fn(loop.inputs.target_path, loop.state)
        return outcome
    loop.sites_patched.append(site.site_id)
    loop.state[site.site_id] = STATE_PATCHED
    loop.diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
    return None


def apply_sites(inputs: ApplySitesInputs) -> PatcherResult:
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    target_path = inputs.target_path
    audit_path = inputs.audit_log_path or (target_path / AUDIT_LOG)
    loop = _ApplyLoop(
        inputs=inputs,
        audit_path=audit_path,
        timestamp=_now_iso(),
        sites_patched=inputs.sites_patched,
        state=inputs.state,
        diagnostics=inputs.diagnostics,
    )
    for site in sorted(inputs.sites, key=lambda site: site.line_for_state, reverse=True):
        if site.site_id in inputs.sites_already:
            loop.diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        outcome = _apply_one_in_loop(site, loop)
        if outcome is not None:
            return outcome
    return _finalize_apply(
        loop.inputs,
        loop.sites_patched,
        inputs.sites_already,
        loop.state,
        loop.diagnostics,
    )


def _apply_one_site(inputs: _ApplyOneSiteInputs) -> PatcherResult | None:
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    site = inputs.site
    target_path = inputs.target_path
    path = target_path / site.file_path
    payload = _build_site_payload(path, site)
    io_result = _try_atomic_write(path, payload.after_bytes)
    if io_result is not None:
        return io_result
    if inputs.force:
        _emit_site_audit(
            _EmitSiteAuditInputs(
                site=site,
                target_path=target_path,
                audit_path=inputs.audit_path,
                timestamp=inputs.timestamp,
                before=payload.before,
                after_bytes=payload.after_bytes,
            ),
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


def _emit_site_audit(inputs: _EmitSiteAuditInputs) -> None:
    emit_audit_log(
        _AuditLogInputs(
            audit_path=inputs.audit_path,
            timestamp=inputs.timestamp,
            site_id=inputs.site.site_id,
            before=inputs.before,
            after_bytes=inputs.after_bytes,
            target_path=inputs.target_path,
        ),
    )


def _try_atomic_write(path: Path, after_bytes: bytes) -> PatcherResult | None:
    """Atomic-write wrapper that converts IO errors to a PatcherResult.

    Returns ``None`` on success, or a PatcherResult on handled error.
    Lazy-imports ``_patcher`` so monkeypatch.setattr on the test seam
    is picked up. (See ``tests/unit/test_patcher.py::test_apply_permission_error_branch``.)
    """
    from hermes_skill_creator_plugin import _patcher as _patcher_mod

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
        diag = PERMISSION_DENIED.format(path=str(path))
        exit_code = EXIT_PERMISSION
    else:
        diag = IO_ERROR.format(path=str(path), error=str(exc))
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
        rejected_path=None,
    )


def _build_result_with_rejected(
    *,
    exit_code: int,
    diagnostics: tuple[str, ...],
    state: dict[str, str],
    rejected_path: Path,
) -> PatcherResult:
    """Build a ``PatcherResult`` with a non-``None`` ``rejected_path``."""
    from hermes_skill_creator_plugin._patcher import PatcherResult

    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state=state,
        diagnostics=diagnostics,
        rejected_path=rejected_path,
    )
