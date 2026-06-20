"""Advisory emission + target resolution helpers.

Split from ``_advisory`` (WPS202 module surface budget).
"""

from __future__ import annotations

import os
from pathlib import Path

from hermes_skill_creator_plugin._advisory_consts import (
    _DEFAULT_TARGET_SUFFIX,
    _MARKER_PAYLOAD,
    _TARGET_ENV_KEY,
)


def resolve_target_dir() -> Path:
    """Return the Hermes checkout to inspect.

    Honors HERMES_HERMES_AGENT_TARGET (set by Script #1 + CI). Falls back
    to ~/.hermes/hermes-agent ONLY in interactive operator use; CI must
    always set the env var to avoid the live read.
    """
    env = os.environ.get(_TARGET_ENV_KEY)
    if env:
        return Path(env)
    return Path(os.path.expanduser(_DEFAULT_TARGET_SUFFIX))


def should_emit_advisory(advisory_marker: Path) -> bool:
    """Return True iff the advisory marker is absent (one-time semantics)."""
    return not advisory_marker.exists()


def emit_advisory(advisory_marker: Path) -> None:
    """Best-effort write of the one-time marker. Never raises."""
    try:
        advisory_marker.write_text(_MARKER_PAYLOAD, encoding="utf-8")
    except OSError:
        # Best-effort: the marker is advisory, not a hard contract.
        return
