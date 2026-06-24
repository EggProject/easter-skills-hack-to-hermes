"""Result builders for the patcher pipeline.

Extracted from ``_patcher_pipeline_apply.py`` to keep that module under
wemake WPS202 (≤7 module members). Holds the ``PatcherResult``
construction helpers.
"""

from __future__ import annotations

from pathlib import Path

from easter_hermes_sorry_skills._patcher_consts import EXIT_IO, EXIT_PERMISSION
from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult
from easter_hermes_sorry_skills.i18n.messages_en import IO_ERROR, PERMISSION_DENIED


def io_error_result(path: Path, exc: OSError | PermissionError) -> PatcherResult:
    """Build the IO-error PatcherResult for the given exception."""
    if isinstance(exc, PermissionError):
        diag = PERMISSION_DENIED.format(path=str(path))
        exit_code = EXIT_PERMISSION
    else:
        diag = IO_ERROR.format(path=str(path), error=str(exc))
        exit_code = EXIT_IO
    return build_result(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=(diag,),
    )


def build_result(
    *,
    exit_code: int,
    sites_patched: tuple[str, ...],
    sites_already: tuple[str, ...],
    state: dict[str, str],
    diagnostics: tuple[str, ...],
) -> PatcherResult:
    """Build a ``PatcherResult``."""
    return PatcherResult(
        exit_code=exit_code,
        sites_patched=sites_patched,
        sites_already=sites_already,
        state=state,
        diagnostics=diagnostics,
        rejected_path=None,
    )


def build_result_with_rejected(
    *,
    exit_code: int,
    diagnostics: tuple[str, ...],
    state: dict[str, str],
    rejected_path: Path,
) -> PatcherResult:
    """Build a ``PatcherResult`` with a non-``None`` ``rejected_path``."""
    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state=state,
        diagnostics=diagnostics,
        rejected_path=rejected_path,
    )
