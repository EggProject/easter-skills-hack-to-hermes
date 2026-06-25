"""Audit pipeline core for the ``cli_profiles`` CLI (READ-ONLY).

Phase 8 collapses the old audit+apply pipeline into a single
read-only scan. The source of truth for "which skills are enabled"
is ``_enabled_detection.get_enabled_skills()``; per-skill
descriptions come from ``_cli_report_helpers_paths.load_skill_description``
and per-skill token counts from ``_cli_profiles_skill.count_skill_token``.
The pipeline returns ``list[_ProfileRenderable]`` — the tuples
``render_all_profiles`` consumes to print tables or a JSON dump.
"""

from __future__ import annotations

import os
from pathlib import Path

import click
from rich.table import Table

from easter_hermes_sorry_skills import _cli_profiles_orchestrator as _orchestrator
from easter_hermes_sorry_skills import _cli_profiles_profiles as _profiles
from easter_hermes_sorry_skills import _cli_profiles_skill as _skill_mod
from easter_hermes_sorry_skills import _cli_profiles_table as _table_mod
from easter_hermes_sorry_skills._cli_report_helpers_paths import load_skill_description
from easter_hermes_sorry_skills._enabled_detection import get_enabled_skills

_bilingual = _orchestrator._bilingual
build_profile_table = _table_mod.build_profile_table

_ProfileRenderable = tuple[str, Table, dict[str, object]]


def _summarize_rows(rows: list[_skill_mod.EnabledSkillRow]) -> dict[str, object]:
    """Aggregate the per-profile rows into a single summary dict.

    The keys mirror the table renderer's JSON shape: ``skill_count``,
    ``token_total``, ``token_source`` (the dominant source across rows;
    ``"tokenizer"`` unless every row fell back to chars/4), and
    ``warnings`` (list of human-readable strings, currently empty).
    """
    every_row_is_fallback = all(row.token_source == "chars_div_4" for row in rows) if rows else False
    return {
        "skill_count": len(rows),
        "token_total": sum(row.token_count for row in rows),
        "token_source": "chars_div_4" if every_row_is_fallback else "tokenizer",
        "warnings": [],
    }


def _collect_enabled_rows_for_profile(
    profile_path: Path,
) -> list[_skill_mod.EnabledSkillRow]:
    """Collect the enabled-skill rows for one profile.

    Uses ``get_enabled_skills`` as the single source of truth; for
    each enabled skill the description is loaded from
    ``<skills_dir>/<name>/SKILL.md`` and the token count comes from
    ``count_skill_token``.
    """
    skills_dir = profile_path / "skills"
    enabled_names = get_enabled_skills(profile_path)
    return [
        _skill_mod.EnabledSkillRow(
            name=name,
            description=load_skill_description(skills_dir, name),
            token_count=_skill_mod.count_skill_token(
                name,
                load_skill_description(skills_dir, name),
            )[0],
            token_source=_skill_mod.count_skill_token(
                name,
                load_skill_description(skills_dir, name),
            )[1],
        )
        for name in sorted(enabled_names)
    ]


def _render_one_profile(
    index: int,
    total: int,
    profile_path: Path,
    name: str,
    *,
    verbose: bool,
) -> _ProfileRenderable:
    """Render one profile (verbose diagnostics + row collection + table build)."""
    if verbose:
        click.echo(
            f"[verbose] rendering profile {index}/{total}: {name}",
            err=True,
        )
    rows = _collect_enabled_rows_for_profile(profile_path)
    summary = _summarize_rows(rows)
    table = build_profile_table(name, rows, summary)
    return name, table, summary


def _run_audit_phase(
    opts: dict[str, object],
    *,
    verbose: bool = False,
    as_json: bool = False,
) -> list[_ProfileRenderable]:
    """Drive the READ-ONLY audit phase over the resolved profiles.

    ``opts`` only carries ``{"profile": str | None}``. ``verbose`` and
    ``as_json`` are forwarded to stderr diagnostics / output-format
    switches (the JSON switch is honored by the downstream renderer).
    """
    _emit_pre_scan_diagnostics(_coerce_profile_filter(opts), verbose)
    selected = _profiles._select_profiles(
        _profiles._list_all_profiles(),
        _coerce_profile_filter(opts),
    )
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return []
    return _render_each_profile(
        [(profile_info.name, profile_info.path) for profile_info in selected],
        verbose=verbose,
    )


def _coerce_profile_filter(opts: dict[str, object]) -> str | None:
    """Coerce the ``profile`` entry of ``opts`` to ``str | None``."""
    profile_filter_raw = opts.get("profile")
    return profile_filter_raw if isinstance(profile_filter_raw, str) else None


def _render_each_profile(
    selected: list[tuple[str, Path]],
    *,
    verbose: bool,
) -> list[_ProfileRenderable]:
    """Render each selected profile into a ``_ProfileRenderable`` entry.

    ``selected`` is a list of ``(name, path)`` tuples pre-extracted from
    the upstream ``ProfileInfo`` records by the caller. This avoids the
    pipeline depending on the ``hermes_cli.profiles.ProfileInfo`` type
    and keeps the wemake WPS201 import cap in reach.
    """
    total = len(selected)
    return [
        _render_one_profile(index, total, profile_path, name, verbose=verbose)
        for index, (name, profile_path) in enumerate(selected, start=1)
    ]


def _emit_pre_scan_diagnostics(
    profile_filter: str | None,
    verbose: bool,
) -> None:
    """Emit the pre-scan stderr diagnostics (HERMES_HOME + profile names)."""
    if verbose:
        hermes_home = os.environ.get("HERMES_HOME", "")
        click.echo(f"[verbose] HERMES_HOME={hermes_home}", err=True)
    click.echo(_bilingual("profiles_msg_scanning"))
    selected = _profiles._select_profiles(
        _profiles._list_all_profiles(),
        profile_filter,
    )
    if verbose:
        names = ",".join(getattr(profile_info, "name", "?") for profile_info in selected)
        click.echo(f"[verbose] resolved profiles: {len(selected)} ({names})", err=True)
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
