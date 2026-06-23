"""Per-invocation finalize helper extracted from ``_patcher_pipeline``.

Extracted to keep :mod:`_patcher_pipeline` under wemake WPS202
(<=7 module members). Holds the ``_FinalizeInputs`` bundle dataclass
and the ``_finalize_apply`` function that writes state and builds
the EXIT_OK PatcherResult.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from easter_hermes_sorry_skills import _patcher_pipeline_apply as _apply_mod
from easter_hermes_sorry_skills import _patcher_pipeline_imports as _imps
from easter_hermes_sorry_skills._patcher_pipeline_emit import _SiteDiff
from easter_hermes_sorry_skills.i18n.messages_en import CROSS_FS_WARN

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher import PatcherResult
    from easter_hermes_sorry_skills._patcher_pipeline import ApplySitesInputs


@dataclasses.dataclass(frozen=True)
class _FinalizeInputs:
    """Bundled args for :func:`_finalize_apply` (WPS211 <= 5 args)."""

    inputs: ApplySitesInputs
    sites_patched: list[str]
    sites_already: list[str]
    state: dict[str, str]
    diagnostics: list[str]
    audit_path: Path
    timestamp: str
    site_diffs: list[_SiteDiff]


def _finalize_apply(spec: _FinalizeInputs) -> PatcherResult:
    """Write state + cross-FS warning, then EXIT_OK."""
    target_path = spec.inputs.target_path
    if _imps._cross_filesystem(target_path):
        spec.diagnostics.append(CROSS_FS_WARN)
    spec.inputs.write_state_fn(target_path, spec.state)
    return _apply_mod.build_result(
        exit_code=spec.inputs.exit_ok_code,
        sites_patched=tuple(spec.sites_patched),
        sites_already=tuple(spec.sites_already),
        state=spec.state,
        diagnostics=tuple(spec.diagnostics),
    )
