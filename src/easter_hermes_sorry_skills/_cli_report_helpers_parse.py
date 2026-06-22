"""Flag / sort / format / path validation helpers for the reporter CLI.

Extracted from ``_cli_report_helpers.py`` to keep that module under
wemake WPS202 (≤7 module members). These helpers read user input, the
frozen-time env var, and the rejected-flags table; they do NOT write
output.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import click

from easter_hermes_sorry_skills._cli_report_helpers_consts import (
    FORMAT_KEYS,
    REJECTED_FLAGS,
    SORT_KEYS,
)
from easter_hermes_sorry_skills.i18n import messages_en as EN


def emit_tokenizer_warning(_msg: str) -> None:
    """Bilingual warning callback for tokenizer. See cli_report."""
    click.echo(EN.report_tokenizer_unavailable, err=True)


def now_iso() -> str:
    """Return an ISO 8601 UTC timestamp. Honors frozen-time env var."""
    frozen = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME", "").strip()
    if frozen:
        return frozen
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def reject_unwanted_flags(argv: list[str]) -> int | None:
    """Return reject_flag code if argv contains a rejected flag, else None."""
    sep = "="
    for arg in argv:
        reject_code = _reject_for_arg(arg, sep)
        if reject_code is not None:
            return reject_code
    return None


def _reject_for_arg(arg: str, sep: str) -> int | None:
    """Return the reject flag code for ``arg`` when it matches a rejected flag."""
    for prefix, key in REJECTED_FLAGS.items():
        with_eq = prefix + sep
        if arg == prefix or arg.startswith(with_eq):
            from easter_hermes_sorry_skills._cli_report_ui import (
                reject_flag as _reject,
            )

            return _reject(key)
    return None


def validate_sort_and_fmt(sort: str, fmt: str) -> int | None:
    """Return 2 when sort/fmt invalid, else None."""
    if sort not in SORT_KEYS:
        click.echo(EN.report_opt_sort, err=True)
        return 2
    if fmt not in FORMAT_KEYS:
        click.echo(EN.report_opt_format, err=True)
        return 2
    return None
