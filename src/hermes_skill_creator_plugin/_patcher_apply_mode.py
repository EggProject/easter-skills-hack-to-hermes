"""File-mode helpers for the atomic-write primitives.

Extracted from ``_patcher_apply_atomic.py`` to keep that module under
wemake WPS202 (≤7 module members). Holds the mode-resolution +
best-effort chmod helpers.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

DEFAULT_FILE_MODE = 0o644


def _cleanup_tmp(tmp_name: str) -> None:
    """Unlink the tmp file (no-op if already gone)."""
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        return


def _restore_mode(path: Path, original_mode: int) -> None:
    """Best-effort chmod; never raises."""
    try:
        os.chmod(path, stat.S_IMODE(original_mode), follow_symlinks=False)
    except OSError:
        return


def _original_mode_for(target_path: Path, mode: int | None) -> int:
    """Return the mode to apply to the freshly-written ``target_path``."""
    if target_path.exists():
        return target_path.stat().st_mode
    if mode is None:
        return DEFAULT_FILE_MODE
    return mode
