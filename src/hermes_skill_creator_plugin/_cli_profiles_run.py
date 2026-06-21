"""Top-level run_audit entry point for the ``cli_profiles`` CLI.

Moved out of ``_cli_profiles_orchestrator`` to keep that module under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from hermes_skill_creator_plugin import _cli_profiles_bindings as _bindings
from hermes_skill_creator_plugin import _cli_profiles_pipeline as _pipeline

_bilingual = _pipeline._bilingual
_live_install_refused = _pipeline._live_install_refused
_extract_audit_options = _pipeline._extract_audit_options
_run_audit_phase = _pipeline._run_audit_phase
_write_json_report = _pipeline._write_json_report
AuditReport = _bindings.AuditReport


def run_audit(**options: object) -> AuditReport:
    """Run the per-profile audit/flip.

    Accepted keyword options:
        apply (bool): Perform the writes (--apply).
        json_path (Path | None): Optional path to write the JSON report to.
        frozen_time (str | None): Optional ISO 8601 UTC string to pin
            the report timestamp (D7: determinism).
        skip_install (bool): Audit only; do not call do_install.
        yes (bool): Suppress the live-install refusal.
        profile (str | None): Optional single profile NAME to restrict.

    Returns:
        The AuditReport (also written to json_path if given).
    """
    import click

    opts = _extract_audit_options(options)

    # 0. Live-install refusal (safety contract). The refusal fires
    #    whenever HERMES_HOME resolves to the LIVE install AND --yes is
    #    absent — TTY or not, CI or interactive. Operators who really
    #    want to write to the live install must pass --yes.
    if _live_install_refused(bool(opts["apply"]), bool(opts["yes"])):
        click.echo(_bilingual("profiles_msg_refuse_no_yes"))
        sys.exit(5)

    report = _run_audit_phase(opts)

    json_path = opts["json_path"]
    if json_path is not None:
        _write_json_report(report, cast(Path, json_path))

    return report
