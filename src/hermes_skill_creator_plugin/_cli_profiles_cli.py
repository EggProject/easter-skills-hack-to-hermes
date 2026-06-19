"""Click CLI surface for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference ``hermes_skill_creator_plugin.cli_profiles.app`` /
``make_cli()`` / ``_build_help_text``; ``cli_profiles.py`` re-exports
them so existing imports continue to work.
"""

from __future__ import annotations

import dataclasses
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


def _build_en_help() -> str:
    """Build the English --help text body."""
    return (
        f"{EN['profiles_help_short']}\n\n"
        f"{HELP_EN_HEADER}\n"
        f"{EN_USAGE_BAR}\n\n"
        f"{EN['profiles_help_long']}\n\n"
        f"{EN_SECTION}\n"
        f"  --apply            {EN['profiles_opt_apply']}\n"
        f"  --audit            {EN['profiles_opt_audit']}\n"
        f"  --profile NAME     {EN['profiles_opt_profile']}\n"
        f"  --json PATH        {EN['profiles_opt_json']}\n"
        f"  --yes              {EN['profiles_opt_yes']}\n"
        f"  --skip-install     {EN['profiles_opt_skip_install']}\n"
        f"  --frozen-time ISO  {EN['profiles_opt_frozen_time']}\n"
        f"  --help             {EN['profiles_opt_help']}\n"
    )


def _build_hu_help() -> str:
    """Build the Hungarian --help text body."""
    return (
        f"{HU['profiles_help_short']}\n\n"
        f"{HELP_HU_HEADER}\n"
        f"{HU_USAGE_BAR}\n\n"
        f"{HU['profiles_help_long']}\n\n"
        f"{HU_SECTION}\n"
        f"  --apply            {HU['profiles_opt_apply']}\n"
        f"  --profile NÉV      {HU['profiles_opt_profile']}\n"
        f"  --json ÚTVONAL     {HU['profiles_opt_json']}\n"
        f"  --yes              {HU['profiles_opt_yes']}\n"
        f"  --skip-install     {HU['profiles_opt_skip_install']}\n"
        f"  --frozen-time ISO  {HU['profiles_opt_frozen_time']}\n"
        f"  --help             {HU['profiles_opt_help']}\n"
    )


def build_help_text() -> str:
    """Build the bilingual --help text (two mirrored sections)."""
    return _build_en_help() + "\n" + _build_hu_help()


@dataclasses.dataclass(frozen=True)
class _ProfilesCmdArgs:
    """Parsed CLI args for :func:`main_cmd` (bundled for WPS211)."""

    apply: bool
    audit_only: bool
    profile: str | None
    json_path: str | None
    yes: bool
    skip_install: bool
    frozen_time: str | None


def _run_profiles_cmd(args: _ProfilesCmdArgs) -> None:
    """Internal: dispatch :class:`_ProfilesCmdArgs` into ``run_audit``."""
    from hermes_skill_creator_plugin.cli_profiles import run_audit

    effective_apply = args.apply and not args.audit_only
    resolved_json: Path | None = Path(args.json_path) if args.json_path else None
    run_audit(
        apply=effective_apply,
        json_path=resolved_json,
        frozen_time=args.frozen_time,
        skip_install=args.skip_install,
        yes=args.yes,
        profile=args.profile,
    )


@click.pass_context
def main_cmd(ctx: click.Context, /, **_kwargs: object) -> None:
    """Per-profile audit/flip (Script #2). Options are read from ``ctx.params``."""
    opts = ctx.params
    _run_profiles_cmd(
        _ProfilesCmdArgs(
            apply=bool(opts.get("apply", False)),
            audit_only=bool(opts.get("audit_only", False)),
            profile=opts.get("profile"),
            json_path=opts.get("json_path"),
            yes=bool(opts.get("yes", False)),
            skip_install=bool(opts.get("skip_install", False)),
            frozen_time=opts.get("frozen_time"),
        ),
    )


# Apply click options to ``main_cmd`` directly (the entry-point contract).
main_cmd = click.command(
    help=build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)(main_cmd)
main_cmd = click.option(
    "--apply",
    "apply",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_apply"],
)(main_cmd)
main_cmd = click.option(
    "--audit",
    "audit_only",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_audit"],
)(main_cmd)
main_cmd = click.option(
    "--profile",
    "profile",
    default=None,
    help=EN["profiles_opt_profile"],
)(main_cmd)
main_cmd = click.option(
    "--json",
    "json_path",
    default=None,
    type=click.Path(),
    help=EN["profiles_opt_json"],
)(main_cmd)
main_cmd = click.option(
    "--yes",
    "yes",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_yes"],
)(main_cmd)
main_cmd = click.option(
    "--skip-install",
    "skip_install",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_skip_install"],
)(main_cmd)
main_cmd = click.option(
    "--frozen-time",
    "frozen_time",
    default=None,
    envvar="HERMES_SKILL_CREATOR_FROZEN_TIME",
    help=EN["profiles_opt_frozen_time"],
)(main_cmd)


def make_cli() -> Any:
    """Return a ``click.testing.CliRunner`` for tests."""
    from click.testing import CliRunner

    return CliRunner()
