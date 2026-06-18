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
record emitted on drift / validation failure (plans/04 §Rejected
sidecar).

The audit log (``.patch.audit.log``) is appended on every successful
``--force`` run, NOT on normal ``--apply`` runs (plans/04 D4 +
plans/04 §Audit log). The state sidecar is the durable record for
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


def _atomic_write_bytes(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """Atomic write: tmp + os.replace; restore on exception; preserve mode.

    ``path`` is the final destination; ``<path>.patch.tmp`` is the temp
    file in the same directory (POSIX-atomic on the same filesystem).
    """
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        original_mode = path.stat().st_mode
    else:
        original_mode = mode if mode is not None else 0o644
    tmp_dir = str(parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".patch.tmp", dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fchmod(fd, original_mode)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    # After os.replace, ``path`` always exists (replace is atomic on
    # POSIX). The chmod is best-effort: if the FS rejects the chmod, we
    # don't fail the patch.
    try:
        os.chmod(path, stat.S_IMODE(original_mode), follow_symlinks=False)
    except OSError:
        pass


def _append_audit_log(audit_path: Path, line: str) -> None:
    """Append one line to the audit log; create parent dirs as needed."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def _diff_sha(before: bytes, after: bytes) -> str:
    return hashlib.sha256(before + b"\0" + after).hexdigest()


def load_state(target: Path) -> dict[str, str]:
    """Load ``.patch.state.json``; return empty dict on missing/corrupt."""
    sidecar = target / STATE_SIDECAR
    if not sidecar.exists():
        return {}
    try:
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def write_state(target: Path, state: dict[str, str]) -> None:
    """Write ``.patch.state.json`` atomically with sorted keys."""
    sidecar = target / STATE_SIDECAR
    payload = json.dumps(dict(sorted(state.items())), indent=2) + "\n"
    _atomic_write_bytes(sidecar, payload.encode("utf-8"))


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
        "tool": "hermes-skill-creator-patch",
        "version": "0.1.0",
        "target": str(target.resolve()),
        "git_head": git_head,
        "failures": failures,
        "remediation_en": remediation_en,
        "remediation_hu": remediation_hu,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write_bytes(rejected_path, text.encode("utf-8"))
    return rejected_path
