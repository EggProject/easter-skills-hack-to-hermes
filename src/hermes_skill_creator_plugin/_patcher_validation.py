"""Patcher pre-validation: per-site drift detection + failure builders.

Extracted from :mod:`._patcher` to keep the orchestrator under
wemake WPS202 (module members <= 7). The public symbol
:class:`_ValidationResult` is a private struct used by the orchestrator.

Each site is validated in a single pass against the file's raw bytes
(multi-signal targeting: 8+ char anchor + 1-based line number). Any
drift returns a failure dict consumed by the pipeline's ``fail_with_drift``
emitter.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._patcher_consts import (
    MISSING_FILE,
    NOT_FOUND,
    OUT_OF_RANGE,
    REASON_LINE_DRIFT,
    REASON_TEXT_DRIFT,
    STATE_MATCHED,
    STATE_PATCHED,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    locate_anchor,
    site_already_patched,
)
from hermes_skill_creator_plugin._patcher_sites import Anchor, Site


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """Outcome of pre-validation across all sites."""

    failures: list[dict[str, Any]]
    matched_count: int


def validate_sites(
    sites: list[Site],
    target_path: Path,
    state: dict[str, str],
    sites_already: list[str],
) -> ValidationResult:
    """Pre-validate every site and update ``state`` / ``sites_already``."""
    failures: list[dict[str, Any]] = []
    for site in sites:
        outcome = _validate_one_site(site, target_path, state, sites_already)
        if outcome is not None:
            failures.append(outcome)
    return ValidationResult(failures=failures, matched_count=0)


def _validate_one_site(
    site: Site,
    target_path: Path,
    state: dict[str, str],
    sites_already: list[str],
) -> dict[str, Any] | None:
    """Validate one site; return a failure dict or ``None``."""
    path = target_path / site.file_path
    if not path.exists():
        return _missing_file_failure(site)
    text = path.read_text(encoding="utf-8", errors="replace")
    if site_already_patched(text, site):
        sites_already.append(site.site_id)
        state[site.site_id] = STATE_PATCHED
        return None
    failure = _validate_site_anchors(site, text)
    if failure is not None:
        return failure
    state[site.site_id] = STATE_MATCHED
    return None


def _missing_file_failure(site: Site) -> dict[str, Any]:
    """Build a TEXT_DRIFT failure for a site whose file is missing."""
    return {
        "site_id": site.site_id,
        "reason": REASON_TEXT_DRIFT,
        "expected": site.primary_anchor().text,
        "actual_at_line_<missing>": MISSING_FILE,
    }


def _validate_site_anchors(
    site: Site,
    text: str,
) -> dict[str, Any] | None:
    """Return a drift failure dict for ``site`` if any anchor drifted."""
    for anchor in site.anchors:
        line_no = locate_anchor(text, anchor)
        if line_no == 0:
            return _text_drift_failure(site, anchor)
        if line_no != anchor.line:
            return _line_drift_failure(site, anchor, line_no, text)
    return None


def _text_drift_failure(site: Site, anchor: Anchor) -> dict[str, Any]:
    """Build a TEXT_DRIFT failure (anchor not found)."""
    return {
        "site_id": site.site_id,
        "anchor_line": anchor.line,
        "reason": REASON_TEXT_DRIFT,
        "expected": anchor.text,
        "actual_at_line_<missing>": NOT_FOUND,
    }


def _line_drift_failure(
    site: Site,
    anchor: Anchor,
    line_no: int,
    text: str,
) -> dict[str, Any]:
    """Build a LINE_DRIFT failure (anchor at wrong line)."""
    lines = text.splitlines()
    actual = lines[line_no - 1] if line_no <= len(lines) else OUT_OF_RANGE
    return {
        "site_id": site.site_id,
        "anchor_line": anchor.line,
        "found_at_line": line_no,
        "reason": REASON_LINE_DRIFT,
        "expected": anchor.text,
        "actual_at_line_<n>": actual,
    }


__all__ = [
    "ValidationResult",
    "validate_sites",
]
