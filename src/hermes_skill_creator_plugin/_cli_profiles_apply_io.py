"""Install / cache-clear helpers for ``_cli_profiles_apply``.

Extracted from :mod:`._cli_profiles_apply` to keep the parent module under
wemake WPS202 (module members <= 7).
"""

from __future__ import annotations

from typing import Any

import click

from hermes_skill_creator_plugin._cli_profiles_diff import DESIRED_SKILL


def apply_do_install(
    do_install: Any,
    row: dict[str, Any],
    actions: list[str],
    errors: list[str],
    bilingual_fn: Any,
) -> None:
    """Install (or refresh) the migrated skill-creator via the hub."""
    try:
        do_install(
            DESIRED_SKILL,
            category="",
            force=True,
            console=None,
            skip_confirm=True,
            invalidate_cache=True,
            name_override="",
        )
    except Exception as exc:
        msg = bilingual_fn(
            "profiles_msg_hub_error",
            name=row["profile_name"],
            err=exc,
        )
        click.echo(msg)
        errors.append(f"hub install failed: {exc}")
        return
    actions.append("do_install")


def apply_clear_cache(
    clear_skills_system_prompt_cache: Any,
    row: dict[str, Any],
    actions: list[str],
    errors: list[str],
    bilingual_fn: Any,
) -> None:
    """Clear the system-prompt cache (warn-and-continue on failure)."""
    try:
        clear_skills_system_prompt_cache(clear_snapshot=True)
    except Exception as exc:
        msg = bilingual_fn(
            "profiles_msg_cache_warn",
            name=row["profile_name"],
            err=exc,
        )
        click.echo(msg)
        errors.append(f"cache clear failed: {exc}")
        return
    actions.append("clear_skills_system_prompt_cache")
