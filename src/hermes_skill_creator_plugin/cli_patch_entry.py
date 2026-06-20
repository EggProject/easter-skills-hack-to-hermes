"""Module entry-point for the patcher CLI.

Split from ``cli_patch`` (WPS202 module surface budget). The
:func:`_main_entry` thin wrapper is kept here so test code can invoke
it without triggering click's process-exit side-effects.
"""

from __future__ import annotations

from hermes_skill_creator_plugin.cli_patch import main


def _main_entry() -> int:
    """Module entry point — extracted for testability."""
    main(standalone_mode=True)
    return 0
