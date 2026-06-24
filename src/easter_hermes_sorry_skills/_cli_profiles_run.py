"""Top-level run_audit entry point for the ``cli_profiles`` CLI.

Moved out of ``_cli_profiles_orchestrator`` to keep that module under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings
from easter_hermes_sorry_skills import _cli_profiles_pipeline as _pipeline

_bilingual = _pipeline._bilingual
_extract_audit_options = _pipeline._extract_audit_options
_run_audit_phase = _pipeline._run_audit_phase
AuditReport = _bindings.AuditReport


def run_audit(**options: object) -> AuditReport:
    """Run the per-profile audit/flip.

    Accepted keyword options:
        apply (bool): Perform the writes (--dry-run inverts this).
        profile (str | None): Optional single profile NAME to restrict.
        verbose (bool): Emit [verbose] diagnostics to stderr + per-site
            row summaries (default: False, back-compat).

    Returns:
        The AuditReport.
    """
    opts = _extract_audit_options(options)
    verbose = bool(options.get("verbose", False))

    return _run_audit_phase(opts, verbose=verbose)
