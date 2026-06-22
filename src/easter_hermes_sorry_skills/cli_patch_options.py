"""Click option-decoration helper for the patcher CLI.

Extracted from ``cli_patch.py`` to keep that module under wemake WPS202
(≤7 module members). Holds the single ``_add_click_option`` helper
plus the per-flag wiring of ``main``.
"""

from __future__ import annotations

import click


def _add_click_option(
    cmd: click.Command,
    flag: str,
    dest: str | None = None,
    is_flag_val: bool = False,
    default_val: object = None,
) -> click.Command:
    """Apply one ``click.option`` decorator to ``cmd`` and return the result."""
    help_text: tuple[str, ...] = ()
    if dest is None:
        return click.option(
            flag,
            type=click.Path() if default_val is None else None,
            default=default_val,
            is_flag=is_flag_val,
            help=help_text,
        )(cmd)
    return click.option(
        flag,
        dest,
        is_flag=is_flag_val,
        default=default_val,
        help=help_text,
    )(cmd)
