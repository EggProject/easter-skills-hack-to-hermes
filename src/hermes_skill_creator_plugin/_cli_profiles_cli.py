"""Click CLI surface for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference ``hermes_skill_creator_plugin.cli_profiles.app`` /
``make_cli()`` / ``_build_help_text``; ``cli_profiles.py`` re-exports
them so existing imports continue to work.

The bilingual --help builders live in :mod:`._cli_profiles_help` (split
to keep this module under WPS202).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin._cli_profiles_help import build_help_text
from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN

__all__ = [
    "build_help_text",
    "_MainCmdInputs",
    "main_cmd",
    "make_cli",
]


@dataclasses.dataclass(frozen=True)
class _MainCmdInputs:
    """Bundle of click-injected flags (kept under WPS211 cap of 5)."""

    apply: bool
    audit_only: bool
    profile: str | None
    json_path: str | None
    yes: bool
    skip_install: bool
    frozen_time: str | None


@click.command(
    help=build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def main_cmd(ctx: click.Context) -> None:
    """Per-profile audit/flip for the migrated skill-creator skill (Script #2)."""
    opts = ctx.params
    _run_main_cmd(
        _MainCmdInputs(
            apply=bool(opts.get("apply", False)),
            audit_only=bool(opts.get("audit_only", False)),
            profile=opts.get("profile"),
            json_path=opts.get("json_path"),
            yes=bool(opts.get("yes", False)),
            skip_install=bool(opts.get("skip_install", False)),
            frozen_time=opts.get("frozen_time"),
        ),
    )


# Apply options to main_cmd directly (click option-decorator pattern).
main_cmd = click.option(
    "--frozen-time",
    "frozen_time",
    default=None,
    envvar="HERMES_SKILL_CREATOR_FROZEN_TIME",
    help=EN["profiles_opt_frozen_time"],
)(main_cmd)
main_cmd = click.option(
    "--skip-install",
    "skip_install",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_skip_install"],
)(main_cmd)
main_cmd = click.option(
    "--yes",
    "yes",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_yes"],
)(main_cmd)
main_cmd = click.option(
    "--json",
    "json_path",
    default=None,
    type=click.Path(),
    help=EN["profiles_opt_json"],
)(main_cmd)
main_cmd = click.option(
    "--profile",
    "profile",
    default=None,
    help=EN["profiles_opt_profile"],
)(main_cmd)
main_cmd = click.option(
    "--audit",
    "audit_only",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_audit"],
)(main_cmd)
main_cmd = click.option(
    "--apply",
    "apply",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_apply"],
)(main_cmd)


def _run_main_cmd(inputs: _MainCmdInputs) -> None:
    """Forward the click-injected flags to the programmatic run_audit entry."""
    from hermes_skill_creator_plugin.cli_profiles import run_audit

    effective_apply = inputs.apply and not inputs.audit_only
    resolved_json: Path | None = Path(inputs.json_path) if inputs.json_path else None
    run_audit(
        apply=effective_apply,
        json_path=resolved_json,
        frozen_time=inputs.frozen_time,
        skip_install=inputs.skip_install,
        yes=inputs.yes,
        profile=inputs.profile,
    )


def make_cli() -> Any:
    """Return a ``click.testing.CliRunner`` for tests."""
    from click.testing import CliRunner

    return CliRunner()
