"""Drift-emission helpers + ``mutate_lines_for_site`` for the patcher.

Split from ``_patcher_pipeline`` to keep module surface small
(WPS202) and to lower cognitive complexity (WPS231).

The ``.patch.rejected`` sidecar was removed in the sidecar-cleanup
phase; ``fail_with_drift`` now only emits diagnostics and returns
``PatcherResult.rejected_path=None``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from easter_hermes_sorry_skills import _patcher_pipeline_emit_helpers as _helpers
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult
from easter_hermes_sorry_skills._patcher_sites import Site


@dataclasses.dataclass(frozen=True)
class _FailDriftInputs:
    """Inputs for :func:`fail_with_drift` (bundled for WPS211)."""

    target_path: Path
    failures: list[dict[str, Any]]
    state: dict[str, str]
    sites_already: list[str]
    diagnostics: list[str]
    git_head: str
    exit_codes: tuple[int, int]
    lang: str = "en"


@dataclasses.dataclass(frozen=True)
class _SiteDiff:
    """Per-site diff bundle accumulated by the audit-log emit pipeline."""

    site_id: str
    before: bytes
    after_bytes: bytes


def fail_with_drift(inputs: _FailDriftInputs) -> PatcherResult:
    """Build the EXIT_DRIFT result and append diagnostics.

    The two exit-code constants are passed in (not imported) so this
    helper has no compile-time cycle with ``_patcher``. The caller
    (``_patcher.run_patch``) supplies the canonical values from
    ``EXIT_DRIFT`` and ``EXIT_PERMISSION``. The ``.patch.rejected``
    sidecar is no longer written; ``rejected_path`` on the result is
    always ``None``.

    ``lang`` selects the single-language i18n module for the drift
    diagnostics via :func:`easter_hermes_sorry_skills._i18n_pick.pick`;
    defaults to ``"en"``.
    """
    exit_drift_code, _ = inputs.exit_codes
    for failure in inputs.failures:
        _helpers.append_drift_diagnostic(failure, inputs.diagnostics, lang=inputs.lang)
    from easter_hermes_sorry_skills._patcher_pipeline_apply import build_result

    return build_result(
        exit_code=exit_drift_code,
        diagnostics=tuple(inputs.diagnostics),
        state=inputs.state,
        sites_patched=(),
        sites_already=(),
    )


def mutate_lines_for_site(site: Site, text: str) -> list[str]:
    """Return the post-mutation line list for ``site`` (cap replace or append)."""
    lines = text.splitlines(keepends=True)
    idx = site.primary_anchor().line - 1
    if site.kind == "cap":
        new_pair_lines = site.insertion.splitlines(keepends=True)
        tail_offset = idx + 2
        return lines[:idx] + new_pair_lines + lines[tail_offset:]
    lines.insert(idx + 1, site.insertion)
    return lines
