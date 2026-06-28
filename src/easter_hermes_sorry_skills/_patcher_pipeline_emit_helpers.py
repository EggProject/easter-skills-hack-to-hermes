"""Internal helpers extracted from ``_patcher_pipeline_emit``.

Pure-function building blocks (drift diagnostic formatting + the
per-invocation diff-sha combiner) extracted to keep
``_patcher_pipeline_emit`` under wemake WPS202 (<=7 module members).
"""

from __future__ import annotations

from typing import Any

from easter_hermes_sorry_skills._i18n_pick import pick
from easter_hermes_sorry_skills._patcher_apply_atomic import _diff_sha
from easter_hermes_sorry_skills._patcher_consts import REASON_LINE_DRIFT


def _pick_text_drift_actual(failure: dict[str, Any]) -> str:
    """Return the TEXT_DRIFT ``actual`` string from a failure dict.

    TEXT_DRIFT failures key the actual content under the
    ``actual_at_line_unknown`` sentinel (the line number is unknown
    because the file is missing or the anchor was not found). LINE_DRIFT
    failures use a dynamic ``actual_at_line_<N>`` key and are not
    consumed here.
    """
    actual_at_unknown = failure.get("actual_at_line_unknown", "")
    return str(actual_at_unknown)


def append_drift_diagnostic(
    failure: dict[str, Any],
    diagnostics: list[str],
    lang: str = "en",
) -> None:
    """Append the right i18n diagnostic for one failure entry.

    ``lang`` selects the single-language module via
    :func:`easter_hermes_sorry_skills._i18n_pick.pick`; defaults to
    ``"en"`` for callers that do not pass a language.
    """
    msgs = pick(lang)
    if failure.get("reason") == REASON_LINE_DRIFT:
        diagnostics.append(
            msgs.LINE_DRIFT.format(
                site_id=failure["site_id"],
                line=failure["anchor_line"],
            ),
        )
    else:
        diagnostics.append(
            msgs.TEXT_DRIFT.format(
                site_id=failure["site_id"],
                expected=failure.get("expected", ""),
                actual=_pick_text_drift_actual(failure),
            ),
        )
    diagnostics.append(msgs.VALIDATION_FAILED.format(site_id=failure["site_id"]))


def combined_sha(parts: list[str]) -> str:
    """Combine per-site diff shas into one sha; empty when ``parts`` is empty."""
    if not parts:
        return ""
    joined = b"".join(part.encode("ascii") for part in parts)
    return _diff_sha(joined, b"")
