"""ISO-8601 UTC timestamp helper for the patcher.

Split from ``_patcher_helpers`` (WPS202 module surface budget). Honors
``HERMES_SKILL_CREATOR_FROZEN_TIME`` for deterministic tests.
"""

from __future__ import annotations

import datetime as _datetime
import os

FROZEN_TIME_ENV_KEY = "HERMES_SKILL_CREATOR_FROZEN_TIME"


def now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get(FROZEN_TIME_ENV_KEY)
    if frozen:
        return frozen
    return _datetime.datetime.now(_datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
