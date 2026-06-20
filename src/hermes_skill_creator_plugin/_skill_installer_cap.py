"""Skill installer active-cap detection (60 vs MAX_DESCRIPTION_LENGTH).

Extracted from :mod:`.skill_installer` to keep the installer under
wemake WPS202 (module members <= 7).

Detects whether the active Hermes checkout has the cap-raise patch by
reading ``extract_skill_description`` in ``agent/skill_utils.py`` via a
static AST-text scan (no execution). Returns ``"patched"`` when the
literal ``60`` is replaced by ``MAX_DESCRIPTION_LENGTH``, else
``"unpatched"``.
"""

from __future__ import annotations

from pathlib import Path

from hermes_skill_creator_plugin._skill_installer_consts import (
    LIVE_HERMES_AGENT,
    PATCHED_MARKER,
    SKILL_UTILS_REL_PARTS,
    STATE_PATCHED,
    STATE_UNPATCHED,
    TEXT_ENCODING,
    UNPATCHED_MARKER,
)


def detect_active_cap(checkout: Path | None = None) -> str:
    """Detect the active cap (60 vs MAX_DESCRIPTION_LENGTH) in agent/skill_utils.py.

    Reads ``extract_skill_description`` in the active checkout (or
    ``~/.hermes/hermes-agent`` if ``checkout`` is None and the env var
    ``HERMES_HERMES_AGENT_TARGET`` is unset). Returns ``"patched"`` if
    the literal ``60`` is replaced by ``MAX_DESCRIPTION_LENGTH``, else
    ``"unpatched"``.

    Raises:
        FileNotFoundError: if the active checkout's
            ``agent/skill_utils.py`` is not present.
    """
    target = checkout or LIVE_HERMES_AGENT
    src = target.joinpath(*SKILL_UTILS_REL_PARTS)
    if not src.exists():
        message = f"agent/skill_utils.py not found in {target}"
        raise FileNotFoundError(message)
    text = src.read_text(encoding=TEXT_ENCODING)
    is_patched = PATCHED_MARKER in text and UNPATCHED_MARKER not in text
    return STATE_PATCHED if is_patched else STATE_UNPATCHED
