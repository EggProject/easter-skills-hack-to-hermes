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

The audit log (``~/.hermes/patch-audit.log``) is appended on every
successful ``--force`` run, one line per invocation (timestamp +
combined diff sha256 hash). NOT on normal ``--apply`` runs (plans/04
D4 + plans/04 Audit log). The state sidecar is the durable record for
normal applies.

See also: plans/04-script-1-patch.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from easter_hermes_sorry_skills._patcher_apply_atomic import (
    TEXT_ENCODING,
    _atomic_write_bytes,
    _with_newline,
)

REJECTED_SIDECAR = Path(".patch.rejected")
AUDIT_LOG_NAME = "patch-audit.log"
AUDIT_LOG_REL = Path(".hermes") / AUDIT_LOG_NAME
REJECTED_TOOL_NAME = "easter-hermes-sorry-skills-patch-hermes"
REJECTED_TOOL_VERSION = "0.1.0"


def _hermes_home_for_audit() -> Path:
    """Resolve the HERMES_HOME root used for the per-invocation audit log.

    Honors ``HERMES_HOME`` (default ``~/.hermes``) so tests can redirect
    the audit log away from the operator's live install. The path is
    always returned as an absolute, resolved Path.
    """
    raw = os.environ.get("HERMES_HOME") or "~/.hermes"
    return Path(raw).expanduser().resolve()


def audit_log_path() -> Path:
    """Return the per-invocation audit-log path under HERMES_HOME."""
    return _hermes_home_for_audit() / AUDIT_LOG_NAME


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
