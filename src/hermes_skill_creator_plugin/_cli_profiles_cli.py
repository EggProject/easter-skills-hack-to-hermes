"""Click CLI surface for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference ``hermes_skill_creator_plugin.cli_profiles.app`` /
``make_cli()`` / ``_build_help_text``; ``cli_profiles.py`` re-exports
them so existing imports continue to work.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

# Header labels for the bilingual --help sections.
HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"
EN_SECTION = "Options:"
HU_SECTION = "Kapcsolók:"
EN_USAGE_BAR = (
    "  hermes-skill-creator-profiles [--apply] [--audit] [--profile NAME]\n"
    "                                  [--json PATH] [--yes] [--skip-install]\n"
    "                                  [--frozen-time ISO] [--help]"
)
HU_USAGE_BAR = (
    "  hermes-skill-creator-profiles [--apply] [--audit] [--profile NÉV]\n"
    "                                  [--json ÚTVONAL] [--yes] [--skip-install]\n"
    "                                  [--frozen-time ISO] [--help]"
)

# (flag_label, i18n_key) pairs — kept short to keep WPS221 quiet.
_EN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply            ", "profiles_opt_apply"),
    ("--audit            ", "profiles_opt_audit"),
    ("--profile NAME     ", "profiles_opt_profile"),
    ("--json PATH        ", "profiles_opt_json"),
    ("--yes              ", "profiles_opt_yes"),
    ("--skip-install     ", "profiles_opt_skip_install"),
    ("--frozen-time ISO  ", "profiles_opt_frozen_time"),
    ("--help             ", "profiles_opt_help"),
)
_HU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply            ", "profiles_opt_apply"),
    ("--profile NÉV      ", "profiles_opt_profile"),
    ("--json ÚTVONAL     ", "profiles_opt_json"),
    ("--yes              ", "profiles_opt_yes"),
    ("--skip-install     ", "profiles_opt_skip_install"),
    ("--frozen-time ISO  ", "profiles_opt_frozen_time"),
    ("--help             ", "profiles_opt_help"),
)


def _format_options_block(
    options: tuple[tuple[str, str], ...],
    messages: Mapping[str, str],
) -> str:
    """Render an options block: ``  FLAG  description`` per line."""
    parts = [_format_option_line(flag, messages[key]) for flag, key in options]
    return "".join(parts)


def _format_option_line(flag: str, description: str) -> str:
    """Format a single ``  FLAG  description\\n`` option line."""
    return f"  {flag}{description}\n"


def _build_en_help() -> str:
    """Build the English --help text body."""
    return (
        f"{EN['profiles_help_short']}\n\n"
        f"{HELP_EN_HEADER}\n"
        f"{EN_USAGE_BAR}\n\n"
        f"{EN['profiles_help_long']}\n\n"
        f"{EN_SECTION}\n"
        f"{_format_options_block(_EN_OPTIONS, EN)}"
    )


def _build_hu_help() -> str:
    """Build the Hungarian --help text body."""
    return (
        f"{HU['profiles_help_short']}\n\n"
        f"{HELP_HU_HEADER}\n"
        f"{HU_USAGE_BAR}\n\n"
        f"{HU['profiles_help_long']}\n\n"
        f"{HU_SECTION}\n"
        f"{_format_options_block(_HU_OPTIONS, HU)}"
    )


_HELP_SECTION_SEP = "\n"


def build_help_text() -> str:
    """Build the bilingual --help text (two mirrored sections)."""
    return f"{_build_en_help()}{_HELP_SECTION_SEP}{_build_hu_help()}"


@click.command(
    help=build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--apply",
    "apply",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_apply"],
)
@click.option(
    "--audit",
    "audit_only",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_audit"],
)
@click.option(
    "--profile",
    "profile",
    default=None,
    help=EN["profiles_opt_profile"],
)
@click.option(
    "--json",
    "json_path",
    default=None,
    type=click.Path(),
    help=EN["profiles_opt_json"],
)
@click.option(
    "--yes",
    "yes",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_yes"],
)
@click.option(
    "--skip-install",
    "skip_install",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_skip_install"],
)
@click.option(
    "--frozen-time",
    "frozen_time",
    default=None,
    envvar="HERMES_SKILL_CREATOR_FROZEN_TIME",
    help=EN["profiles_opt_frozen_time"],
)
def main_cmd(
    apply: bool,
    audit_only: bool,
    profile: str | None,
    json_path: str | None,
    yes: bool,
    skip_install: bool,
    frozen_time: str | None,
) -> None:
    """Per-profile audit/flip for the migrated skill-creator skill (Script #2)."""
    from hermes_skill_creator_plugin.cli_profiles import run_audit

    effective_apply = apply and not audit_only
    resolved_json: Path | None = Path(json_path) if json_path else None
    run_audit(
        apply=effective_apply,
        json_path=resolved_json,
        frozen_time=frozen_time,
        skip_install=skip_install,
        yes=yes,
        profile=profile,
    )


def make_cli() -> Any:
    """Return a ``click.testing.CliRunner`` for tests."""
    from click.testing import CliRunner

    return CliRunner()
