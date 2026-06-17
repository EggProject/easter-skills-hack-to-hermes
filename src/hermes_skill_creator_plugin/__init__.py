"""hermes-skill-creator-plugin: advisory-only cap-state detector.

The plugin emits a ONE-TIME bilingual advisory at session start if the
60-char skill-description cap is detected (via static AST read of the
operator's Hermes checkout) as still 60.

Hard rules:
  - NEVER writes to ~/.hermes/hermes-agent.
  - NEVER calls setattr on any Hermes module.
  - NEVER calls ctx.register_skill (the migrated skill is shipped standalone
    via Script #2's flat-path do_install into ~/.hermes/skills/skill-creator/).

TDD test cases for this module:
    test_register_calls_ctx_register_hook_once
    test_register_does_not_call_ctx_register_skill
    test_register_silent_when_cap_patched
    test_register_emits_advisory_when_cap_unpatched
    test_register_silent_when_target_unknown
    test_register_silent_when_marker_already_seen
    test_register_warns_when_hermes_home_unset
    test_register_callable_in_package_init

See also: docs/plans/03-plugin-spec.md
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

from ._advisory import (
    detect_cap_state,
    emit_advisory,
    resolve_target_dir,
    should_emit_advisory,
)
from .i18n.messages_en import ADVISORY_CAP_EN
from .i18n.messages_hu import ADVISORY_CAP_HU


class _PluginCtx(Protocol):
    """Minimal ctx shape used by this plugin (duck-typed; no hermes_cli import)."""

    def register_hook(self, hook_name: str, callback: Any) -> None: ...
    def log(self, message: str) -> None: ...


_ADVISORY_MARKER_FILENAME = ".hermes_skill_creator_advisory_seen"


def register(ctx: _PluginCtx) -> None:
    """Single entry point invoked by hermes_cli.plugins at plugin load.

    Detects the cap state, emits a one-time bilingual advisory via ctx.log,
    and wires the on_session_start hook for downstream consumers.

    Per the Phase 5 safety contract: NEVER writes to HERMES_HOME except for
    the best-effort, idempotent marker file under $HERMES_HOME. NEVER calls
    ctx.register_skill. NEVER calls setattr on any Hermes module.
    """
    target = resolve_target_dir()
    state = detect_cap_state(target)
    if state != "unpatched":
        ctx.register_hook("on_session_start", _on_session_start)
        return

    hermes_home_env = os.environ.get("HERMES_HOME")
    if not hermes_home_env:
        # No HERMES_HOME => no marker path => cannot implement one-time
        # semantics. Stay silent rather than guessing the live install path.
        ctx.register_hook("on_session_start", _on_session_start)
        return
    advisory_marker = Path(hermes_home_env) / _ADVISORY_MARKER_FILENAME
    if should_emit_advisory(advisory_marker):
        ctx.log(f"{ADVISORY_CAP_EN} / {ADVISORY_CAP_HU}")
        emit_advisory(advisory_marker)

    ctx.register_hook("on_session_start", _on_session_start)


def _on_session_start() -> None:
    """The on_session_start hook callback. No-op; the one-time advisory is
    already emitted at register() time (the marker enforces one-time)."""


__all__ = ["register"]
