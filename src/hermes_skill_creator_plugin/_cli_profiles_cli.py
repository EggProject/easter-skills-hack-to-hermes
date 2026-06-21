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
    r"""Format a single ``  FLAG  description\n`` option line."""
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


def _bool_flag(cmd: click.Command, flag: str, dest: str, help_key: str) -> click.Command:
    """Apply one boolean ``click.option``."""
    help_text = EN[help_key]
    return click.option(flag, dest, is_flag=True, default=False, help=help_text)(cmd)


def _value_flag(cmd: click.Command, flag: str, dest: str, help_key: str, **extras: object) -> click.Command:
    """Apply one value-bearing ``click.option``."""
    help_text = EN[help_key]
    type_arg = extras.pop("type", None)
    envvar = extras.pop("envvar", None)
    return click.option(
        flag,
        dest,
        default=None,
        type=type_arg,
        envvar=envvar,
        help=help_text,
    )(cmd)


def _with_misc_flags(cmd: click.Command) -> click.Command:
    """Apply the four boolean flags: --apply / --audit / --yes / --skip-install."""
    cmd = _bool_flag(cmd, "--apply", "apply", "profiles_opt_apply")
    cmd = _bool_flag(cmd, "--audit", "audit_only", "profiles_opt_audit")
    cmd = _bool_flag(cmd, "--yes", "yes", "profiles_opt_yes")
    cmd = _bool_flag(cmd, "--skip-install", "skip_install", "profiles_opt_skip_install")
    return cmd


def _with_path_and_time_flags(cmd: click.Command) -> click.Command:
    """Apply the three value flags: --profile / --json / --frozen-time."""
    cmd = _value_flag(cmd, "--profile", "profile", "profiles_opt_profile")
    cmd = _value_flag(cmd, "--json", "json_path", "profiles_opt_json", type=click.Path())
    cmd = _value_flag(
        cmd,
        "--frozen-time",
        "frozen_time",
        "profiles_opt_frozen_time",
        envvar="HERMES_SKILL_CREATOR_FROZEN_TIME",
    )
    return cmd


@click.command(
    help=build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def main_cmd(ctx: click.Context, /, **kwargs: bool | str | None) -> None:
    """Per-profile audit/flip for the migrated skill-creator skill (Script #2)."""
    from hermes_skill_creator_plugin.cli_profiles import run_audit

    apply_flag = bool(kwargs.get("apply", False))
    audit_only = bool(kwargs.get("audit_only", False))
    effective_apply = apply_flag and not audit_only
    json_path = kwargs.get("json_path")
    resolved_json: Path | None = Path(json_path) if isinstance(json_path, str) else None
    run_audit(
        apply=effective_apply,
        json_path=resolved_json,
        frozen_time=kwargs.get("frozen_time"),
        skip_install=bool(kwargs.get("skip_install", False)),
        yes=bool(kwargs.get("yes", False)),
        profile=kwargs.get("profile"),
    )


# Apply the seven ``click.option`` decorators via wrapper helpers
# so the function itself only has two decorators (``@click.command`` +
# ``@click.pass_context``) — keeps the WPS216 cap of 5 happy.
main_cmd = _with_misc_flags(main_cmd)
main_cmd = _with_path_and_time_flags(main_cmd)


def make_cli() -> Any:
    """Return a ``click.testing.CliRunner`` for tests."""
    from click.testing import CliRunner

    return CliRunner()
