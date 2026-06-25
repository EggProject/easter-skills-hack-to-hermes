"""Atomic-write primitives for the patcher (tmp + os.replace).

Extracted from ``_patcher_apply.py`` to keep module member count under
wemake's WPS202 threshold. Public surface used by
``_patcher_apply_state.py`` and ``_patcher_apply.py``.

File-mode helpers live in ``_patcher_apply_mode`` for the same reason.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from easter_hermes_sorry_skills._patcher_apply_mode import (
    _cleanup_tmp,
    _original_mode_for,
    _restore_mode,
)

NEWLINE = "\n"
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
    _restore_mode(target_path, original_mode)


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


def _diff_sha(before: bytes, after: bytes) -> str:
    """Return the hex SHA-256 of ``HASH_SEPARATOR``-joined ``before`` and ``after``."""
    joined = HASH_SEPARATOR.join([before, after])
    digest = hashlib.sha256(joined).hexdigest()
    return digest
