"""Apply-side primitives: atomic write, state sidecar, rejected sidecar.

This module is the I/O layer for Script #1's patcher. The orchestrator
(``_patcher.py``) calls into here to persist the patcher's state to disk
and to perform the atomic-write protocol required by plans/04 D6:

- ``<file>.patch.tmp`` + ``os.replace`` (POSIX-atomic on the same FS)
- original mode bits preserved via ``os.chmod`` (best-effort)
- on any exception during the write, the tmp file is unlinked and the
  original file is left untouched (the snapshot is in memory, not on
  disk, so a partial write can never reach the user-visible path)

The state sidecar (``.patch.state.json``) is the durable record of
"which sites have been matched / patched / drifted". The rejected
sidecar (``.patch.rejected``) is the bilingual-machine-readable JSON
record emitted on drift / validation failure (plans/04 Rejected
sidecar).

The audit log (``.patch.audit.log``) is appended on every successful
``--force`` run, NOT on normal ``--apply`` runs (plans/04 D4 +
plans/04 Audit log). The state sidecar is the durable record for
normal applies.

See also: plans/04-script-1-patch.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

# --- sidecar file names ---------------------------------------------------
STATE_SIDECAR = Path(".patch.state.json")
REJECTED_SIDECAR = Path(".patch.rejected")
AUDIT_LOG = Path(".patch.audit.log")

DEFAULT_FILE_MODE = 0o644
TMP_PREFIX_SUFFIX = ".", ".patch.tmp"
TEXT_ENCODING = "utf-8"
HASH_SEPARATOR = b"\0"
SHA_HEX_LENGTH = 64
REJECTED_TOOL_NAME = "hermes-skill-creator-patch"
REJECTED_TOOL_VERSION = "0.1.0"


def _make_tmp_path(parent: Path, final_name: str) -> str:
    return tempfile.mkstemp(
        prefix=final_name + TMP_PREFIX_SUFFIX[0],
        suffix=TMP_PREFIX_SUFFIX[1],
        dir=str(parent),
    )


def _cleanup_tmp(tmp_name: str) -> None:
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
    if target_path.exists():
        original_mode = target_path.stat().st_mode
    else:
        original_mode = mode if mode is not None else DEFAULT_FILE_MODE
    fd, tmp_name = _make_tmp_path(parent, target_path.name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fchmod(fd, original_mode)
        os.replace(tmp_name, target_path)
    except Exception:
        _cleanup_tmp(tmp_name)
        raise
    # After os.replace, ``target_path`` always exists (replace is atomic
    # on POSIX). The chmod is best-effort: if the FS rejects the chmod,
    # we don't fail the patch.
    _restore_mode(target_path, original_mode)


def _append_audit_log(audit_path: Path, line: str) -> None:
    """Append one line to the audit log; create parent dirs as needed."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding=TEXT_ENCODING) as fh:
        fh.write(line.rstrip("\n") + "\n")


def _diff_sha(before: bytes, after: bytes) -> str:
    digest = hashlib.sha256(before + HASH_SEPARATOR + after).hexdigest()
    return digest


def load_state(target: Path) -> dict[str, str]:
    """Load ``.patch.state.json``; return empty dict on missing/corrupt."""
    sidecar = target / STATE_SIDECAR
    if not sidecar.exists():
        return {}
    try:
        raw = json.loads(sidecar.read_text(encoding=TEXT_ENCODING))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def write_state(target: Path, state: dict[str, str]) -> None:
    """Write ``.patch.state.json`` atomically with sorted keys."""
    sidecar = target / STATE_SIDECAR
    sorted_payload = json.dumps(dict(sorted(state.items())), indent=2) + "\n"
    _atomic_write_bytes(sidecar, sorted_payload.encode(TEXT_ENCODING))


def write_rejected(
    target: Path,
    *,
    failures: list[dict[str, Any]],
    remediation_en: str,
    remediation_hu: str,
    git_head: str,
) -> Path:
    """Write ``.patch.rejected`` JSON; return its path."""
    rejected_path = target / REJECTED_SIDECAR
    payload = {
        "tool": REJECTED_TOOL_NAME,
        "version": REJECTED_TOOL_VERSION,
        "target": str(target.resolve()),
        "git_head": git_head,
        "failures": failures,
        "remediation_en": remediation_en,
        "remediation_hu": remediation_hu,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write_bytes(rejected_path, text.encode(TEXT_ENCODING))
    return rejected_path
