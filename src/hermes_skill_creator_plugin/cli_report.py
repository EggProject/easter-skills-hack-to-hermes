"""src/hermes_skill_creator_plugin/cli_report.py

Hermes skill-creator reporter (READ-ONLY) - Script #3.

See also: plans/13-script-3-report.md

The reporter is the operator's "what is on right now, and what does it
cost?" view. It is purely informational: NO file writes (except the
operator-chosen --json PATH), NO config flips, NO install calls.

TDD test cases for this module:
  test_help_is_bilingual
  test_exit_zero_on_success
  test_exit_six_when_enabled_detection_unavailable
  test_default_profile_iteration
  test_named_profile_selects_one
  test_sort_by_tokens
  test_sort_by_use_count
  test_sort_by_last_used_at
  test_text_format_columns
  test_json_format_shape
  test_rejects_apply_flag
  test_rejects_emit_migration_note_flag
  test_rejects_write_report_flag
  test_json_path_outside_fixture
  test_json_path_inside_hermes_home_aborts
  test_no_write_to_hermes_home_under_any_flag_combination
  test_no_migration_report_file_emitted
  test_console_log_lines_match_bilingual_regex
  test_uses_at_suffixed_timestamps
  test_does_not_invent_fields
"""
from __future__ import annotations

from pathlib import Path

import click

from ._cli_report_helpers import (
    HELP_EN_HEADER,
    HELP_HU_HEADER,
    REJECTED_FLAGS,
    emit_tokenizer_warning as _emit_tokenizer_warning,
    load_curator as _load_curator,
    load_skill_description as _load_skill_description,
    now_iso as _now_iso,
    resolve_hermes_home as _resolve_hermes_home,
    resolve_profiles as _resolve_profiles,
)
from ._cli_report_rows import (
    EnabledDetectionUnavailable as _EnabledDetectionUnavailable,
    build_rows_for_profile as _build_rows_for_profile,
    build_usage_rows as _build_usage_rows,
    check_json_path as _check_json_path,
)
from ._enabled_detection import get_enabled_skills
from ._cli_report_ui import emit_bilingual_help, reject_flag
from ._reporter import ProfileSection, format_json, format_text, sort_rows
from ._tokenizer import estimate_tokens
from .i18n import messages_en as EN


def run(
    *,
    profile: str | None = None,
    sort: str = "tokens",
    fmt: str = "text",
    json_path: Path | None = None,
    platform: str | None = None,
    show_help: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Run the reporter. Returns the exit code (0 on success)."""
    if argv is not None:
        for arg in argv:
            for prefix, key in REJECTED_FLAGS.items():
                if arg == prefix or arg.startswith(prefix + "="):
                    return reject_flag(key)
    if show_help:
        emit_bilingual_help()
        return 0
    if sort not in {"tokens", "use_count", "last_used_at"}:
        click.echo(EN.report_opt_sort, err=True)
        return 2
    if fmt not in {"text", "json"}:
        click.echo(EN.report_opt_format, err=True)
        return 2
    hermes_home = _resolve_hermes_home()
    if json_path is None and fmt == "json":
        json_path = Path("./skill-report.json")
    if json_path is not None and _check_json_path(json_path, hermes_home):
        click.echo(EN.report_json_path_inside_hermes_home, err=True)
        return 6
    curator = _load_curator(hermes_home)
    profile_paths = _resolve_profiles(hermes_home, profile)
    if not profile_paths:
        click.echo(EN.report_no_profiles, err=True)
        return 0
    generated_at = _now_iso()
    text_sections: list[str] = []
    json_sections: list[ProfileSection] = []
    for p in profile_paths:
        try:
            rows, total = _build_rows_for_profile(
                p,
                platform=platform,
                curator=curator,
                estimate_tokens_fn=estimate_tokens,
                enabled_skills_fn=get_enabled_skills,
            )
        except _EnabledDetectionUnavailable:
            click.echo(EN.report_enabled_detection_unavailable, err=True)
            return 6
        rows = sort_rows(rows, sort)
        if fmt == "text":
            text_sections.append(
                format_text(p.name, rows, total_tokens=total)
            )
        else:
            json_sections.append(
                ProfileSection(
                    profile_name=p.name, rows=rows, total_tokens=total
                )
            )
    if fmt == "text":
        output = "\n\n".join(text_sections)
    else:
        output = format_json(
            tool="hermes-skill-creator-report",
            version="0.1.0",
            generated_at=generated_at,
            sections=json_sections,
        )
    if fmt == "json":
        assert json_path is not None
        json_path.write_text(output, encoding="utf-8")
        click.echo(EN.report_opt_json)
    else:
        click.echo(output)
    return 0


@click.command(
    help=EN.report_help_short + "\n\n" + EN.report_help_long,
    context_settings={
        "help_option_names": [],
        "ignore_unknown_options": True,
    },
)
@click.option("--profile", default=None, help=EN.report_opt_profile)
@click.option(
    "--sort",
    type=click.Choice(["tokens", "use_count", "last_used_at"]),
    default="tokens",
    help=EN.report_opt_sort,
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help=EN.report_opt_format,
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(),
    default=None,
    help=EN.report_opt_json,
)
@click.option(
    "--help", "show_help", is_flag=True, default=False,
    help=EN.report_opt_help,
)
def main(
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: str | None,
    show_help: bool,
) -> None:
    """Bilingual EN+HU reporter. See --help for details."""
    import sys

    argv = sys.argv[1:]
    if show_help:
        emit_bilingual_help()
        raise SystemExit(0)
    jp: Path | None = Path(json_path) if json_path else None
    raise SystemExit(
        run(
            profile=profile,
            sort=sort,
            fmt=fmt,
            json_path=jp,
            argv=argv,
        )
    )


def _main_entry() -> None:
    """Module entry point - extracted for testability."""
    main()