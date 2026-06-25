"""Hermes plugin entry point: ``register(ctx)``.

Implements the single ``register(ctx)`` callable discovered by
``hermes_cli.plugins`` at plugin load. The body performs the
static-AST cap-state check synchronously and, when the cap is still
un-raised, emits the bilingual advisory exactly once per
``$HERMES_HOME``. It also registers the ``on_session_start`` hook
(whose body is a no-op at runtime — the work is done at load time).

The plugin does NOT call ``ctx.register_skill`` (the skill is shipped
standalone via Script #2's flat-path install) and NEVER performs
``setattr`` on any Hermes module.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from easter_hermes_sorry_skills._advisory import (
    UNPATCHED_STATE,
    detect_cap_state,
    emit_advisory,
    resolve_target_dir,
    should_emit_advisory,
)
from easter_hermes_sorry_skills.i18n.messages_en import ADVISORY_CAP_EN
from easter_hermes_sorry_skills.i18n.messages_hu import ADVISORY_CAP_HU

_MARKER_FILENAME = ".easter_hermes_sorry_skills_advisory_seen"


def _advisory_marker_path() -> Path:
    """Resolve the one-time advisory marker under ``$HERMES_HOME``."""
    home = os.environ.get("HERMES_HOME")
    if not home:
        # Fall back to the same default _advisory.resolve_target_dir uses
        # so the marker never collides with the operator's live install.
        home = os.path.expanduser("~/.hermes/hermes-agent")
    return Path(home) / _MARKER_FILENAME


def _advisory_callback(_ctx: object) -> None:
    """Hook body for the ``on_session_start`` event.

    The work is performed synchronously by :func:`register`; this
    callback is a no-op (it exists so the plugin can advertise the
    ``on_session_start`` capability on the manifest).
    """


def register(ctx: Any) -> None:
    """Single entry point invoked by ``hermes_cli.plugins`` at plugin load.

    Performs the static-AST cap-state check synchronously and, when the
    cap is still un-raised, emits the bilingual advisory exactly once
    per ``$HERMES_HOME``. Registers the ``on_session_start`` hook (a
    no-op, the work is already done at load time). The plugin does NOT
    call ``ctx.register_skill`` (the skill is shipped standalone via
    Script #2's flat-path install).
    """
    target = resolve_target_dir()
    if detect_cap_state(target) == UNPATCHED_STATE:
        marker = _advisory_marker_path()
        if should_emit_advisory(marker):
            log: Callable[[str], object] = ctx.log
            log(f"{ADVISORY_CAP_EN} / {ADVISORY_CAP_HU}")
            emit_advisory(marker)
    register_hook: Callable[[str, Callable[[object], None]], object] = ctx.register_hook
    register_hook("on_session_start", _advisory_callback)
