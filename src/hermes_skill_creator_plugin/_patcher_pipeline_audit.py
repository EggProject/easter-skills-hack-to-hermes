"""Site audit emitter for the patcher pipeline.

Split from ``_patcher_pipeline`` (WPS202 module surface budget). The
:func:`_emit_site_audit` forwarder + the audit-args dataclass live
here.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    _AuditLogInputs,
    emit_audit_log,
)
from hermes_skill_creator_plugin._patcher_sites import Site


@dataclasses.dataclass(frozen=True)
class _EmitSiteAuditArgs:
    """Bundle of audit-emit args (kept under WPS211 cap of 5)."""

    site: Site
    target_path: Path
    audit_path: Path
    timestamp: str
    before: bytes
    after_bytes: bytes


def _emit_site_audit(args: _EmitSiteAuditArgs) -> None:
    emit_audit_log(
        _AuditLogInputs(
            audit_path=args.audit_path,
            timestamp=args.timestamp,
            site_id=args.site.site_id,
            before=args.before,
            after_bytes=args.after_bytes,
            target_path=args.target_path,
        ),
    )
