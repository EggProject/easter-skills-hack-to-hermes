"""src/hermes_skill_creator_plugin/_cli_report_ui.py

Bilingual help/rejection messages for the reporter CLI.
"""
from __future__ import annotations

from hermes_skill_creator_plugin._cli_report_helpers import HELP_EN_HEADER, HELP_HU_HEADER
from hermes_skill_creator_plugin.i18n import messages_en as EN
from hermes_skill_creator_plugin.i18n import messages_hu as HU


_USAGE_LINE = (
    "  uv run hermes-skill-creator-report [--profile <name>] "
    "[--sort tokens|use_count|last_used_at]"
)
_USAGE_CONT = (
    "                                     [--format text|json] "
    "[--json PATH] [--help]"
)


def emit_bilingual_help() -> None:
    """Print a two-section bilingual help (English, then Hungarian)."""
    import click

    en_lines = [
        HELP_EN_HEADER,
        "",
        _USAGE_LINE,
        _USAGE_CONT,
        "",
        "Options:",
        "  --profile <name>    " + EN.report_opt_profile,
        "  --sort <key>        " + EN.report_opt_sort,
        "  --format <fmt>      " + EN.report_opt_format,
        "  --json PATH         " + EN.report_opt_json,
        "  --help              " + EN.report_opt_help,
    ]
    hu_lines = [
        HELP_HU_HEADER,
        "",
        _USAGE_LINE,
        _USAGE_CONT,
        "",
        "Opciok:",
        "  --profile <name>    " + HU.report_opt_profile,
        "  --sort <key>        " + HU.report_opt_sort,
        "  --format <fmt>      " + HU.report_opt_format,
        "  --json PATH         " + HU.report_opt_json,
        "  --help              " + HU.report_opt_help,
    ]
    click.echo("\n".join(en_lines))
    click.echo("")
    click.echo("\n".join(hu_lines))


def reject_flag(flag_name: str) -> int:
    """Print a bilingual rejection message and return exit code 2."""
    import click

    msg = {
        "apply": EN.report_rejected_apply,
        "emit-migration-note": EN.report_rejected_emit_migration_note,
        "write-report": EN.report_rejected_write_report,
    }.get(flag_name, EN.report_rejected_apply)
    click.echo(msg, err=True)
    return 2