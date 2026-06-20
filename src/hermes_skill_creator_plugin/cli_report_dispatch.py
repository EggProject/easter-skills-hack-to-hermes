"""Reporter dispatch + early-exit + build-and-emit helpers.

Split from ``cli_report`` (WPS202 module surface budget). These three
helpers stitch the per-profile sections into the final output.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from hermes_skill_creator_plugin import cli_report_imports as _imps
from hermes_skill_creator_plugin.cli_report_sections import (
    _build_profile_sections,
)

if TYPE_CHECKING:
    from hermes_skill_creator_plugin.cli_report import ReportInputs


_helpers = _imps._helpers
emit_bilingual_help = _imps.emit_bilingual_help


def _build_and_emit(
    inputs: ReportInputs,
    json_path: Path | None,
    curator: Any | None,
    profile_paths: list[Path],
) -> int:
    """Build sections for ``profile_paths`` and emit the final report."""
    from hermes_skill_creator_plugin.cli_report import (
        _emit_sections,
    )

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
