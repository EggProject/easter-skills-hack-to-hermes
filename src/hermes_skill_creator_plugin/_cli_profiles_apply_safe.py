"""Best-effort safe wrappers for the apply pipeline.

Split from ``_cli_profiles_apply`` (WPS202 module surface budget). These
private helpers translate exceptions into ``errors.append(...)`` + False
returns so the public apply pipeline can stay flat.
"""

from __future__ import annotations

from typing import Any


def _save_disabled_skills_safe(
    save_disabled_skills: Any,
    config: Any,
    desired_disabled: set[str],
    errors: list[str],
) -> bool:
    try:
        save_disabled_skills(config, sorted(desired_disabled), platform=None)
    except Exception as exc:
        errors.append(f"save_disabled_skills failed: {exc}")
        return False
    return True


def _save_config_safe(save_config: Any, config: Any, errors: list[str]) -> bool:
    try:
        save_config(config)
    except Exception as exc:
        errors.append(f"save_config failed: {exc}")
        return False
    return True
