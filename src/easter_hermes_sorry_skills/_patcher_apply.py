"""Apply-side primitives: atomic write.

This module is the I/O layer for Script #1's patcher. The orchestrator
(``_patcher.py``) calls into here to perform the atomic-write protocol
required by plans/04 D6:

- ``<file>.patch.tmp`` + ``os.replace`` (POSIX-atomic on the same FS)
- original mode bits preserved via ``os.chmod`` (best-effort)
- on any exception during the write, the tmp file is unlinked and the
  original file is left untouched (the snapshot is in memory, not on
  disk, so a partial write can never reach the user-visible path)

The audit log (``./logs/patch-audit.log``) is appended on every
successful ``--force`` run, one line per invocation (timestamp +
combined diff sha256 hash). NOT on normal ``--apply`` runs (plans/04
D4 + plans/04 Audit log).

See also: plans/04-script-1-patch.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

from pathlib import Path

AUDIT_LOG_NAME = "patch-audit.log"
AUDIT_LOG_REL = Path("logs") / AUDIT_LOG_NAME


def audit_log_path() -> Path:
    """Return the per-invocation audit-log path under the cwd's ``./logs`` dir.

    Creates ``./logs`` if it doesn't exist so the first invocation in a
    fresh checkout does not fail with FileNotFoundError.
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / AUDIT_LOG_NAME
