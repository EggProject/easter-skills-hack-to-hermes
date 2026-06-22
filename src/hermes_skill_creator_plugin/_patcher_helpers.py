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
import subprocess
import sys
from pathlib import Path

from hermes_skill_creator_plugin._patcher_helpers_fs import cross_filesystem as _cross_filesystem
from hermes_skill_creator_plugin._patcher_helpers_locate import locate_anchor as _locate_anchor
from hermes_skill_creator_plugin._patcher_sites import Site

# Re-export so existing ``from _patcher_helpers import cross_filesystem``
# keeps working after the WPS202 split.
cross_filesystem = _cross_filesystem

# Re-export so existing ``from _patcher_helpers import locate_anchor``
# keeps working after the multi-line anchor split.
locate_anchor = _locate_anchor

DEFAULT_CYCLE_MARKER = "from tools.skills_tool import"
FROZEN_TIME_ENV_KEY = "HERMES_SKILL_CREATOR_FROZEN_TIME"
HOME_DIR_PARTS = (".hermes", "hermes-agent")
_SUBPROCESS_IMPORT_TIMEOUT_SEC = 5


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
    """True iff importing ``tools.skills_tool`` from this checkout would cycle.

    The pre-flight rejects the import strategy for
    ``MAX_DESCRIPTION_LENGTH`` when ``tools.skills_tool`` exists in the
    target checkout and the live ``import tools.skills_tool`` fails in a
    subprocess (the cycle risk is real because a real Python process
    was unable to resolve the module from the target cwd). The fallback
    is a local constant ``_MAX_DESCRIPTION_LENGTH = 1024``.

    The subprocess check replaces the previous string-grep approach
    (which only checked whether ``agent/skill_utils.py`` already
    contained a literal ``from tools.skills_tool import`` line). The
    subprocess is only invoked when ``tools/skills_tool.py`` actually
    exists in the target checkout so missing-module errors do NOT
    produce a false-positive cycle detection.
    """
    if not skill_utils_path.exists():
        return False
    text = skill_utils_path.read_text(encoding="utf-8", errors="replace")
    if cycle_marker in text:
        return True
    target_dir = skill_utils_path.parent.parent
    target_tools_skill = target_dir / "tools" / "skills_tool.py"
    if not target_tools_skill.exists():
        return False
    try:
        completed = subprocess.run(
            [sys.executable, "-c", "import tools.skills_tool"],
            cwd=str(target_dir),
            check=False,
            capture_output=True,
            timeout=_SUBPROCESS_IMPORT_TIMEOUT_SEC,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return completed.returncode != 0


def site_already_patched(text: str, site: Site) -> bool:
    """True iff the site's ``expected_replacement`` is present in ``text``."""
    return site.expected_replacement in text


def site_in_state(state: dict[str, str], site_id: str, *, status: str) -> bool:
    """True iff the state sidecar records ``site_id`` as ``status``."""
    return state.get(site_id) == status


def now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get(FROZEN_TIME_ENV_KEY)
    if frozen:
        return frozen
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
