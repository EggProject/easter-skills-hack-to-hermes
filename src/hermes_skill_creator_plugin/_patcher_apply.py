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

import json
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._patcher_apply_atomic import (
    NEWLINE,
    TEXT_ENCODING,
    _atomic_write_bytes,
    _with_newline,
)

REJECTED_SIDECAR = Path(".patch.rejected")
AUDIT_LOG = Path(".patch.audit.log")
REJECTED_TOOL_NAME = "hermes-skill-creator-patch"
REJECTED_TOOL_VERSION = "0.1.0"


def _append_audit_log(audit_path: Path, line: str) -> None:
    """Append one line to the audit log; create parent dirs as needed."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    formatted = _with_newline(line.rstrip(NEWLINE))
    with audit_path.open("a", encoding=TEXT_ENCODING) as fh:
        fh.write(formatted)


def _build_rejected_payload(
    target: Path,
    failures: list[dict[str, Any]],
    remediation_en: str,
    remediation_hu: str,
    git_head: str,
) -> dict[str, Any]:
    """Build the JSON-ready dict for ``.patch.rejected``."""
    return {
        "tool": REJECTED_TOOL_NAME,
        "version": REJECTED_TOOL_VERSION,
        "target": str(target.resolve()),
        "git_head": git_head,
        "failures": failures,
        "remediation_en": remediation_en,
        "remediation_hu": remediation_hu,
    }


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
    payload = _build_rejected_payload(
        target=target,
        failures=failures,
        remediation_en=remediation_en,
        remediation_hu=remediation_hu,
        git_head=git_head,
    )
    text = _with_newline(json.dumps(payload, indent=2, sort_keys=True))
    _atomic_write_bytes(rejected_path, text.encode(TEXT_ENCODING))
    return rejected_path
