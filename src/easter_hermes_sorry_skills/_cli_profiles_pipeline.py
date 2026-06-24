"""Audit pipeline core for the ``cli_profiles`` CLI.

Moved out of ``_cli_profiles_orchestrator`` to keep that module under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import click

if TYPE_CHECKING:
    from hermes_cli.profiles import ProfileInfo

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings
from easter_hermes_sorry_skills import _cli_profiles_orchestrator as _orchestrator
from easter_hermes_sorry_skills import _cli_profiles_profiles as _profiles

_bilingual = _orchestrator._bilingual
_audit_and_collect_row = _orchestrator._audit_and_collect_row
AuditReport = _bindings.AuditReport


def _extract_audit_options(options: dict[str, object]) -> dict[str, object]:
    """Pull the recognized keyword options out of the raw options dict."""
    return {
        "apply": bool(options.get("apply", False)),
        "profile": options.get("profile"),
    }


@dataclass(frozen=True)
class _AuditPhaseParams:
    """Validated, typed view of the audit-phase options dict."""

    apply: bool
    profile: str | None

    @classmethod
    def from_opts(cls, opts: dict[str, object]) -> _AuditPhaseParams:
        return cls(
            apply=bool(opts["apply"]),
            profile=cast(str | None, opts["profile"]),
        )


def _audit_each_profile(
    selected: list[ProfileInfo],
    audit_params: _AuditPhaseParams,
    *,
    verbose: bool = False,
) -> AuditReport:
    mode_key = "profiles_msg_applying"
    click.echo(_bilingual(mode_key, n=len(selected)))
    report = _profiles._empty_report()
    for profile_info in selected:
        row = _audit_and_collect_row(
            profile_info,
            apply=audit_params.apply,
            verbose=verbose,
        )
        report.profiles.append(row)
    click.echo(_bilingual("profiles_msg_done", n=len(selected)))
    return report


def _run_audit_phase(opts: dict[str, object], *, verbose: bool = False) -> AuditReport:
    """Drive the audit/flip after the live-install refusal gate."""
    audit_params = _AuditPhaseParams.from_opts(opts)
    if verbose:
        hermes_home = os.environ.get("HERMES_HOME", "")
        click.echo(f"[verbose] HERMES_HOME={hermes_home}", err=True)
    click.echo(_bilingual("profiles_msg_scanning"))
    selected = _profiles._select_profiles(
        _profiles._list_all_profiles(),
        audit_params.profile,
    )
    if verbose:
        names = ",".join(profile_info.name for profile_info in selected)
        click.echo(f"[verbose] resolved profiles: {len(selected)} ({names})", err=True)
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return _profiles._empty_report()
    return _audit_each_profile(selected, audit_params, verbose=verbose)
