"""Target-resolution pre-flight flow for the patcher CLI.

Extracted from ``cli_patch.py`` to keep that module under wemake WPS202
(≤7 module members). Holds the small pre-patch helpers that decide
whether to refuse the run (``is_hermes_agent``) and resolve the
``--target`` path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from easter_hermes_sorry_skills.i18n.messages_en import (
    TARGET_IS_HERMES_AGENT,
)


def resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None


def refuse_hermes_agent(target_path: Path) -> None:
    click.echo(
        TARGET_IS_HERMES_AGENT.format(resolved=str(target_path)),
        err=True,
    )
    sys.exit(4)
