"""Patcher preflight: refuse rules before any file is touched.

Extracted from :mod:`._patcher` to keep the orchestrator under
wemake WPS202 (module members <= 7).

The preflight encodes the four refusal rules:

1. No ``--target`` provided -> exit code 4 (``EXIT_IO``).
2. Target resolves to ``~/.hermes/hermes-agent`` -> exit code 4
   (bilingual diagnostic, see ``TARGET_IS_HERMES_AGENT``).
3. ``agent/skill_utils.py`` missing under the target -> exit code 4.
4. ``--force`` without ``--i-accept-line-drift`` -> exit code 5
   (``EXIT_USER_ABORT``).
"""

from __future__ import annotations

from pathlib import Path

from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_IO,
    EXIT_USER_ABORT,
)
from hermes_skill_creator_plugin._patcher_helpers import is_hermes_agent
from hermes_skill_creator_plugin._patcher_sites import TOOLS_SKILL_UTILS_REL
from hermes_skill_creator_plugin.i18n.messages_en import (
    FORCE_REQUIRES_I_ACCEPT,
    TARGET_IS_HERMES_AGENT,
    TARGET_MISSING_SKILL_UTILS,
    TARGET_REQUIRED,
)


def run_preflight(
    target: Path | None,
    force: bool,
    i_accept_line_drift: bool,
) -> tuple[int, str] | None:
    """Return ``(exit_code, diagnostic)`` on failure, ``None`` to continue.

    Encodes the refusal rules: no target, target is the hermes-agent
    checkout, missing skill_utils, force without --i-accept-line-drift.
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
    if force and not i_accept_line_drift:
        return (EXIT_USER_ABORT, FORCE_REQUIRES_I_ACCEPT)
    return None


__all__ = [
    "run_preflight",
]
