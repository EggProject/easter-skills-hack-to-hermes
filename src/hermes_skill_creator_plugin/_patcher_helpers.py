"""Pure-function helpers used by the Script #1 patcher orchestrator.

These helpers are stateless (or near-stateless) and are imported by
both the orchestrator (``_patcher.py``) and the unit tests. Splitting
them out keeps the orchestrator under the 500-line hard cap
(``plans/10 D1``) while letting the unit tests import the same names
they did before the F1 split (the public API of ``_patcher.py`` still
re-exports them).

Functions:

- :func:`hermes_agent_path` / :func:`is_hermes_agent` — the no-touch
  sentinel resolver (plans/04 Safety gates + ``conftest.py``).
- :func:`file_has_circular_import` — cycle-detection pre-flight
  against ``agent/skill_utils.py`` (plans/04 D2).
- :func:`locate_anchor` — multi-signal anchor matcher; 0 means "not
  found", otherwise the 1-based line number (plans/04 D5).
- :func:`site_already_patched` / :func:`site_in_state` — idempotency
  and sidecar status lookups.
- :func:`cross_filesystem` — best-effort cross-FS detector (POSIX
  ``statvfs``; returns ``False`` on platforms without it).
- :func:`now_iso` — ISO-8601 UTC timestamp; honors
  ``HERMES_SKILL_CREATOR_FROZEN_TIME`` for deterministic tests.

See also: plans/04-script-1-patch.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import datetime
import os
import tempfile
from pathlib import Path

from hermes_skill_creator_plugin._patcher_sites import Anchor, Site

DEFAULT_CYCLE_MARKER = "from tools.skills_tool import"
FROZEN_TIME_ENV_KEY = "HERMES_SKILL_CREATOR_FROZEN_TIME"
HOME_DIR_PARTS = (".hermes", "hermes-agent")


def hermes_agent_path() -> Path:
    """Resolved path to ``~/.hermes/hermes-agent`` (the no-touch sentinel)."""
    return (Path.home().joinpath(*HOME_DIR_PARTS)).resolve()


def is_hermes_agent(target: Path) -> bool:
    """True iff ``target`` resolves to ``~/.hermes/hermes-agent``."""
    return target.resolve() == hermes_agent_path()


def file_has_circular_import(
    skill_utils_path: Path,
    *,
    cycle_marker: str = DEFAULT_CYCLE_MARKER,
) -> bool:
    """True iff the top of ``agent/skill_utils.py`` already imports from tools.

    The pre-flight rejects the import strategy for
    ``MAX_DESCRIPTION_LENGTH`` when the file already imports from
    ``tools.skills_tool`` to avoid an agent <-> tools cycle; the
    fallback is a local constant ``_MAX_DESCRIPTION_LENGTH = 1024``.
    """
    if not skill_utils_path.exists():
        return False
    text = skill_utils_path.read_text(encoding="utf-8", errors="replace")
    return cycle_marker in text


def locate_anchor(text: str, anchor: Anchor) -> int:
    """Return the 1-based line number where ``anchor.text`` appears.

    Returns 0 when the anchor is not found. Matches the FULL line bytes
    (no implicit-concat normalization).
    """
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if line == anchor.text:
            return idx
    return 0


def site_already_patched(text: str, site: Site) -> bool:
    """True iff the site's ``expected_replacement`` is present in ``text``."""
    return site.expected_replacement in text


def site_in_state(state: dict[str, str], site_id: str, *, status: str) -> bool:
    """True iff the state sidecar records ``site_id`` as ``status``."""
    return state.get(site_id) == status


def cross_filesystem(target: Path) -> bool:
    """Best-effort cross-filesystem detector.

    Returns False on platforms that do not support ``os.statvfs``.
    """
    try:
        target_stat = os.statvfs(target)
    except (OSError, AttributeError):
        return False
    try:
        tmp_stat = os.statvfs(tempfile.gettempdir())
    except (OSError, AttributeError):
        return False
    return target_stat.f_fsid != tmp_stat.f_fsid


def now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get(FROZEN_TIME_ENV_KEY)
    if frozen:
        return frozen
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "hermes_agent_path",
    "is_hermes_agent",
    "file_has_circular_import",
    "locate_anchor",
    "site_already_patched",
    "site_in_state",
    "cross_filesystem",
    "now_iso",
]
