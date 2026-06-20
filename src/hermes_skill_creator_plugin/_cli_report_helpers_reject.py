"""Reject-flag helpers for the reporter CLI surface.

Split from ``_cli_report_helpers`` (WPS202 module surface budget). The
reject walk + per-arg matcher live here; the output / section / sort
helpers stay in ``_cli_report_helpers``.
"""

from __future__ import annotations

from types import MappingProxyType

REJECTED_FLAGS: MappingProxyType[str, str] = MappingProxyType(
    {
        "--apply": "apply",
        "--emit-migration-note": "emit-migration-note",
        "--write-report": "write-report",
    },
)


def reject_unwanted_flags(argv: list[str]) -> int | None:
    """Return reject_flag code if argv contains a rejected flag, else None."""
    sep = "="
    for arg in argv:
        reject_code = _reject_for_arg(arg, sep)
        if reject_code is not None:
            return reject_code
    return None


def _reject_for_arg(arg: str, sep: str) -> int | None:
    """Return the reject flag code for ``arg`` when it matches a rejected flag."""
    for prefix, key in REJECTED_FLAGS.items():
        with_eq = prefix + sep
        if arg == prefix or arg.startswith(with_eq):
            from hermes_skill_creator_plugin._cli_report_ui import (
                reject_flag as _reject,
            )

            return _reject(key)
    return None
