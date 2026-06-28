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

from easter_hermes_sorry_skills import _patcher_pipeline_apply as _apply_mod
from easter_hermes_sorry_skills import _patcher_pipeline_finalize as _finalize_mod
from easter_hermes_sorry_skills import _patcher_pipeline_imports as _imps
from easter_hermes_sorry_skills._i18n_pick import pick
from easter_hermes_sorry_skills._patcher_pipeline_emit import _SiteDiff
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult
from easter_hermes_sorry_skills._patcher_sites import Site

# Re-bindings so the ``from _patcher_pipeline import X`` path keeps
# working for tests that reach for these symbols directly.
_build_result = _apply_mod.build_result
_apply_one_site = _apply_mod.apply_one_site

audit_log_path = _imps.audit_log_path
_cross_filesystem = _imps._cross_filesystem
STATE_DRIFTED = _imps.STATE_DRIFTED
STATE_PATCHED = _imps.STATE_PATCHED

if TYPE_CHECKING:
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
    lang: str = "en"


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
    lang: str = "en"


@dataclasses.dataclass
class _ApplyLoop:
    """Per-iteration bindings for the descending-line ``apply_sites`` loop."""

    inputs: ApplySitesInputs
    sites_patched: list[str]
    state: dict[str, str]
    diagnostics: list[str]
    site_diffs: list[_SiteDiff] = dataclasses.field(default_factory=list)


def ok_check_result(inputs: OkCheckInputs) -> PatcherResult:
    """Build the EXIT_OK result for ``--check`` (or non-apply runs)."""
    diagnostics = inputs.diagnostics
    sites_patched = inputs.sites_patched
    sites_already = inputs.sites_already
    msgs = pick(inputs.lang)
    for site in inputs.sites:
        if site.site_id in sites_already:
            diagnostics.append(msgs.OK_ALREADY_PATCHED.format(site_id=site.site_id))
        else:
            diagnostics.append(msgs.OK_PATCHED.format(site_id=site.site_id))
    return _build_result(
        exit_code=inputs.exit_ok_code,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=inputs.state,
        diagnostics=tuple(diagnostics),
    )


_finalize_apply = _finalize_mod._finalize_apply


def _apply_one_in_loop(site: Site, loop: _ApplyLoop) -> PatcherResult | None:
    """Apply one site inside the descending-line-order loop."""
    payload = _apply_mod.build_site_payload(
        loop.inputs.target_path / site.file_path,
        site,
    )
    outcome = _apply_one_site(
        _apply_mod._ApplyOneSiteInputs(
            site=site,
            target_path=loop.inputs.target_path,
            after_bytes=payload.after_bytes,
        ),
    )
    if outcome is not None:
        loop.state[site.site_id] = STATE_DRIFTED
        return outcome
    msgs = pick(loop.inputs.lang)
    loop.sites_patched.append(site.site_id)
    loop.state[site.site_id] = STATE_PATCHED
    loop.diagnostics.append(msgs.OK_PATCHED.format(site_id=site.site_id))
    loop.site_diffs.append(
        _SiteDiff(site_id=site.site_id, before=payload.before, after_bytes=payload.after_bytes),
    )
    return None


def apply_sites(inputs: ApplySitesInputs) -> PatcherResult:
    """Apply sites in DESCENDING line order (insertions don't shift later sites)."""
    loop = _ApplyLoop(
        inputs=inputs,
        sites_patched=inputs.sites_patched,
        state=inputs.state,
        diagnostics=inputs.diagnostics,
    )
    msgs = pick(inputs.lang)
    for site in sorted(inputs.sites, key=lambda site: site.line_for_state, reverse=True):
        if site.site_id in inputs.sites_already:
            loop.diagnostics.append(msgs.OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        outcome = _apply_one_in_loop(site, loop)
        if outcome is not None:
            return outcome
    return _finalize_apply(
        _finalize_mod._FinalizeInputs(
            inputs=loop.inputs,
            sites_patched=loop.sites_patched,
            sites_already=inputs.sites_already,
            state=loop.state,
            diagnostics=loop.diagnostics,
            site_diffs=loop.site_diffs,
            lang=inputs.lang,
        ),
    )
