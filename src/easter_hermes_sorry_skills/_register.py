"""Hermes plugin entry point: ``register(ctx, lang)``.

Implements the single ``register(ctx, lang)`` callable discovered by
``hermes_cli.plugins`` at plugin load. The body performs the
static-AST cap-state check synchronously and, when the cap is still
un-raised, emits the single-language advisory via ``pick(lang).ADVISORY_CAP``
EVERY call (no marker-file gating, no one-time semantics). It also
registers the ``on_session_start`` hook (whose body is a no-op at
runtime — the work is done at load time).

The plugin does NOT call ``ctx.register_skill`` (the skill is shipped
standalone via Script #2's flat-path install) and NEVER performs
``setattr`` on any Hermes module.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from easter_hermes_sorry_skills._advisory import (
    UNPATCHED_STATE,
    detect_cap_state,
    resolve_target_dir,
)
from easter_hermes_sorry_skills._i18n_pick import pick


def _advisory_callback(_ctx: object) -> None:
    """Hook body for the ``on_session_start`` event.

    The work is performed synchronously by :func:`register`; this
    callback is a no-op (it exists so the plugin can advertise the
    ``on_session_start`` capability on the manifest).
    """


def register(ctx: Any, lang: str = "en") -> None:
    """Single entry point invoked by ``hermes_cli.plugins`` at plugin load.

    Performs the static-AST cap-state check synchronously and, when the
    cap is still un-raised, emits ``pick(lang).ADVISORY_CAP`` (PLAIN
    english or PLAIN hungarian, no bilingual ``[en] ... / [hu] ...`` format)
    EVERY call. Registers the ``on_session_start`` hook (a no-op, the
    work is already done at load time). The plugin does NOT call
    ``ctx.register_skill`` (the skill is shipped standalone via Script
    #2's flat-path install).
    """
    target = resolve_target_dir()
    if detect_cap_state(target) == UNPATCHED_STATE:
        log: Callable[[str], object] = ctx.log
        log(pick(lang).ADVISORY_CAP)
    register_hook: Callable[[str, Callable[[object], None]], object] = ctx.register_hook
    register_hook("on_session_start", _advisory_callback)
