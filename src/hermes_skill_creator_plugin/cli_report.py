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

from hermes_skill_creator_plugin import cli_report_imports as _imps
from hermes_skill_creator_plugin.cli_report_dispatch import (
    _build_and_emit,
    _early_exit_rc,
)
from hermes_skill_creator_plugin.i18n import messages_en as EN

# Local bindings for readability; source-of-truth imports live in
# :mod:`.cli_report_imports` (extracted to satisfy WPS201).
_helpers = _imps._helpers
_paths = _imps._paths
_rows = _imps._rows
main = _imps.main

# ``ProfileSection`` is used in type annotations only; with
# ``from __future__ import annotations`` the type-checker can resolve
# it through the imports module without a module-level binding.
# Tests import ``ProfileSection`` by name from this module via the
# reporter submodule, so we DO need to bind it.
ProfileSection = _imps.ProfileSection

HELP_EN_HEADER = _helpers.HELP_EN_HEADER
HELP_HU_HEADER = _helpers.HELP_HU_HEADER
FORMAT_TEXT = _helpers.FORMAT_TEXT
SORT_TOKENS = _helpers.SORT_TOKENS
_check_json_path = _rows.check_json_path
_now_iso = _helpers.now_iso
_resolve_hermes_home = _paths.resolve_hermes_home
_load_curator = _paths.load_curator
_resolve_profiles = _paths.resolve_profiles
_load_skill_description = _paths.load_skill_description
_build_usage_rows = _rows.build_usage_rows
_build_rows_for_profile = _rows.build_rows_for_profile
estimate_tokens = _imps.estimate_tokens


def _check_hermes_home(
    json_path: Path | None,
    hermes_home: Path,
) -> int | None:
    """Return 6 when json_path falls under hermes_home, else None."""
    if json_path is not None and _check_json_path(
        json_path,
        hermes_home,
    ):
        click.echo(EN.report_json_path_inside_hermes_home, err=True)
        return 6
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


def _main_entry() -> None:
    """Module entry point - extracted for testability."""
    main()
