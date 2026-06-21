"""Apply-one-site helpers for the patcher pipeline.

Extracted from ``_patcher_pipeline.py`` to keep that module under wemake
WPS202 (≤7 module members). Holds the per-site payload reader, the
atomic-write error-translation helper, and the ``PatcherResult`` builder
variants.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_skill_creator_plugin import _patcher_pipeline_imports as _imps
from hermes_skill_creator_plugin._patcher_pipeline_emit import _AuditLogInputs
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import (
    IO_ERROR,
    PERMISSION_DENIED,
)

EXIT_IO = _imps.EXIT_IO
EXIT_PERMISSION = _imps.EXIT_PERMISSION
emit_audit_log = _imps.emit_audit_log

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult


@dataclasses.dataclass(frozen=True)
class _ApplyOneSiteInputs:
    """Inputs for :func:`apply_one_site` (bundled to keep the function small)."""

    site: Site
    target_path: Path
    force: bool
    audit_path: Path
    timestamp: str


@dataclasses.dataclass(frozen=True)
class _EmitSiteAuditInputs:
    """Inputs for :func:`emit_site_audit` (bundled to keep the function small)."""

    site: Site
    target_path: Path
    audit_path: Path
    timestamp: str
    before: bytes
    after_bytes: bytes


@dataclasses.dataclass(frozen=True)
class _SitePayload:
    """Before/after byte pair for one site's atomic write."""

    before: bytes
    after_bytes: bytes


def build_site_payload(path: Path, site: Site) -> _SitePayload:
    """Read ``path`` and return the (before, after) byte pair for ``site``."""
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = _imps.mutate_lines_for_site(site, text)
    return _SitePayload(before=before, after_bytes="".join(new_lines).encode("utf-8"))


def emit_site_audit(inputs: _EmitSiteAuditInputs) -> None:
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


def apply_one_site(inputs: _ApplyOneSiteInputs) -> PatcherResult | None:
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    site = inputs.site
    target_path = inputs.target_path
    path = target_path / site.file_path
    payload = build_site_payload(path, site)
    io_result = try_atomic_write(path, payload.after_bytes)
    if io_result is not None:
        return io_result
    if inputs.force:
        emit_site_audit(
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


def try_atomic_write(path: Path, after_bytes: bytes) -> PatcherResult | None:
    """Atomic-write wrapper that converts IO errors to a PatcherResult."""
    from hermes_skill_creator_plugin import _patcher as _patcher_mod

    try:
        _patcher_mod._atomic_write_bytes(path, after_bytes)
    except (PermissionError, OSError) as exc:
        return io_error_result(path, exc)
    return None


def io_error_result(path: Path, exc: OSError | PermissionError) -> PatcherResult:
    """Build the IO-error PatcherResult for the given exception."""
    if isinstance(exc, PermissionError):
        diag = PERMISSION_DENIED.format(path=str(path))
        exit_code = EXIT_PERMISSION
    else:
        diag = IO_ERROR.format(path=str(path), error=str(exc))
        exit_code = EXIT_IO
    return build_result(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=(diag,),
    )


def build_result(
    *,
    exit_code: int,
    sites_patched: tuple[str, ...],
    sites_already: tuple[str, ...],
    state: dict[str, str],
    diagnostics: tuple[str, ...],
) -> PatcherResult:
    """Build a ``PatcherResult`` (lazy import to avoid the cycle)."""
    from hermes_skill_creator_plugin._patcher import PatcherResult

    return PatcherResult(
        exit_code=exit_code,
        sites_patched=sites_patched,
        sites_already=sites_already,
        state=state,
        diagnostics=diagnostics,
        rejected_path=None,
    )


def build_result_with_rejected(
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
