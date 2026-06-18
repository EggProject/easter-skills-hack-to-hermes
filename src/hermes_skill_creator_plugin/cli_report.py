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

from hermes_skill_creator_plugin import _cli_report_helpers as _helpers
from hermes_skill_creator_plugin import _cli_report_rows as _rows
from hermes_skill_creator_plugin._cli_report_cmd import main
from hermes_skill_creator_plugin._cli_report_ui import emit_bilingual_help
from hermes_skill_creator_plugin._enabled_detection import get_enabled_skills
from hermes_skill_creator_plugin._reporter import ProfileSection, sort_rows
from hermes_skill_creator_plugin._tokenizer import estimate_tokens


HELP_EN_HEADER = _helpers.HELP_EN_HEADER
HELP_HU_HEADER = _helpers.HELP_HU_HEADER
FORMAT_TEXT = _helpers.FORMAT_TEXT
SORT_TOKENS = _helpers.SORT_TOKENS
EnabledDetectionUnavailable = _rows.EnabledDetectionUnavailable
_build_rows_for_profile = _rows.build_rows_for_profile
_build_usage_rows = _rows.build_usage_rows
_check_json_path = _rows.check_json_path
_load_curator = _helpers.load_curator
_load_skill_description = _helpers.load_skill_description
_now_iso = _helpers.now_iso
_resolve_hermes_home = _helpers.resolve_hermes_home
_resolve_profiles = _helpers.resolve_profiles


def _check_hermes_home(
    json_path: Path | None, hermes_home: Path,
) -> int | None:
    """Return 6 when json_path falls under hermes_home, else None."""
    from hermes_skill_creator_plugin.i18n import messages_en as EN

    if json_path is not None and _check_json_path(
        json_path, hermes_home,
    ):
        click.echo(EN.report_json_path_inside_hermes_home, err=True)
        return 6
    return None


def _build_profile_sections(
    profile_paths: list[Path],
    *,
    fmt: str,
    sort: str,
    platform: str | None,
    curator,
) -> tuple[list[str], list[ProfileSection], int | None]:
    """Build text/json sections for all profiles. Error code or None."""
    from hermes_skill_creator_plugin.i18n import messages_en as EN

    text_sections: list[str] = []
    json_sections: list[ProfileSection] = []
    for prof in profile_paths:
        try:
            rows, total = _build_rows_for_profile(
                prof, platform=platform, curator=curator,
                estimate_tokens_fn=estimate_tokens,
                enabled_skills_fn=get_enabled_skills,
            )
        except EnabledDetectionUnavailable:
            click.echo(EN.report_enabled_detection_unavailable, err=True)
            return text_sections, json_sections, 6
        rows = sort_rows(rows, sort)
        section = _helpers.make_section(fmt, prof.name, rows, total)
        if fmt == FORMAT_TEXT:
            text_sections.append(section)  # type: ignore[arg-type]
        else:
            json_sections.append(section)  # type: ignore[arg-type]
    return text_sections, json_sections, None


def _load_context(
    fmt: str,
    json_path: Path | None,
    profile: str | None,
) -> tuple[Path | None, object, list[Path], int | None]:
    """Resolve paths + curator + profiles. Return error code or None."""
    hermes_home = _helpers.resolve_hermes_home()
    json_path = _helpers.resolve_json_path(fmt, json_path)
    rc = _check_hermes_home(json_path, hermes_home)
    if rc is not None:
        return json_path, None, [], rc
    curator = _helpers.load_curator(hermes_home)
    profile_paths = _helpers.resolve_profiles(hermes_home, profile)
    return json_path, curator, profile_paths, None


def _emit_sections(
    fmt: str,
    json_path: Path | None,
    text_sections: list[str],
    json_sections: list[ProfileSection],
) -> None:
    """Render and write/print the final output."""
    output = _helpers.render_output(
        fmt, text_sections, json_sections, _helpers.now_iso(),
    )
    _helpers.emit_output(fmt, output, json_path)


def _make_run_kwargs(
    *,
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: Path | None,
    platform: str | None,
    show_help: bool,
    argv: list[str] | None,
) -> dict[str, object]:
    """Bundle the run kwargs into a dict for _dispatch."""
    return {
        "profile": profile, "sort": sort, "fmt": fmt,
        "json_path": json_path, "platform": platform,
        "show_help": show_help, "argv": argv,
    }


def run(
    *,
    profile: str | None = None,
    sort: str = SORT_TOKENS,
    fmt: str = FORMAT_TEXT,
    json_path: Path | None = None,
    platform: str | None = None,
    show_help: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Run the reporter. Returns the exit code (0 on success)."""
    return _dispatch(**_make_run_kwargs(
        profile=profile, sort=sort, fmt=fmt,
        json_path=json_path, platform=platform,
        show_help=show_help, argv=argv,
    ))


def _dispatch(
    *,
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: Path | None,
    platform: str | None,
    show_help: bool,
    argv: list[str] | None,
) -> int:
    """Validate, resolve paths, build sections, emit."""
    if show_help:
        emit_bilingual_help()
        return 0
    if argv is not None:
        rc = _helpers.reject_unwanted_flags(argv)
        if rc is not None:
            return rc
    rc = _helpers.validate_sort_and_fmt(sort, fmt)
    if rc is not None:
        return rc
    json_path, curator, profile_paths, err = _load_context(
        fmt, json_path, profile,
    )
    if err is not None:
        return err
    text_sections, json_sections, build_err = _build_profile_sections(
        profile_paths, fmt=fmt, sort=sort,
        platform=platform, curator=curator,
    )
    if build_err is not None:
        return build_err
    _emit_sections(fmt, json_path, text_sections, json_sections)
    return 0


def _main_entry() -> None:
    """Module entry point - extracted for testability."""
    main()