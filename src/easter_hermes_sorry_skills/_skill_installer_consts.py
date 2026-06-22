"""Skill installer constants (keys, state strings, paths, env keys).

Extracted from :mod:`.skill_installer` to keep the installer under
wemake WPS202 (module members <= 7). All names are re-exported from
:mod:`.skill_installer` so existing imports keep working.
"""

from __future__ import annotations

from pathlib import Path

# --- row builder keys -----------------------------------------------------
KEY_ID = "id"
KEY_LOCATION = "location"
KEY_CLAUDE = "claude"
KEY_HERMES = "hermes"

# --- cap-state strings ----------------------------------------------------
STATE_PATCHED = "patched"
STATE_UNPATCHED = "unpatched"

# --- static-AST detection markers (agent/skill_utils.py) ------------------
PATCHED_MARKER = "MAX_DESCRIPTION_LENGTH"
UNPATCHED_MARKER = "if len(desc) > 60:"

# --- path / env constants -------------------------------------------------
LIVE_HERMES_AGENT_SUFFIX = "~/.hermes/hermes-agent"
_UPSTREAM_COMMIT_REL_PARTS = (
    "docs",
    "research",
    "anthropic-skill-creator-original",
    "UPSTREAM_COMMIT.txt",
)
_UPSTREAM_COMMIT_FILE = (
    Path(__file__)
    .resolve()
    .parents[2]
    .joinpath(
        *_UPSTREAM_COMMIT_REL_PARTS,
    )
)


def _load_pinned_upstream_commit() -> str:
    """Read the pinned upstream commit SHA from UPSTREAM_COMMIT.txt.

    The file is a single line containing the 40-char hex SHA. Strips
    whitespace so trailing newlines / CRLF do not corrupt the emitted
    markdown table cell.
    """
    return _UPSTREAM_COMMIT_FILE.read_text(encoding="utf-8").strip()


PINNED_UPSTREAM_COMMIT = _load_pinned_upstream_commit()
FROZEN_TIME_ENV_KEY = "HERMES_SKILL_CREATOR_FROZEN_TIME"
TEXT_ENCODING = "utf-8"
SKILL_UTILS_REL_PARTS = ("agent", "skill_utils.py")
SKILL_DEST_REL_PARTS = ("skills", "skill-creator")
SHORT_DESC_CAP = 60
FULL_DESC_CAP = 1024
SHORT_SKILL_MD_NAME = "SKILL.md.short"
FULL_SKILL_MD_NAME = "SKILL.md"
MIGRATION_NOTE_NAME = "MIGRATION.skill-port.md"

# Live Hermes install path (resolved at import time).
LIVE_HERMES_AGENT: Path = Path(LIVE_HERMES_AGENT_SUFFIX).expanduser()
