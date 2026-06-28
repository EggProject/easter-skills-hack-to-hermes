"""Per-invocation finalize helper extracted from ``_patcher_pipeline``.

Extracted to keep :mod:`_patcher_pipeline` under wemake WPS202
(<=7 module members). Holds the ``_FinalizeInputs`` bundle dataclass
and the ``_finalize_apply`` function that writes state and builds
the EXIT_OK PatcherResult.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from easter_hermes_sorry_skills import _patcher_pipeline_apply as _apply_mod
from easter_hermes_sorry_skills import _patcher_pipeline_imports as _imps
from easter_hermes_sorry_skills._i18n_pick import pick
from easter_hermes_sorry_skills._patcher_pipeline_emit import _SiteDiff
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher_pipeline import ApplySitesInputs


@dataclasses.dataclass(frozen=True)
class _FinalizeInputs:
    """Bundled args for :func:`_finalize_apply` (WPS211 <= 5 args)."""

    inputs: ApplySitesInputs
    sites_patched: list[str]
    sites_already: list[str]
    state: dict[str, str]
    diagnostics: list[str]
    site_diffs: list[_SiteDiff]
    lang: str = "en"


def _finalize_apply(spec: _FinalizeInputs) -> PatcherResult:
    """Write cross-FS warning, then EXIT_OK.

    The ``.patch.state.json`` sidecar was removed; ``_finalize_apply``
    no longer calls a state-write callable. The state is no longer
    persisted across runs — idempotency flows through
    :func:`site_already_patched` reading the target file at validation
    time.

    Note: ``spec`` is a ``@dataclass(frozen=True)``, so attribute
    assignment is forbidden — but ``spec.diagnostics`` is a
    ``list[str]`` field whose contents remain mutable. We
    intentionally append ``CROSS_FS_WARN`` to that list in place
    (rather than rebuilding the dataclass with ``dataclasses.replace``)
    because the field is constructed once at the call site and shared
    by reference; mutating the list keeps the warning alongside the
    diagnostics accumulated upstream without an extra copy.

    ``lang`` selects the single-language module via
    :func:`easter_hermes_sorry_skills._i18n_pick.pick`; defaults to
    ``"en"``.
    """
    target_path = spec.inputs.target_path
    if _imps._cross_filesystem(target_path):
        spec.diagnostics.append(pick(spec.lang).CROSS_FS_WARN)
    return _apply_mod.build_result(
        exit_code=spec.inputs.exit_ok_code,
        sites_patched=tuple(spec.sites_patched),
        sites_already=tuple(spec.sites_already),
        state=spec.state,
        diagnostics=tuple(spec.diagnostics),
    )
