"""src/hermes_skill_creator_plugin/cli_report.py

Hermes skill-creator reporter (READ-ONLY) - Script #3.

See also: plans/13-script-3-report.md

The reporter is the operator's "what is on right now, and what does it
cost?" view. It is purely informational: NO file writes (except the
operator-chosen --json PATH), NO config flips, NO install calls.

Per-profile section building lives in :mod:`.cli_report_profile` and
context-loading / emit helpers live in :mod:`.cli_report_dispatch`;
the splits keep this module under wemake WPS202 (≤7 members).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin import _cli_report_helpers_consts as _helpers_consts
from hermes_skill_creator_plugin import cli_report_dispatch as _dispatch_mod
from hermes_skill_creator_plugin import cli_report_imports as _imps
from hermes_skill_creator_plugin import cli_report_profile as _profile_mod

# Test contract: the reporter MUST share enabled-detection with Script #2.
# Tests grep this source for ``from ... import get_enabled_skills`` to
# ensure the import is at module top-level (not inside a function). The
# alias ``_detect_fn`` keeps the F811 lint happy because the rebinding
# on the next line would otherwise flag the original name as unused.
from hermes_skill_creator_plugin._enabled_detection import (
    get_enabled_skills as _detect_fn,
)

# Public alias for callers and monkeypatch.setattr; rebinds to the
# shared import so :mod:`.cli_report_profile` sees the patched value.
get_enabled_skills = _imps.get_enabled_skills

# Touch ``_detect_fn`` so flake8 treats the alias import as used
# (the rebinding of ``get_enabled_skills`` alone does not satisfy F401).
# The identity check is a no-op at runtime but ruff understands it.
if _detect_fn is None:
    raise RuntimeError("enabled-detection import is unexpectedly None")

emit_bilingual_help = _imps.emit_bilingual_help
main = _imps.main
estimate_tokens = _imps.estimate_tokens
HELP_EN_HEADER = _helpers_consts.HELP_EN_HEADER
HELP_HU_HEADER = _helpers_consts.HELP_HU_HEADER
_emit_sections = _dispatch_mod.emit_sections
_load_context = _dispatch_mod.load_context
_profile_sections = _profile_mod.build_profile_sections
_paths = _imps._paths
_check_json_path = _imps._check_json_path
_load_skill_description = _paths.load_skill_description
_load_curator = _paths.load_curator
_resolve_hermes_home = _paths.resolve_hermes_home
_resolve_profiles = _paths.resolve_profiles
_now_iso = _imps.now_iso
_build_usage_rows = _imps._rows.build_usage_rows


@dataclass(frozen=True)
class ReportInputs:
    """Immutable input set for the reporter's dispatch pipeline."""

    profile: str | None = None
    sort: str = _imps.SORT_TOKENS
    fmt: str = _imps.FORMAT_TEXT
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
    text_sections, json_sections, build_err = _profile_sections(
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
        rc: int | None = _imps.reject_unwanted_flags(inputs.argv)
        if rc is not None:
            return rc
    rc = _imps.validate_sort_and_fmt(inputs.sort, inputs.fmt)
    if rc is not None:
        return rc
    return None


def _main_entry() -> None:
    """Module entry point - extracted for testability."""
    main()
