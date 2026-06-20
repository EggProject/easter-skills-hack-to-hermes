"""src/hermes_skill_creator_plugin/_cli_report_cmd.py

Click command definition for the reporter CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin._cli_report_ui import emit_bilingual_help
from hermes_skill_creator_plugin.i18n import messages_en as EN

_HELP_PARAGRAPH_SEP = "\n\n"


def _option_decorators() -> tuple[Any, ...]:
    """Return the per-flag ``click.option`` decorators for ``main``.

    Composed into a single stack by :func:`_compose_options` so the
    ``main`` definition does not trip ``WPS216`` (>5 decorators).
    """
    return (
        click.option("--profile", default=None, help=EN.report_opt_profile),
        click.option(
            "--sort",
            type=click.Choice(["tokens", "use_count", "last_used_at"]),
            default="tokens",
            help=EN.report_opt_sort,
        ),
        click.option(
            "--format",
            "fmt",
            type=click.Choice(["text", "json"]),
            default="text",
            help=EN.report_opt_format,
        ),
        click.option(
            "--json",
            "json_path",
            type=click.Path(),
            default=None,
            help=EN.report_opt_json,
        ),
        click.option(
            "--help",
            "show_help",
            is_flag=True,
            default=False,
            help=EN.report_opt_help,
        ),
    )


def _compose_options(func: Any) -> Any:
    """Apply all option decorators + ``click.command`` in a single stack.

    Keeps the ``main`` signature free of decorator noise so ``WPS216``
    (>5 decorators) stays quiet.
    """
    decorated: Any = func
    for option in _option_decorators():
        decorated = option(decorated)
    return click.command(
        help=f"{EN.report_help_short}{_HELP_PARAGRAPH_SEP}{EN.report_help_long}",
        context_settings={
            "help_option_names": [],
            "ignore_unknown_options": True,
        },
    )(decorated)


@_compose_options
def main(
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: str | None,
    show_help: bool,
) -> None:
    """Bilingual EN+HU reporter. See --help for details."""
    from hermes_skill_creator_plugin.cli_report import run as _run

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
