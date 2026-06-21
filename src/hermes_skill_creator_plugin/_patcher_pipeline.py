"""Apply pipeline helpers for the patcher orchestrator.

The drift-emission helpers (and ``mutate_lines_for_site``) live in
``_patcher_pipeline_emit``. The per-site apply + payload + IO-error
helpers live in ``_patcher_pipeline_apply``. The orchestrator
(``_patcher.run_patch``) is the entry point; this module holds the
top-level ``ok_check_result`` / ``apply_sites`` loops and the
``_ApplyLoop`` bundle dataclass.

The split keeps this module under wemake WPS202 (≤7 module members).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin import _patcher_pipeline_apply as _apply_mod
from hermes_skill_creator_plugin import _patcher_pipeline_imports as _imps
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import (
    CROSS_FS_WARN,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
)

# Re-bindings so the ``from _patcher_pipeline import X`` path keeps
# working for tests that reach for these symbols directly.
_build_result = _apply_mod.build_result
_build_site_payload = _apply_mod.build_site_payload
_emit_site_audit = _apply_mod.emit_site_audit
_io_error_result = _apply_mod.io_error_result
_apply_one_site = _apply_mod.apply_one_site
_try_atomic_write = _apply_mod.try_atomic_write

AUDIT_LOG = _imps.AUDIT_LOG
_cross_filesystem = _imps._cross_filesystem
_now_iso = _imps._now_iso
STATE_DRIFTED = _imps.STATE_DRIFTED
STATE_PATCHED = _imps.STATE_PATCHED

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
class _ApplyLoop:
    """Per-iteration bindings for the descending-line ``apply_sites`` loop."""

    inputs: ApplySitesInputs
    audit_path: Path
    timestamp: str
    sites_patched: list[str]
    state: dict[str, str]
    diagnostics: list[str]


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


def _apply_one_in_loop(site: Site, loop: _ApplyLoop) -> PatcherResult | None:
    """Apply one site inside the descending-line-order loop."""
    outcome = _apply_one_site(
        _apply_mod._ApplyOneSiteInputs(
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
