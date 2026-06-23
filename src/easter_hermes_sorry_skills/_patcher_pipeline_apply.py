"""Apply-one-site helpers for the patcher pipeline.

Extracted from ``_patcher_pipeline.py`` to keep that module under wemake
WPS202 (≤7 module members). Holds the per-site payload reader, the
atomic-write error-translation helper, and the ``PatcherResult`` builder
variants.

Result builders (``build_result``, ``build_result_with_rejected``,
``io_error_result``) live in ``_patcher_pipeline_results``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from easter_hermes_sorry_skills import _patcher_pipeline_imports as _imps
from easter_hermes_sorry_skills import _patcher_pipeline_results as _results_mod
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult
from easter_hermes_sorry_skills._patcher_sites import Site

EXIT_IO = _imps.EXIT_IO
EXIT_PERMISSION = _imps.EXIT_PERMISSION
IO_ERROR_TEXT = _imps.IO_ERROR
PERMISSION_DENIED_TEXT = _imps.PERMISSION_DENIED

# Re-bindings for backward compat (existing callers and test patches
# resolve through these names).
build_result = _results_mod.build_result
build_result_with_rejected = _results_mod.build_result_with_rejected
io_error_result = _results_mod.io_error_result


@dataclasses.dataclass(frozen=True)
class _ApplyOneSiteInputs:
    """Inputs for :func:`apply_one_site` (bundled to keep the function small)."""

    site: Site
    target_path: Path
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


def build_site_bytes(path: Path, site: Site) -> tuple[bytes, bytes]:
    """Read ``path`` and return the (before, after) byte tuple for ``site``."""
    payload = build_site_payload(path, site)
    return payload.before, payload.after_bytes


def apply_one_site(inputs: _ApplyOneSiteInputs) -> PatcherResult | None:
    """Apply one site. Return ``None`` on success, or a result on IO error."""
    site = inputs.site
    target_path = inputs.target_path
    path = target_path / site.file_path
    io_result = try_atomic_write(path, inputs.after_bytes)
    if io_result is not None:
        return io_result
    return None


def try_atomic_write(path: Path, after_bytes: bytes) -> PatcherResult | None:
    """Atomic-write wrapper that converts IO errors to a PatcherResult."""
    from easter_hermes_sorry_skills import _patcher as _patcher_mod

    try:
        _patcher_mod._atomic_write_bytes(path, after_bytes)
    except (PermissionError, OSError) as exc:
        return io_error_result(path, exc)
    return None


def emit_site_audit_stub(*_args: object, **_kwargs: object) -> None:
    """No-op stub: per-site audit emit was replaced by per-invocation.

    External callers / test monkeypatches that import this name should
    still resolve to a callable; the per-site line is now part of the
    per-invocation line emitted at the end of ``apply_sites``.
    """
