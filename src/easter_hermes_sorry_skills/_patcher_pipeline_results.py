"""Result builders for the patcher pipeline.

Extracted from ``_patcher_pipeline_apply.py`` to keep that module under
wemake WPS202 (≤7 module members). Holds the ``PatcherResult``
construction helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from easter_hermes_sorry_skills._patcher import PatcherResult


def io_error_result(path: Path, exc: OSError | PermissionError) -> PatcherResult:
    """Build the IO-error PatcherResult for the given exception."""
    if isinstance(exc, PermissionError):
        from easter_hermes_sorry_skills._patcher_pipeline_apply import (
            EXIT_PERMISSION,
            PERMISSION_DENIED_TEXT,
        )

        diag = PERMISSION_DENIED_TEXT.format(path=str(path))
        exit_code = EXIT_PERMISSION
    else:
        from easter_hermes_sorry_skills._patcher_pipeline_apply import (
            EXIT_IO,
            IO_ERROR_TEXT,
        )

        diag = IO_ERROR_TEXT.format(path=str(path), error=str(exc))
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
    """Build a ``PatcherResult`` (lazy import to avoid the cycle)."""
    from easter_hermes_sorry_skills._patcher import PatcherResult

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
    from easter_hermes_sorry_skills._patcher import PatcherResult

    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state=state,
        diagnostics=diagnostics,
        rejected_path=rejected_path,
    )
