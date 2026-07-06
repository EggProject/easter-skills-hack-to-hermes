"""Constants for the WOW skill reminder hook config."""

from __future__ import annotations

PLUGIN_ID = "easter-hermes-sorry-skills-plugin"
ENV_LOG_LEVEL = "EASTER_HERMES_SORRY_SKILLS_LOG_LEVEL"
MODE_OFF = "off"
MODE_ADAPTIVE = "adaptive"
MODE_FIRST = "first"
OUTPUT_SHORTLIST = "shortlist"
OUTPUT_NAMES = "names"
OUTPUT_INDEX = "index"
DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 2
DEFAULT_LOG_LEVEL = "INFO"
VALID_MODES = frozenset((MODE_OFF, MODE_ADAPTIVE, MODE_FIRST))
VALID_OUTPUTS = frozenset((OUTPUT_SHORTLIST, OUTPUT_NAMES, OUTPUT_INDEX))
VALID_LOG_LEVELS = frozenset(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
