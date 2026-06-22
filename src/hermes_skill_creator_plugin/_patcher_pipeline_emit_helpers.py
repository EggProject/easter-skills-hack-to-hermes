"""Internal helpers extracted from ``_patcher_pipeline_emit``.

Pure-function building blocks (drift diagnostic formatting + the
per-invocation diff-sha combiner) extracted to keep
``_patcher_pipeline_emit`` under wemake WPS202 (<=7 module members).
"""

from __future__ import annotations

from typing import Any

from hermes_skill_creator_plugin._patcher_apply_atomic import _diff_sha
from hermes_skill_creator_plugin._patcher_pipeline_consts import REASON_LINE_DRIFT
from hermes_skill_creator_plugin.i18n.messages_en import (
    LINE_DRIFT,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)


def append_drift_diagnostic(
    failure: dict[str, Any],
    diagnostics: list[str],
) -> None:
    """Append the right i18n diagnostic for one failure entry."""
    if failure.get("reason") == REASON_LINE_DRIFT:
        diagnostics.append(
            LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            ),
        )
    else:
        diagnostics.append(
            TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=failure.get("actual_at_line_<missing>", ""),
            ),
        )
    diagnostics.append(VALIDATION_FAILED.format(site_id=failure["site_id"]))


def combined_sha(parts: list[str]) -> str:
    """Combine per-site diff shas into one sha; empty when ``parts`` is empty."""
    if not parts:
        return ""
    joined = b"".join(part.encode("ascii") for part in parts)
    return _diff_sha(joined, b"")
