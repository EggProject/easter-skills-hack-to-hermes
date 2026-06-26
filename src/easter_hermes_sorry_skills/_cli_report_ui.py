"""src/easter_hermes_sorry_skills/_cli_report_ui.py

Bilingual help/rejection messages for the reporter CLI.
"""

from __future__ import annotations

from easter_hermes_sorry_skills._cli_report_helpers_consts import (
    HELP_EN_HEADER,
    HELP_HU_HEADER,
)
from easter_hermes_sorry_skills.i18n import messages_en as EN


def emit_bilingual_help(lang: str = "en") -> None:
    """Print the short help text (no Options block).

    ``lang="en"`` prints the English header; ``lang="hu"`` prints the
    Hungarian header. The Click-rendered ``Options:`` block is omitted
    here — callers that need it should let ``_LangAwareCommand`` render
    the full ``--help`` output.
    """
    import click

    if lang == "hu":
        click.echo(HELP_HU_HEADER)
    else:
        click.echo(HELP_EN_HEADER)


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
