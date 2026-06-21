"""Bilingual help-text rendering helpers for the profiles CLI surface.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). The helpers here read the option-pair
tables and the per-language constants via direct attribute access to
the sub-modules (``_cli_profiles_cli_options`` / ``_cli_profiles_cli_flags``)
rather than via local re-binding, so this module's own surface stays
small.
"""

from __future__ import annotations

from collections.abc import Mapping

from hermes_skill_creator_plugin import _cli_profiles_cli_flags as _flags_mod
from hermes_skill_creator_plugin import _cli_profiles_cli_options as _opts_mod
from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU


def _format_options_block(
    options: tuple[tuple[str, str], ...],
    messages: Mapping[str, str],
) -> str:
    """Render an options block: ``  FLAG  description`` per line."""
    parts = [_format_option_line(flag, messages[key]) for flag, key in options]
    return "".join(parts)


def _format_option_line(flag: str, description: str) -> str:
    r"""Format a single ``  FLAG  description\n`` option line."""
    return f"  {flag}{description}\n"


def _build_en_help() -> str:
    """Build the English --help text body."""
    return (
        f"{EN['profiles_help_short']}\n\n"
        f"{_opts_mod.HELP_EN_HEADER}\n"
        f"{_opts_mod.EN_USAGE_BAR}\n\n"
        f"{EN['profiles_help_long']}\n\n"
        f"{_opts_mod.EN_SECTION}\n"
        f"{_format_options_block(_flags_mod._EN_OPTIONS, EN)}"
    )


def _build_hu_help() -> str:
    """Build the Hungarian --help text body."""
    return (
        f"{HU['profiles_help_short']}\n\n"
        f"{HU['profiles_help_long']}\n\n"
        f"{_opts_mod.HU_SECTION}\n"
        f"{_format_options_block(_flags_mod._HU_OPTIONS, HU)}"
    )


def build_help_text() -> str:
    """Build the bilingual --help text (two mirrored sections)."""
    return f"{_build_en_help()}\n{_build_hu_help()}"
