"""Patcher preflight: refuse rules before any file is touched.

Extracted from :mod:`._patcher` to keep the orchestrator under
wemake WPS202 (module members <= 7).

The preflight encodes the two refusal rules:

1. No ``--target`` provided -> exit code 4 (``EXIT_IO``) with severity
   ``"error"``.
2. Target resolves to ``~/.hermes/hermes-agent`` AND ``dry_run=True`` ->
   severity ``"warning"`` with exit code ``EXIT_OK`` (soft safety — the
   patcher continues so the operator sees the planned changes before
   deciding whether to apply). Apply mode (``dry_run=False``) no
   longer refuses the live hermes-agent checkout; the operator is the
   authority on which checkout to patch.
3. ``agent/skill_utils.py`` missing under the target -> exit code 4
   (``EXIT_IO``) with severity ``"error"``.

The new :class:`PreflightOutcome` dataclass carries ``severity`` so
:func:`easter_hermes_sorry_skills._patcher_internals._check_preflight`
can branch on it: ``"error"`` short-circuits the pipeline,
``"warning"`` appends the diagnostic and lets the pipeline continue.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from easter_hermes_sorry_skills._i18n_pick import pick
from easter_hermes_sorry_skills._patcher_consts import (
    EXIT_IO,
    EXIT_OK,
)
from easter_hermes_sorry_skills._patcher_helpers import is_hermes_agent
from easter_hermes_sorry_skills._patcher_sites import TOOLS_SKILL_UTILS_REL


@dataclasses.dataclass(frozen=True)
class PreflightOutcome:
    """Outcome of :func:`run_preflight`.

    ``severity`` is ``"warning"`` (pipeline continues) or ``"error"``
    (pipeline short-circuits). ``exit_code`` is the matrix exit code
    (4 for the hard refusal rules, 0 for the soft hermes-agent warning
    under ``--dry-run``).
    """

    exit_code: int
    diagnostic: str
    severity: str


def run_preflight(
    target: Path | None,
    *,
    dry_run: bool = False,
    lang: str = "en",
) -> PreflightOutcome | None:
    """Return a :class:`PreflightOutcome` on refusal, ``None`` to continue.

    Encodes the refusal rules: no target, missing skill_utils. The
    hermes-agent rule is SOFT (severity ``"warning"``, exit_code
    ``EXIT_OK``) under ``--dry-run`` so the operator can audit the
    planned patches before applying; apply mode (``dry_run=False``) does
    NOT short-circuit on the hermes-agent target — the operator is the
    authority on which checkout to patch. The no-target and
    missing-skill-utils rules are always HARD (severity ``"error"``,
    exit_code ``EXIT_IO``).

    ``lang`` selects the single-language i18n module via
    :func:`easter_hermes_sorry_skills._i18n_pick.pick`. Defaults to
    ``"en"`` so callers that do not pass a language get English
    diagnostics.
    """
    msgs = pick(lang)
    if target is None:
        return PreflightOutcome(
            exit_code=EXIT_IO,
            diagnostic=msgs.TARGET_REQUIRED,
            severity="error",
        )
    target_path = Path(target).resolve()
    if dry_run and is_hermes_agent(target_path):
        return PreflightOutcome(
            exit_code=EXIT_OK,
            diagnostic=msgs.DRY_RUN_PREFLIGHT_WARNING,
            severity="warning",
        )
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not skill_utils.exists():
        msg = msgs.TARGET_MISSING_SKILL_UTILS.format(path=str(skill_utils))
        return PreflightOutcome(
            exit_code=EXIT_IO,
            diagnostic=msg,
            severity="error",
        )
    return None
