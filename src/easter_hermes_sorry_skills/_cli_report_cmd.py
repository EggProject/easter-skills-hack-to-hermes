"""src/easter_hermes_sorry_skills/_cli_report_cmd.py

Click command definition for the reporter CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from easter_hermes_sorry_skills._cli_report_ui import emit_bilingual_help
from easter_hermes_sorry_skills.i18n import messages_en as EN

_HELP_PARAGRAPH_SEP = "\n\n"


def _with_report_options(cmd: click.Command) -> click.Command:
    """Apply the five reporter ``click.option`` decorators as one wrapper."""
    cmd = click.option("--profile", default=None, help=EN.report_opt_profile)(cmd)
    cmd = click.option(
        "--sort",
        type=click.Choice(["tokens", "use_count", "last_used_at"]),
        default="tokens",
        help=EN.report_opt_sort,
    )(cmd)
    cmd = click.option(
        "--format",
        "fmt",
        type=click.Choice(["text", "json"]),
        default="text",
        help=EN.report_opt_format,
    )(cmd)
    cmd = click.option(
        "--json",
        "json_path",
        type=click.Path(),
        default=None,
        help=EN.report_opt_json,
    )(cmd)
    cmd = click.option(
        "--help",
        "show_help",
        is_flag=True,
        default=False,
        help=EN.report_opt_help,
    )(cmd)
    return cmd


@click.command(
    help=f"{EN.report_help_short}{_HELP_PARAGRAPH_SEP}{EN.report_help_long}",
    context_settings={
        "help_option_names": [],
        "ignore_unknown_options": True,
    },
)
def _bare_main(
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: str | None,
    show_help: bool,
) -> None:
    """Bilingual EN+HU reporter. See --help for details."""
    from easter_hermes_sorry_skills.cli_report import run as _run

    argv = sys.argv[1:]
    if show_help:
        emit_bilingual_help()
        sys.exit(0)
    jp: Path | None = Path(json_path) if json_path else None
    sys.exit(
        _run(
            profile=profile,
            sort=sort,
            fmt=fmt,
            json_path=jp,
            argv=argv,
        ),
    )


# Apply the five ``click.option`` decorators via a wrapper helper so the
# function itself only has one decorator (WPS216 cap of 5).
main = _with_report_options(_bare_main)
