"""Core audit + apply helpers for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference several private helpers from
``hermes_skill_creator_plugin.cli_profiles``; ``cli_profiles.py`` re-exports
them so existing imports continue to work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin._cli_profiles_report import AuditReport
from hermes_skill_creator_plugin._scope import hermes_home_scope

# ---------------------------------------------------------------------------
# Module-level constants (mirrored from cli_profiles.py for tests).
# ---------------------------------------------------------------------------

DESIRED_SKILL = "skill-creator"
NEVER_DISABLE = frozenset({"openai", "skills"})


# ---------------------------------------------------------------------------
# Bilingual helper.
# ---------------------------------------------------------------------------


def build_bilingual(
    en_table: Any,
    hu_table: Any,
    key: str,
    **values: Any,
) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key.

    The English half uses the ``en_table``; the Hungarian half uses
    ``hu_table``. ``values`` are substituted via ``str.format`` into both
    halves.
    """
    en_template = en_table[key]
    hu_template = hu_table[key]
    en_part = "[en] " + en_template.format(**values)
    hu_part = "[hu] " + hu_template.format(**values)
    return f"{en_part} / {hu_part}"


# ---------------------------------------------------------------------------
# Row builders.
# ---------------------------------------------------------------------------


def new_row(profile_path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    """Build the initial empty row + convenience handles for actions/errors."""
    row: dict[str, Any] = {
        "profile_name": profile_path.name or "hermes",
        "current_disabled": [],
        "current_installed": [],
        "desired_disabled": [],
        "desired_installed": [],
        "diff": {
            "added_disabled": [],
            "removed_disabled": [],
            "added_installed": [],
            "removed_installed": [],
        },
        "actions_taken": [],
        "errors": [],
    }
    return row, row["actions_taken"], row["errors"]


# ---------------------------------------------------------------------------
# Skill walking + diff.
# ---------------------------------------------------------------------------


def walk_skills(skills_dir: Path) -> set[str]:
    """Return the set of installed skill NAMES under ``skills_dir``.

    NAME comes from the SKILL.md frontmatter ``name:`` field; the
    directory name is the fallback. Directories without SKILL.md are
    ignored. The walk is robust to read errors (the skill is dropped).
    """
    from agent.skill_utils import parse_frontmatter

    if not skills_dir.is_dir():
        return set()
    out: set[str] = set()
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            fm, _body = parse_frontmatter(text)
        except Exception:
            continue
        name = fm.get("name")
        if isinstance(name, str) and name:
            out.add(name)
        else:
            out.add(child.name)
    return out


def diff_sets(current: set[str], desired: set[str]) -> dict[str, list[str]]:
    """Compute the symmetric diff between current and desired as sorted lists."""
    return {
        "added": sorted(desired - current),
        "removed": sorted(current - desired),
    }


# ---------------------------------------------------------------------------
# Apply helpers.
# ---------------------------------------------------------------------------


def load_config_or_error(
    load_config: Any, errors: list[str], row: dict[str, Any]
) -> Any:
    """Call ``load_config``; on failure record the error and return the row sentinel."""
    try:
        return load_config()
    except Exception as exc:
        errors.append(f"load_config failed: {exc}")
        return row


def read_disabled_or_empty(
    get_disabled_skill_names: Any, errors: list[str]
) -> set[str]:
    """Read the currently-disabled skill names; fall back to an empty set on error."""
    try:
        return set(get_disabled_skill_names(platform=None))
    except Exception as exc:
        errors.append(f"get_disabled_skill_names failed: {exc}")
        return set()


def populate_diff_row(
    row: dict[str, Any],
    disabled_now: set[str],
    installed_now: set[str],
) -> None:
    """Fill in current/desired/diff sub-fields on ``row``."""
    desired_disabled: set[str] = set(disabled_now) - NEVER_DISABLE
    desired_installed: set[str] = set(installed_now) | {DESIRED_SKILL}
    row["current_disabled"] = sorted(disabled_now)
    row["current_installed"] = sorted(installed_now)
    row["desired_disabled"] = sorted(desired_disabled)
    row["desired_installed"] = sorted(desired_installed)
    diff_disabled = diff_sets(disabled_now, desired_disabled)
    diff_installed = diff_sets(installed_now, desired_installed)
    row["diff"] = {
        "added_disabled": diff_disabled["added"],
        "removed_disabled": diff_disabled["removed"],
        "added_installed": diff_installed["added"],
        "removed_installed": diff_installed["removed"],
    }


def apply_save_disabled(
    save_disabled_skills: Any,
    save_config: Any,
    config: Any,
    desired_disabled: set[str],
    disabled_now: set[str],
    actions: list[str],
    errors: list[str],
) -> None:
    """Persist the desired-disabled set when it actually changes."""
    if desired_disabled == disabled_now:
        return
    try:
        save_disabled_skills(config, sorted(desired_disabled), platform=None)
    except Exception as exc:
        errors.append(f"save_disabled_skills failed: {exc}")
        return
    actions.append("save_disabled_skills")
    try:
        save_config(config)
    except Exception as exc:
        errors.append(f"save_config failed: {exc}")
        return
    actions.append("save_config")


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


def audit_profile(
    profile_path: Path,
    *,
    apply: bool,
    skip_install: bool,
    frozen_time: str | None,
    bilingual_fn: Any,
) -> dict[str, Any]:
    """Audit (and optionally apply) a single profile.

    Returns the per-profile row of the report. The call runs inside
    ``hermes_home_scope(profile_path)`` so all ``load_config`` /
    ``do_install`` / ``save_config`` calls resolve against the
    scoped HERMES_HOME (per plan 06 D4 + AC-3.4 / AC-3.6).
    """
    from agent.prompt_builder import clear_skills_system_prompt_cache
    from agent.skill_utils import get_disabled_skill_names
    from hermes_cli.config import load_config, save_config
    from hermes_cli.skills_hub import do_install

    row, actions, errors = new_row(profile_path)

    with hermes_home_scope(profile_path):
        # Look up the mutator at call time so monkeypatch.setattr on
        # the module works. The top-of-function import caches a
        # reference; the test infrastructure may rebind it.
        from hermes_cli.skills_config import save_disabled_skills

        config = load_config_or_error(load_config, errors, row)
        if config is row:
            return row

        disabled_now = read_disabled_or_empty(get_disabled_skill_names, errors)
        installed_now: set[str] = walk_skills(profile_path / "skills")
        populate_diff_row(row, disabled_now, installed_now)

        if not apply:
            return row

        apply_save_disabled(
            save_disabled_skills,
            save_config,
            config,
            set(disabled_now) - NEVER_DISABLE,
            disabled_now,
            actions,
            errors,
        )
        if not skip_install:
            apply_do_install(do_install, row, actions, errors, bilingual_fn)
        apply_clear_cache(
            clear_skills_system_prompt_cache,
            row,
            actions,
            errors,
            bilingual_fn,
        )

    return row


__all__ = [
    "AuditReport",
    "DESIRED_SKILL",
    "NEVER_DISABLE",
    "apply_clear_cache",
    "apply_do_install",
    "apply_save_disabled",
    "audit_profile",
    "build_bilingual",
    "diff_sets",
    "load_config_or_error",
    "new_row",
    "populate_diff_row",
    "read_disabled_or_empty",
    "walk_skills",
]
