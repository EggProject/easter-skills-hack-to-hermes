"""Pin values + sentinel states + AST-walk markers for advisory cap-state.

Split from ``_advisory`` (WPS202 module surface budget).
"""

from __future__ import annotations

# Pin: the cap value in the unpatched agent/skill_utils.py.
UNPATCHED_CAP = 60
# Pin: the constant the patched function uses.
PATCHED_CAP_REFERENCE = "MAX_DESCRIPTION_LENGTH"
# Sentinel return values (public so register() can compare without importing
# leading-underscore names from another module).
PATCHED_STATE = "patched"
UNPATCHED_STATE = "unpatched"
UNKNOWN_STATE = "unknown"

# Target function whose Compare nodes carry the cap marker.
_EXTRACT_FUNC_NAME = "extract_skill_description"
_TARGET_ENV_KEY = "HERMES_HERMES_AGENT_TARGET"
_DEFAULT_TARGET_SUFFIX = "~/.hermes/hermes-agent"
_SKILL_UTILS_REL_PARTS = ("agent", "skill_utils.py")
_MARKER_PAYLOAD = "advisory shown\n"
