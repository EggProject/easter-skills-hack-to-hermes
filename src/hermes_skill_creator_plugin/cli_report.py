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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from hermes_skill_creator_plugin import _cli_report_helpers as _helpers
from hermes_skill_creator_plugin import _cli_report_helpers_paths as _paths
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
_load_curator = _paths.load_curator
_load_skill_description = _paths.load_skill_description
_now_iso = _helpers.now_iso
_resolve_hermes_home = _paths.resolve_hermes_home
_resolve_profiles = _paths.resolve_profiles


def _check_hermes_home(
    json_path: Path | None,
    hermes_home: Path,
) -> int | None:
    """Return 6 when json_path falls under hermes_home, else None."""
    from hermes_skill_creator_plugin.i18n import messages_en as EN

    if json_path is not None and _check_json_path(
        json_path,
        hermes_home,
    ):
        click.echo(EN.report_json_path_inside_hermes_home, err=True)
        return 6
    return None


@dataclass(frozen=True)
class ProfileBuildContext:
    """Per-profile build inputs (everything except the profile path)."""

    fmt: str
    sort: str
    platform: str | None
    curator: Any | None


def _build_profile_sections(
    profile_paths: list[Path],
    *,
    fmt: str,
    sort: str,
    platform: str | None,
    curator: Any | None,
) -> tuple[list[str], list[ProfileSection], int | None]:
    """Build text/json sections for all profiles. Error code or None."""
    text_sections: list[str] = []
    json_sections: list[ProfileSection] = []
    ctx = ProfileBuildContext(
        fmt=fmt,
        sort=sort,
        platform=platform,
        curator=curator,
    )
    for prof in profile_paths:
        rc = _build_one_profile_section(
            prof,
            ctx=ctx,
            text_sections=text_sections,
            json_sections=json_sections,
        )
        if rc is not None:
            return text_sections, json_sections, rc
    return text_sections, json_sections, None


def _build_one_profile_section(
    prof: Path,
    *,
    ctx: ProfileBuildContext,
    text_sections: list[str],
    json_sections: list[ProfileSection],
) -> int | None:
    """Append one profile's section; return 6 on detection error, else None."""
    from hermes_skill_creator_plugin.i18n import messages_en as EN

    try:
        rows, total = _build_rows_for_profile(
            prof,
            platform=ctx.platform,
            curator=ctx.curator,
            estimate_tokens_fn=estimate_tokens,
            enabled_skills_fn=get_enabled_skills,
        )
    except EnabledDetectionUnavailable:
        click.echo(EN.report_enabled_detection_unavailable, err=True)
        return 6
    rows = sort_rows(rows, ctx.sort)
    section = _helpers.make_section(ctx.fmt, prof.name, rows, total)
    if ctx.fmt == FORMAT_TEXT:
        text_sections.append(section)  # type: ignore[arg-type]
    else:
        json_sections.append(section)  # type: ignore[arg-type]
    return None


def _load_context(
    fmt: str,
    json_path: Path | None,
    profile: str | None,
) -> tuple[Path | None, object, list[Path], int | None]:
    """Resolve paths + curator + profiles. Return error code or None."""
    hermes_home = _paths.resolve_hermes_home()
    json_path = _helpers.resolve_json_path(fmt, json_path)
    rc = _check_hermes_home(json_path, hermes_home)
    if rc is not None:
        return json_path, None, [], rc
    curator = _paths.load_curator(hermes_home)
    profile_paths = _paths.resolve_profiles(hermes_home, profile)
    return json_path, curator, profile_paths, None


def _emit_sections(
    fmt: str,
    json_path: Path | None,
    text_sections: list[str],
    json_sections: list[ProfileSection],
) -> None:
    """Render and write/print the final output."""
    output = _helpers.render_output(
        fmt,
        text_sections,
        json_sections,
        _helpers.now_iso(),
    )
    _helpers.emit_output(fmt, output, json_path)


@dataclass(frozen=True)
class ReportInputs:
    """Immutable input set for the reporter's dispatch pipeline."""

    profile: str | None = None
    sort: str = SORT_TOKENS
    fmt: str = FORMAT_TEXT
    json_path: Path | None = None
    platform: str | None = None
    show_help: bool = False
    argv: list[str] | None = None


def run(**kwargs: Any) -> int:
    """Run the reporter. Returns the exit code (0 on success)."""
    return _dispatch(ReportInputs(**kwargs))


def _dispatch(inputs: ReportInputs) -> int:
    """Validate, resolve paths, build sections, emit."""
    early_rc = _early_exit_rc(inputs)
    if early_rc is not None:
        return early_rc
    json_path, curator, profile_paths, err = _load_context(
        inputs.fmt,
        inputs.json_path,
        inputs.profile,
    )
    if err is not None:
        return err
    return _build_and_emit(inputs, json_path, curator, profile_paths)


def _build_and_emit(
    inputs: ReportInputs,
    json_path: Path | None,
    curator: Any | None,
    profile_paths: list[Path],
) -> int:
    """Build sections for ``profile_paths`` and emit the final report."""
    text_sections, json_sections, build_err = _build_profile_sections(
        profile_paths,
        fmt=inputs.fmt,
        sort=inputs.sort,
        platform=inputs.platform,
        curator=curator,
    )
    if build_err is not None:
        return build_err
    _emit_sections(inputs.fmt, json_path, text_sections, json_sections)
    return 0


def _early_exit_rc(inputs: ReportInputs) -> int | None:
    """Return exit code for short-circuit cases (help / invalid args), or None."""
    if inputs.show_help:
        emit_bilingual_help()
        return 0
    if inputs.argv is not None:
        rc = _helpers.reject_unwanted_flags(inputs.argv)
        if rc is not None:
            return rc
    rc = _helpers.validate_sort_and_fmt(inputs.sort, inputs.fmt)
    if rc is not None:
        return rc
    return None


def _main_entry() -> None:
    """Module entry point - extracted for testability."""
    main()
