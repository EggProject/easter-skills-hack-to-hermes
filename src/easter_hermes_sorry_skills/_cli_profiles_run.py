"""Top-level run_audit entry point for the ``cli_profiles`` CLI (READ-ONLY).

Phase 8 collapses the audit/apply split into a single read-only scan.
The CLI never writes; ``run_audit`` builds the per-profile renderable
entries (text tables or a JSON dump) and returns them to the caller
without ever touching the live ``~/.hermes`` install.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from easter_hermes_sorry_skills import _cli_profiles_pipeline as _pipeline
from easter_hermes_sorry_skills import _cli_profiles_table as _table_mod

_run_audit_phase = _pipeline._run_audit_phase
render_all_profiles = _table_mod.render_all_profiles

_ProfileRenderable = tuple[str, Table, dict[str, object]]


def run_audit(
    *,
    profile: str | None = None,
    verbose: bool = False,
    as_json: bool = False,
) -> list[_ProfileRenderable]:
    """Run the read-only per-profile audit.

    Args:
        profile: optional profile NAME to restrict the run to. ``None``
            audits every profile returned by ``hermes_cli.profiles.list_profiles``.
        verbose: emit ``[verbose]`` diagnostics to stderr.
        as_json: when True, ``render_all_profiles`` dumps the per-profile
            rows as JSON; otherwise it prints rich tables.

    Returns:
        The list of ``(profile_name, Table, summary)`` tuples produced
        by the pipeline.
    """
    entries = _run_audit_phase(
        {"profile": profile},
        verbose=verbose,
        as_json=as_json,
    )
    console = Console()
    render_all_profiles(entries, as_json=as_json, console=console)
    return entries
