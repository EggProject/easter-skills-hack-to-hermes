"""Drift-emission helpers + ``mutate_lines_for_site`` for the patcher.

Split from ``_patcher_pipeline`` to keep module surface small
(WPS202) and to lower cognitive complexity (WPS231).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin import _patcher_pipeline_emit_helpers as _helpers
from hermes_skill_creator_plugin._patcher_apply import (
    _append_audit_log,
    write_rejected,
)
from hermes_skill_creator_plugin._patcher_apply_atomic import _diff_sha
from hermes_skill_creator_plugin._patcher_pipeline_consts import (
    REMEDIATION_EN,
    REMEDIATION_HU,
)
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import FORCE_AUDIT_LOG

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult


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


@dataclasses.dataclass(frozen=True)
class _SiteDiff:
    """Per-site diff bundle accumulated by the audit-log emit pipeline."""

    site_id: str
    before: bytes
    after_bytes: bytes


@dataclasses.dataclass(frozen=True)
class _AuditLogInputs:
    """Inputs for :func:`emit_audit_log` (bundled for WPS211)."""

    audit_path: Path
    timestamp: str
    target_path: Path
    site_diffs: tuple[_SiteDiff, ...] = ()


def fail_with_drift(inputs: _FailDriftInputs) -> PatcherResult:
    """Build the EXIT_DRIFT result, write rejected sidecar, append diagnostics.

    The two exit-code constants are passed in (not imported) so this
    helper has no compile-time cycle with ``_patcher``. The caller
    (``_patcher.run_patch``) supplies the canonical values from
    ``EXIT_DRIFT`` and ``EXIT_PERMISSION``.
    """
    exit_drift_code, _ = inputs.exit_codes
    rejected_path = write_rejected(
        inputs.target_path,
        failures=inputs.failures,
        remediation_en=REMEDIATION_EN,
        remediation_hu=REMEDIATION_HU,
        git_head=inputs.git_head,
    )
    for failure in inputs.failures:
        _helpers.append_drift_diagnostic(failure, inputs.diagnostics)
    from hermes_skill_creator_plugin._patcher_pipeline_apply import (
        build_result_with_rejected as _build_result_with_rejected,
    )

    return _build_result_with_rejected(
        exit_code=exit_drift_code,
        diagnostics=tuple(inputs.diagnostics),
        state=inputs.state,
        rejected_path=rejected_path,
    )


def emit_audit_log(inputs: _AuditLogInputs) -> None:
    """Append one FORCE_AUDIT_LOG line per ``--force`` invocation.

    Per AC-2.5.1 the audit log records ONE line per invocation
    (timestamp + combined diff sha256) at ``~/.hermes/patch-audit.log``.
    The combined diff is the sha256 of the empty-bytes separator joined
    per-site ``HASH_SEPARATOR`` diff shas (so the audit log records the
    set of sites touched by THIS invocation in a deterministic order).
    """
    parts: list[str] = []
    for site_diff in inputs.site_diffs:
        parts.append(_diff_sha(site_diff.before, site_diff.after_bytes))
    combined_diff_sha = _helpers.combined_sha(parts)
    site_ids = ",".join(sd.site_id for sd in inputs.site_diffs)
    audit_line = FORCE_AUDIT_LOG.format(
        timestamp=inputs.timestamp,
        site_id=site_ids,
        diff_sha=combined_diff_sha,
        target=str(inputs.target_path),
    )
    _append_audit_log(inputs.audit_path, audit_line)


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
