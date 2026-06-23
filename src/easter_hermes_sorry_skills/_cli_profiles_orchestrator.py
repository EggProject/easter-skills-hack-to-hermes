"""Audit pipeline helpers for the ``cli_profiles`` CLI.

Moved out of the top-level ``cli_profiles`` module to keep that
module under the wemake WPS202 cap (<=7 module members).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import click

if TYPE_CHECKING:
    from hermes_cli.profiles import ProfileInfo

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings

_audit_profile = _bindings._audit_profile
AuditReport = _bindings.AuditReport


def _bilingual(key: str, **format_kwargs: object) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key."""
    return _bindings._build_bilingual(_bindings.EN, _bindings.HU, key, **format_kwargs)


def _echo_row_summary(row: dict[str, object]) -> None:
    """Echo the per-profile audit summary + diff in bilingual form."""
    click.echo(
        _bilingual(
            "profiles_msg_profile_audit",
            name=row["profile_name"],
            disabled=_join_or_dash(cast(list[str], row["current_disabled"])),
            installed=_join_or_dash(cast(list[str], row["current_installed"])),
        )
    )
    diff_row = cast(dict[str, list[str]], row["diff"])
    click.echo(
        _bilingual(
            "profiles_msg_diff",
            ad=_join_or_dash(diff_row["added_disabled"]),
            rd=_join_or_dash(diff_row["removed_disabled"]),
            ai=_join_or_dash(diff_row["added_installed"]),
            ri=_join_or_dash(diff_row["removed_installed"]),
        )
    )


def _join_or_dash(names: list[str]) -> str:
    """Join a list of names with commas, or ``-`` for empty/None."""
    if not names:
        return "-"
    return ",".join(names)


def _audit_and_collect_row(
    profile_info: ProfileInfo,
    *,
    apply: bool,
    skip_install: bool,
    frozen_time: str | None,
) -> dict[str, object]:
    """Audit a single profile and backfill profile_name from ProfileInfo."""
    row = _audit_profile(
        profile_info.path,
        apply=apply,
        skip_install=skip_install,
        frozen_time=frozen_time,
        bilingual_fn=_bilingual,
    )
    # Backfill the profile_name from the ProfileInfo (in case
    # the path-based name was "hermes" by default).
    row["profile_name"] = profile_info.name
    _echo_row_summary(row)
    return row
