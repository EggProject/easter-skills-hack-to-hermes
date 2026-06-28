"""src/easter_hermes_sorry_skills/_cli_report_cmd.py

Click command definition for the reporter CLI.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import click

from easter_hermes_sorry_skills._cli_report_helpers_consts import (
    _EN_DESCRIPTIONS,
    HELP_EN_HEADER,
    LANG_EN,
    LANG_OPT_DESC_EN,
    help_header,
    options_header,
    resolve_descriptions,
    resolve_lang_opt_desc,
)

_SORT_DEFAULT = "tokens"
_FMT_DEFAULT = "text"
_LANG_PARAM = "lang"


class _LangAwareCommand(click.Command):
    """Click command whose ``--help`` text follows the ``--lang`` option.

    ``--lang`` is declared ``is_eager`` so Click parses it before the
    built-in ``--help`` flag fires. When the user only passes ``--help``
    (no ``--lang``), ``ctx.params['lang']`` defaults to ``"en"`` so the
    English branch wins.

    Overrides both ``format_help_text`` (for the short description) and
    ``format_options`` (for the per-option description lines) so the
    whole ``--help`` output is in the requested single language — no
    bilingual ``[en] X / [hu] Y`` interleaving.
    """

    def format_help_text(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write(help_header(ctx.params.get(_LANG_PARAM, LANG_EN)))

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        lang = ctx.params.get(_LANG_PARAM, LANG_EN)
        lang_opt_desc = resolve_lang_opt_desc(lang)
        descriptions = resolve_descriptions(lang)

        with formatter.section(options_header(lang)):
            self._write_option_lines(formatter, ctx, descriptions, lang_opt_desc)

    def _write_option_lines(
        self,
        formatter: click.HelpFormatter,
        ctx: click.Context,
        descriptions: MappingProxyType[str, str],
        lang_opt_desc: str,
    ) -> None:
        """Emit one ``  --flag  description`` line per option."""
        for entry in self.get_params(ctx):
            if entry.name is None:
                continue
            if entry.name == _LANG_PARAM:
                opt_label = "--lang"
                description = lang_opt_desc
            else:
                opt_label = entry.opts[0] if entry.opts else f"--{entry.name}"
                description = descriptions.get(opt_label, "")
            if description:
                formatter.write_text(f"  {opt_label}  {description}")


def _with_report_options(cmd: click.Command) -> click.Command:
    """Apply the seven reporter ``click.option`` decorators as one wrapper.

    ``--help`` is intentionally NOT registered here — Click handles the
    native ``--help`` flag (printing ``Usage:``, ``Options:`` and exiting
    with code 0) via ``_LangAwareCommand.format_help_text`` +
    ``_LangAwareCommand.format_options``.
    """
    cmd = click.option(
        "--lang",
        type=click.Choice([LANG_EN, "hu"]),
        default=LANG_EN,
        is_eager=True,
        expose_value=True,
        help=LANG_OPT_DESC_EN,
    )(cmd)
    cmd = click.option(
        "--profile",
        default=None,
        help=_EN_DESCRIPTIONS["--profile"],
    )(cmd)
    cmd = click.option(
        "--sort",
        type=click.Choice(["tokens", "use_count", "last_used_at"]),
        default="tokens",
        help=_EN_DESCRIPTIONS["--sort"],
    )(cmd)
    cmd = click.option(
        "--format",
        "fmt",
        type=click.Choice(["text", "json"]),
        default="text",
        help=_EN_DESCRIPTIONS["--format"],
    )(cmd)
    cmd = click.option(
        "--json",
        "json_path",
        type=click.Path(),
        default=None,
        help=_EN_DESCRIPTIONS["--json"],
    )(cmd)
    cmd = click.option(
        "--verbose",
        "verbose",
        is_flag=True,
        default=False,
        help=_EN_DESCRIPTIONS["--verbose"],
    )(cmd)
    return cmd


@click.command(
    cls=_LangAwareCommand,
    help=HELP_EN_HEADER,
    context_settings={
        "ignore_unknown_options": True,
    },
)
def _bare_main(**kwargs: bool | str | None) -> None:
    """Bilingual EN+HU reporter. See --help for details."""
    from easter_hermes_sorry_skills.cli_report import run as _run

    resolved = _resolve_cli_kwargs(kwargs)
    argv = sys.argv[1:]
    sys.exit(
        _run(
            profile=resolved.profile,
            sort=resolved.sort,
            fmt=resolved.fmt,
            json_path=resolved.json_path,
            verbose=resolved.verbose,
            lang=resolved.lang,
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
    verbose: bool
    lang: str


def _resolve_cli_kwargs(kwargs: dict[str, bool | str | None]) -> _ResolvedCliArgs:
    """Narrow click kwargs to typed reporter args (≤5 locals in caller)."""
    profile = kwargs.get("profile")
    sort = kwargs.get("sort")
    fmt = kwargs.get("fmt")
    json_path_str = kwargs.get("json_path")
    lang = kwargs.get(_LANG_PARAM)
    return _ResolvedCliArgs(
        profile=profile if isinstance(profile, str) else None,
        sort=sort if isinstance(sort, str) else _SORT_DEFAULT,
        fmt=fmt if isinstance(fmt, str) else _FMT_DEFAULT,
        json_path=Path(json_path_str) if isinstance(json_path_str, str) else None,
        verbose=bool(kwargs.get("verbose", False)),
        lang=lang if isinstance(lang, str) else LANG_EN,
    )


# Apply the seven ``click.option`` decorators via a wrapper helper so the
# function itself only has one decorator (WPS216 cap of 5).
main = _with_report_options(_bare_main)
