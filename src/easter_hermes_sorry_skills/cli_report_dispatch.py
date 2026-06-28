"""Context-loading + emit helpers for the reporter CLI.

Extracted from ``cli_report.py`` to keep that module under wemake WPS202
(≤7 module members).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from easter_hermes_sorry_skills import cli_report_imports as _imps
from easter_hermes_sorry_skills._i18n_pick import pick

_JSON_INSIDE_HERMES_HOME_RC = 6


def check_hermes_home(
    json_path: Path | None,
    hermes_home: Path,
    lang: str = "en",
) -> int | None:
    """Return 6 when json_path falls under hermes_home, else None."""
    if json_path is not None and _imps._check_json_path(
        json_path,
        hermes_home,
    ):
        click.echo(pick(lang).report_json_path_inside_hermes_home, err=True)
        return _JSON_INSIDE_HERMES_HOME_RC
    return None


def load_context(
    fmt: str,
    json_path: Path | None,
    profile: str | None,
    lang: str = "en",
) -> tuple[Path | None, object, list[Path], int | None]:
    """Resolve paths + curator + profiles. Return error code or None."""
    hermes_home = _imps._paths.resolve_hermes_home()
    resolved_json = _imps._helpers.resolve_json_path(fmt, json_path)
    rc = check_hermes_home(resolved_json, hermes_home, lang=lang)
    if rc is not None:
        return resolved_json, None, [], rc
    curator = _imps._paths.load_curator(hermes_home)
    profile_paths = _imps._paths.resolve_profiles(hermes_home, profile)
    return resolved_json, curator, profile_paths, None


def emit_sections(
    fmt: str,
    json_path: Path | None,
    text_sections: list[str],
    json_sections: list[Any],
    lang: str = "en",
) -> None:
    """Render and write/print the final output."""
    output = _imps.render_output(
        fmt,
        text_sections,
        json_sections,
        _imps.now_iso(),
    )
    _imps.emit_output(fmt, output, json_path, lang=lang)
