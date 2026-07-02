"""Configuration loading for the WOW skill reminder hook."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from easter_hermes_sorry_skills._skill_hook_config_consts import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_MIN_SCORE,
    DEFAULT_TOP_K,
    MODE_ADAPTIVE,
    OUTPUT_SHORTLIST,
    PLUGIN_ID,
    VALID_MODES,
    VALID_OUTPUTS,
)
from easter_hermes_sorry_skills._skill_hook_config_normalize import (
    as_bool,
    choice,
    log_level,
    non_negative_int,
    positive_int,
)


@dataclass(frozen=True)
class SkillHookConfig:
    """Normalized plugin-owned config for the skill hook."""

    enabled: bool = True
    mode: str = MODE_ADAPTIVE
    output: str = OUTPUT_SHORTLIST
    top_k: int = DEFAULT_TOP_K
    min_score: int = DEFAULT_MIN_SCORE
    log_level: str = DEFAULT_LOG_LEVEL


def load_skill_hook_config(config: dict[str, Any] | None = None) -> SkillHookConfig:
    """Load normalized hook config from Hermes config and env overrides."""
    source = config
    if source is None:
        source = _load_hermes_config()
    raw = _skill_hook_section(source)
    return SkillHookConfig(
        enabled=as_bool(raw.get("enabled"), default=True),
        mode=choice(raw.get("mode"), VALID_MODES, MODE_ADAPTIVE),
        output=choice(raw.get("output"), VALID_OUTPUTS, OUTPUT_SHORTLIST),
        top_k=positive_int(raw.get("top_k"), DEFAULT_TOP_K),
        min_score=non_negative_int(raw.get("min_score"), DEFAULT_MIN_SCORE),
        log_level=log_level(raw.get("log_level")),
    )


def _load_hermes_config() -> dict[str, Any]:
    """Read Hermes config, falling back to an empty config on failure."""
    try:
        from hermes_cli.config import load_config
    except ImportError:
        return {}
    return _call_load_config(load_config)


def _call_load_config(load_config: Callable[[], object]) -> dict[str, Any]:
    """Call Hermes config loader safely."""
    try:
        loaded = load_config()
    except (OSError, TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _skill_hook_section(config: dict[str, Any]) -> dict[str, Any]:
    """Return the plugin-owned ``skill_hook`` config section."""
    plugins = config.get("plugins")
    if not isinstance(plugins, dict):
        return {}
    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        return {}
    plugin_entry = entries.get(PLUGIN_ID)
    if not isinstance(plugin_entry, dict):
        return {}
    skill_hook = plugin_entry.get("skill_hook")
    return skill_hook if isinstance(skill_hook, dict) else {}
