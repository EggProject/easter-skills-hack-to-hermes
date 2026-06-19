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
PINNED_UPSTREAM_COMMIT = "2a40fd2e7c52207aa903bd33fc4c65716126966e"
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

__all__ = [
    "KEY_ID",
    "KEY_LOCATION",
    "KEY_CLAUDE",
    "KEY_HERMES",
    "STATE_PATCHED",
    "STATE_UNPATCHED",
    "PATCHED_MARKER",
    "UNPATCHED_MARKER",
    "LIVE_HERMES_AGENT_SUFFIX",
    "PINNED_UPSTREAM_COMMIT",
    "FROZEN_TIME_ENV_KEY",
    "TEXT_ENCODING",
    "SKILL_UTILS_REL_PARTS",
    "SKILL_DEST_REL_PARTS",
    "SHORT_DESC_CAP",
    "FULL_DESC_CAP",
    "SHORT_SKILL_MD_NAME",
    "FULL_SKILL_MD_NAME",
    "MIGRATION_NOTE_NAME",
    "LIVE_HERMES_AGENT",
]
