"""Normalization helpers for the WOW skill reminder hook config."""

from __future__ import annotations

import os

from easter_hermes_sorry_skills._skill_hook_config_consts import (
    DEFAULT_LOG_LEVEL,
    ENV_LOG_LEVEL,
    VALID_LOG_LEVELS,
)


def as_bool(raw_value: object, *, default: bool) -> bool:
    """Normalize bool-like config values."""
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def choice(raw_value: object, allowed: frozenset[str], default: str) -> str:
    """Normalize a string choice."""
    if not isinstance(raw_value, str):
        return default
    normalized = raw_value.strip().lower()
    return normalized if normalized in allowed else default


def positive_int(raw_value: object, default: int) -> int:
    """Normalize positive integer config values."""
    normalized = _int_or_none(raw_value)
    if normalized is None or normalized < 1:
        return default
    return normalized


def non_negative_int(raw_value: object, default: int) -> int:
    """Normalize non-negative integer config values."""
    normalized = _int_or_none(raw_value)
    if normalized is None or normalized < 0:
        return default
    return normalized


def log_level(raw_value: object) -> str:
    """Normalize log level with env override."""
    env_value = os.environ.get(ENV_LOG_LEVEL)
    if env_value:
        return _log_level_choice(env_value)
    return _log_level_choice(raw_value)


def _int_or_none(raw_value: object) -> int | None:
    """Return an int for integer-like values."""
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str) and raw_value.strip().isdigit():
        return int(raw_value.strip())
    return None


def _log_level_choice(raw_value: object) -> str:
    """Normalize an uppercase logging level choice."""
    if not isinstance(raw_value, str):
        return DEFAULT_LOG_LEVEL
    normalized = raw_value.strip().upper()
    return normalized if normalized in VALID_LOG_LEVELS else DEFAULT_LOG_LEVEL
