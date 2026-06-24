"""Click option-decoration helpers for the profiles CLI surface.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). Help-text rendering lives in
``_cli_profiles_cli_help``; the constants live in
``_cli_profiles_cli_options`` / ``_cli_profiles_cli_flags``.
"""

from __future__ import annotations

import click

from easter_hermes_sorry_skills.i18n.messages_en import EN_MESSAGES as EN


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
    """Apply the one boolean flag: --dry-run."""
    cmd = _bool_flag(cmd, "--dry-run", "dry_run", "profiles_opt_dry_run")
    return cmd


def _with_profile_flag(cmd: click.Command) -> click.Command:
    """Apply the one value flag: --profile."""
    cmd = _value_flag(cmd, "--profile", "profile", "profiles_opt_profile")
    return cmd


def _with_verbose_flag(cmd: click.Command) -> click.Command:
    """Apply the boolean --verbose flag."""
    cmd = _bool_flag(cmd, "--verbose", "verbose", "profiles_opt_verbose")
    return cmd
