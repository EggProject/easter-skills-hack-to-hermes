"""src/easter_hermes_sorry_skills/_cli_report_cmd.py

Click command definition for the reporter CLI.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import click

from easter_hermes_sorry_skills._cli_report_ui import emit_bilingual_help
from easter_hermes_sorry_skills.i18n import messages_en as EN

_HELP_PARAGRAPH_SEP = "\n\n"
_SORT_DEFAULT = "tokens"
_FMT_DEFAULT = "text"


def _with_report_options(cmd: click.Command) -> click.Command:
    """Apply the six reporter ``click.option`` decorators as one wrapper."""
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
    cmd = click.option(
        "--verbose",
        "verbose",
        is_flag=True,
        default=False,
        help=EN.report_opt_verbose,
    )(cmd)
    return cmd


@click.command(
    help=f"{EN.report_help_short}{_HELP_PARAGRAPH_SEP}{EN.report_help_long}",
    context_settings={
        "help_option_names": [],
        "ignore_unknown_options": True,
    },
)
def _bare_main(**kwargs: bool | str | None) -> None:
    """Bilingual EN+HU reporter. See --help for details."""
    from easter_hermes_sorry_skills.cli_report import run as _run

    resolved = _resolve_cli_kwargs(kwargs)
    argv = sys.argv[1:]
    if resolved.show_help:
        emit_bilingual_help()
        sys.exit(0)
    sys.exit(
        _run(
            profile=resolved.profile,
            sort=resolved.sort,
            fmt=resolved.fmt,
            json_path=resolved.json_path,
            verbose=resolved.verbose,
            argv=argv,
        ),
    )


@dataclass(frozen=True)
class _ResolvedCliArgs:
    """Click-resolved CLI args narrowed to the reporter's expected types."""

    profile: str | None
    sort: str
    fmt: str
    json_path: Path | None
    show_help: bool
    verbose: bool


def _resolve_cli_kwargs(kwargs: dict[str, bool | str | None]) -> _ResolvedCliArgs:
    """Narrow click kwargs to typed reporter args (≤5 locals in caller)."""
    profile = kwargs.get("profile")
    sort = kwargs.get("sort")
    fmt = kwargs.get("fmt")
    json_path_str = kwargs.get("json_path")
    return _ResolvedCliArgs(
        profile=profile if isinstance(profile, str) else None,
        sort=sort if isinstance(sort, str) else _SORT_DEFAULT,
        fmt=fmt if isinstance(fmt, str) else _FMT_DEFAULT,
        json_path=Path(json_path_str) if isinstance(json_path_str, str) else None,
        show_help=bool(kwargs.get("show_help", False)),
        verbose=bool(kwargs.get("verbose", False)),
    )


# Apply the six ``click.option`` decorators via a wrapper helper so the
# function itself only has one decorator (WPS216 cap of 5).
main = _with_report_options(_bare_main)
