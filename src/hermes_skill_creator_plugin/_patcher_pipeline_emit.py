"""Drift-emission helpers + ``mutate_lines_for_site`` for the patcher.

Split from ``_patcher_pipeline`` to keep module surface small
(WPS202) and to lower cognitive complexity (WPS231).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin._patcher_apply import (
    _append_audit_log,
    write_rejected,
)
from hermes_skill_creator_plugin._patcher_apply_atomic import _diff_sha
from hermes_skill_creator_plugin._patcher_pipeline_consts import (
    REASON_LINE_DRIFT,
    REMEDIATION_EN,
    REMEDIATION_HU,
)
from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import (
    FORCE_AUDIT_LOG,
    LINE_DRIFT,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)

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
class _AuditLogInputs:
    """Inputs for :func:`emit_audit_log` (bundled for WPS211)."""

    audit_path: Path
    timestamp: str
    site_id: str
    before: bytes
    after_bytes: bytes
    target_path: Path


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
        _append_drift_diagnostic(failure, inputs.diagnostics)
    from hermes_skill_creator_plugin._patcher_pipeline import _build_result

    return _build_result(
        exit_code=exit_drift_code,
        sites_patched=(),
        sites_already=tuple(inputs.sites_already),
        state=inputs.state,
        diagnostics=tuple(inputs.diagnostics),
        rejected_path=rejected_path,
    )


def _append_drift_diagnostic(
    failure: dict[str, Any],
    diagnostics: list[str],
) -> None:
    """Append the right i18n diagnostic for one failure entry."""
    if failure.get("reason") == REASON_LINE_DRIFT:
        diagnostics.append(
            LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            )
        )
    else:
        diagnostics.append(
            TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            )
        )
    diagnostics.append(VALIDATION_FAILED.format(site_id=failure["site_id"]))


def emit_audit_log(inputs: _AuditLogInputs) -> None:
    """Append one FORCE_AUDIT_LOG line for a successful ``--force`` site."""
    diff_sha = _diff_sha(inputs.before, inputs.after_bytes)
    audit_line = FORCE_AUDIT_LOG.format(
        timestamp=inputs.timestamp,
        site_id=inputs.site_id,
        diff_sha=diff_sha,
        target=str(inputs.target_path),
    )
    _append_audit_log(inputs.audit_path, audit_line)


def mutate_lines_for_site(site: Site, text: str) -> list[str]:
    """Return the post-mutation line list for ``site`` (cap replace or append)."""
    lines = text.splitlines(keepends=True)
    idx = site.primary_anchor().line - 1
    if site.kind == "cap":
        new_pair_lines = site.insertion.splitlines(keepends=True)
        return lines[:idx] + new_pair_lines + lines[idx + 2:]
    lines.insert(idx + 1, site.insertion)
    return lines
