"""Audit pipeline core for the ``cli_profiles`` CLI.

Moved out of ``_cli_profiles_orchestrator`` to keep that module under
the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click
from hermes_cli.profiles import ProfileInfo

from hermes_skill_creator_plugin import _cli_profiles_bindings as _bindings
from hermes_skill_creator_plugin import _cli_profiles_orchestrator as _orchestrator
from hermes_skill_creator_plugin import _cli_profiles_profiles as _profiles

_bilingual = _orchestrator._bilingual
_audit_and_collect_row = _orchestrator._audit_and_collect_row
AuditReport = _bindings.AuditReport
LIVE_HERMES_HOME = _profiles.LIVE_HERMES_HOME


def _live_install_refused(apply: bool, yes: bool) -> bool:
    """Return True when the run should refuse to write the LIVE install."""
    if not apply or yes:
        return False
    env = os.environ.get("HERMES_HOME")
    if env is None:
        return False
    return Path(env).resolve() == LIVE_HERMES_HOME.resolve()


def _extract_audit_options(options: dict[str, object]) -> dict[str, object]:
    """Pull the recognized keyword options out of the raw options dict."""
    apply_key = "apply"
    return {
        apply_key: bool(options.get(apply_key, False)),
        "json_path": options.get("json_path"),
        "frozen_time": options.get("frozen_time"),
        "skip_install": bool(options.get("skip_install", False)),
        "yes": bool(options.get("yes", False)),
        "profile": options.get("profile"),
    }


def _write_json_report(report: AuditReport, json_path: Path) -> None:
    """Write the report JSON to json_path (creating parent dirs)."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes(report.to_json_bytes())
    click.echo(_bilingual("profiles_msg_json_written", path=str(json_path)))


@dataclass(frozen=True)
class _AuditPhaseParams:
    """Validated, typed view of the audit-phase options dict."""

    apply: bool
    frozen_time: str | None
    skip_install: bool
    profile: str | None

    @classmethod
    def from_opts(cls, opts: dict[str, object]) -> _AuditPhaseParams:
        return cls(
            apply=bool(opts["apply"]),
            frozen_time=cast(str | None, opts["frozen_time"]),
            skip_install=bool(opts["skip_install"]),
            profile=cast(str | None, opts["profile"]),
        )


def _audit_each_profile(
    selected: list[ProfileInfo],
    audit_params: _AuditPhaseParams,
) -> AuditReport:
    mode_key = "profiles_msg_applying" if audit_params.apply else "profiles_msg_audit_default"
    click.echo(_bilingual(mode_key))
    report = _profiles._empty_report(audit_params.frozen_time)
    for profile_info in selected:
        row = _audit_and_collect_row(
            profile_info,
            apply=audit_params.apply,
            skip_install=audit_params.skip_install,
            frozen_time=audit_params.frozen_time,
        )
        report.profiles.append(row)
    click.echo(_bilingual("profiles_msg_done", n=len(selected)))
    return report


def _run_audit_phase(opts: dict[str, object]) -> AuditReport:
    """Drive the audit/flip after the live-install refusal gate."""
    audit_params = _AuditPhaseParams.from_opts(opts)
    click.echo(_bilingual("profiles_msg_scanning"))
    selected = _profiles._select_profiles(
        _profiles._list_all_profiles(),
        audit_params.profile,
    )
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return _profiles._empty_report(audit_params.frozen_time)
    return _audit_each_profile(selected, audit_params)
