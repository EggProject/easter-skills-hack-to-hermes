"""Drift-emission helpers + ``mutate_lines_for_site`` for the patcher.

Split from ``_patcher_pipeline`` to keep module surface small
(WPS202) and to lower cognitive complexity (WPS231).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin import i18n as _i18n
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

if TYPE_CHECKING:
    from hermes_skill_creator_plugin._patcher import PatcherResult


def fail_with_drift(
    target_path: Path,
    failures: list[dict[str, Any]],
    state: dict[str, str],
    sites_already: list[str],
    diagnostics: list[str],
    git_head: str,
    exit_codes: tuple[int, int],
) -> PatcherResult:
    """Build the EXIT_DRIFT result, write rejected sidecar, append diagnostics.

    The two exit-code constants are passed in (not imported) so this
    helper has no compile-time cycle with ``_patcher``. The caller
    (``_patcher.run_patch``) supplies the canonical values from
    ``EXIT_DRIFT`` and ``EXIT_PERMISSION``.
    """
    exit_drift_code, _ = exit_codes
    rejected_path = write_rejected(
        target_path,
        failures=failures,
        remediation_en=REMEDIATION_EN,
        remediation_hu=REMEDIATION_HU,
        git_head=git_head,
    )
    for failure in failures:
        _append_drift_diagnostic(failure, diagnostics)
    from hermes_skill_creator_plugin._patcher_pipeline import _build_result

    return _build_result(
        exit_code=exit_drift_code,
        sites_patched=(),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
        rejected_path=rejected_path,
    )


def _append_drift_diagnostic(
    failure: dict[str, Any],
    diagnostics: list[str],
) -> None:
    """Append the right i18n diagnostic for one failure entry."""
    if failure.get("reason") == REASON_LINE_DRIFT:
        diagnostics.append(
            _i18n.LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            )
        )
    else:
        diagnostics.append(
            _i18n.TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            )
        )
    diagnostics.append(_i18n.VALIDATION_FAILED.format(site_id=failure["site_id"]))


def emit_audit_log(
    audit_path: Path,
    timestamp: str,
    site_id: str,
    before: bytes,
    after_bytes: bytes,
    target_path: Path,
) -> None:
    """Append one FORCE_AUDIT_LOG line for a successful ``--force`` site."""
    diff_sha = _diff_sha(before, after_bytes)
    audit_line = _i18n.FORCE_AUDIT_LOG.format(
        timestamp=timestamp,
        site_id=site_id,
        diff_sha=diff_sha,
        target=str(target_path),
    )
    _append_audit_log(audit_path, audit_line)


def mutate_lines_for_site(site: Site, text: str) -> list[str]:
    """Return the post-mutation line list for ``site`` (cap replace or append)."""
    lines = text.splitlines(keepends=True)
    idx = site.primary_anchor().line - 1
    if site.kind == "cap":
        new_pair_lines = site.insertion.splitlines(keepends=True)
        return lines[:idx] + new_pair_lines + lines[idx + 2:]
    lines.insert(idx + 1, site.insertion)
    return lines
