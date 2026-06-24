"""Dataclass types for the ``_cli_profiles_audit`` apply pipeline.

Moved out of ``_cli_profiles_audit`` to keep that orchestrator under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class _ApplyDeps:
    """Lazily-bound callables captured inside ``hermes_home_scope``."""

    save_disabled_skills: Any
    save_config: Any
    do_install: Any
    clear_skills_system_prompt_cache: Any
    bilingual_fn: Any


@dataclasses.dataclass(frozen=True)
class _ApplyCallArgs:
    """Per-profile args for the apply pipeline (bundled to stay under WPS211)."""

    config: Any
    disabled_now: set[str]
    row: dict[str, Any]
    actions: list[str]
    errors: list[str]
    profile_path: Any
    bilingual_fn: Any


@dataclasses.dataclass(frozen=True)
class _ApplySlot:
    """Per-profile mutable row + action log + error log (bundled for WPS211)."""

    row: dict[str, Any]
    actions: list[str]
    errors: list[str]
