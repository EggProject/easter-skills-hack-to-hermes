"""Profile-selection + live-install refusal helpers for cli_profiles.

Split from ``cli_profiles`` (WPS202 module surface budget). The
``_select_profiles`` filter and the ``_live_install_refused`` safety
gate live here so the orchestrator stays under the module surface cap.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

LIVE_HERMES_HOME = Path.home() / ".hermes"


def _select_profiles(
    all_profiles: list[Any],
    profile: str | None,
) -> list[Any]:
    """Filter all_profiles to the requested NAME (or return them all)."""
    if profile is None:
        return list(all_profiles)
    return [profile_info for profile_info in all_profiles if profile_info.name == profile]


def _live_install_refused(apply: bool, yes: bool) -> bool:
    """Return True when the run should refuse to write the LIVE install."""
    if not apply or yes:
        return False
    env = os.environ.get("HERMES_HOME")
    if env is None:
        return False
    return Path(env).resolve() == LIVE_HERMES_HOME.resolve()
