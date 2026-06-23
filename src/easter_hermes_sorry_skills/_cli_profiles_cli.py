"""Click CLI surface for cli_profiles (Script #2 per-profile audit/flip).

TDD tests reference ``easter_hermes_sorry_skills.cli_profiles.app`` /
``make_cli()`` / ``_build_help_text``; ``cli_profiles.py`` re-exports
them so existing imports continue to work.

To keep this orchestrator module under wemake WPS202 (≤7 module
members), the help-text constants live in ``_cli_profiles_cli_options``
+ ``_cli_profiles_cli_flags``, the bilingual help renderer lives in
``_cli_profiles_cli_help``, and the click-option decorators live in
``_cli_profiles_cli_build``. Only ``main_cmd`` + ``make_cli`` live here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from easter_hermes_sorry_skills._cli_profiles_cli_build import (
    _with_misc_flags,
    _with_path_and_time_flags,
)
from easter_hermes_sorry_skills._cli_profiles_cli_help import build_help_text


@click.command(
    help=build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def main_cmd(ctx: click.Context, /, **kwargs: bool | str | None) -> None:
    """Per-profile audit/flip for the migrated skill-creator skill (Script #2)."""
    from easter_hermes_sorry_skills.cli_profiles import run_audit

    dry_run = bool(kwargs.get("dry_run", False))
    raw_json_path = kwargs.get("json_path")
    json_path: Path | None
    json_path = Path(raw_json_path) if isinstance(raw_json_path, str) else None
    run_audit(
        apply=not dry_run,
        profile=kwargs.get("profile"),
        json_path=json_path,
        frozen_time=kwargs.get("frozen_time"),
        skip_install=bool(kwargs.get("skip_install", False)),
        yes=bool(kwargs.get("yes", False)),
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
