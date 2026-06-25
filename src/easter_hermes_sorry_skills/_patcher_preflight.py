"""Patcher preflight: refuse rules before any file is touched.

Extracted from :mod:`._patcher` to keep the orchestrator under
wemake WPS202 (module members <= 7).

The preflight encodes the three refusal rules:

1. No ``--target`` provided -> exit code 4 (``EXIT_IO``).
2. Target resolves to ``~/.hermes/hermes-agent`` -> exit code 4
   (bilingual diagnostic, see ``TARGET_IS_HERMES_AGENT``).
3. ``agent/skill_utils.py`` missing under the target -> exit code 4.
"""

from __future__ import annotations

from pathlib import Path

from easter_hermes_sorry_skills._patcher_consts import (
    EXIT_IO,
)
from easter_hermes_sorry_skills._patcher_helpers import is_hermes_agent
from easter_hermes_sorry_skills._patcher_sites import TOOLS_SKILL_UTILS_REL
from easter_hermes_sorry_skills.i18n.messages_en import (
    TARGET_IS_HERMES_AGENT,
    TARGET_MISSING_SKILL_UTILS,
    TARGET_REQUIRED,
)


def run_preflight(
    target: Path | None,
) -> tuple[int, str] | None:
    """Return ``(exit_code, diagnostic)`` on failure, ``None`` to continue.

    Encodes the refusal rules: no target, target is the hermes-agent
    checkout, missing skill_utils.
    """
    if target is None:
        return (EXIT_IO, TARGET_REQUIRED)
    target_path = Path(target).resolve()
    if is_hermes_agent(target_path):
        msg = TARGET_IS_HERMES_AGENT.format(resolved=str(target_path))
        return (EXIT_IO, msg)
    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not skill_utils.exists():
        msg = TARGET_MISSING_SKILL_UTILS.format(path=str(skill_utils))
        return (EXIT_IO, msg)
    return None
