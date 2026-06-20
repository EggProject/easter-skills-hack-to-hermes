"""Atomic-write primitives for the patcher (tmp + os.replace).

Extracted from ``_patcher_apply.py`` to keep module member count under
wemake's WPS202 threshold. Public surface used by
``_patcher_apply_state.py`` and ``_patcher_apply.py``.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

NEWLINE = "\n"
DEFAULT_FILE_MODE = 0o644
TMP_PREFIX = "."
TMP_SUFFIX = ".patch.tmp"
TEXT_ENCODING = "utf-8"
HASH_SEPARATOR = b"\0"
SHA_HEX_LENGTH = 64


def _with_newline(text: str) -> str:
    """Append a single newline to ``text`` if not already present."""
    if text.endswith(NEWLINE):
        return text
    return f"{text}{NEWLINE}"


def _make_tmp_path(parent: Path, final_name: str) -> tuple[int, str]:
    """Create a tmp file in ``parent`` alongside ``final_name`` and return its fd + name."""
    return tempfile.mkstemp(
        prefix=f"{final_name}{TMP_PREFIX}",
        suffix=TMP_SUFFIX,
        dir=str(parent),
    )


def _cleanup_tmp(tmp_name: str) -> None:
    """Unlink the tmp file (no-op if already gone)."""
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        return


def _original_mode_for(target_path: Path, mode: int | None) -> int:
    """Return the mode to apply to the freshly-written ``target_path``."""
    if target_path.exists():
        return target_path.stat().st_mode
    if mode is None:
        return DEFAULT_FILE_MODE
    return mode


def _atomic_write_bytes(
    target_path: Path,
    payload: bytes,
    *,
    mode: int | None = None,
) -> None:
    """Atomic write: tmp + os.replace; restore on exception; preserve mode.

    ``target_path`` is the final destination; ``<target_path>.patch.tmp``
    is the temp file in the same directory (POSIX-atomic on the same
    filesystem).
    """
    parent = target_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    original_mode = _original_mode_for(target_path, mode)
    fd, tmp_name = _make_tmp_path(parent, target_path.name)
    try:
        _commit_tmp_to_target(fd, payload, original_mode, tmp_name, target_path)
    except Exception:
        _cleanup_tmp(tmp_name)
        raise
    # After os.replace, ``target_path`` always exists (replace is atomic
    # on POSIX). The chmod is best-effort: if the FS rejects the chmod,
    # we don't fail the patch.
    try:
        os.chmod(target_path, stat.S_IMODE(original_mode), follow_symlinks=False)
    except OSError:
        pass


def _commit_tmp_to_target(
    fd: int,
    payload: bytes,
    original_mode: int,
    tmp_name: str,
    target_path: Path,
) -> None:
    """Write payload to tmp fd, then atomically replace target."""
    _write_tmp_payload(fd, payload, original_mode)
    os.replace(tmp_name, target_path)


def _write_tmp_payload(fd: int, payload: bytes, original_mode: int) -> None:
    """Write ``payload`` to ``fd`` and apply ``original_mode`` via fchmod."""
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fchmod(fd, original_mode)
