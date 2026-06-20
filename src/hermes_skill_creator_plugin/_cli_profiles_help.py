"""Bilingual --help text builders for the cli_profiles click surface.

Split from ``_cli_profiles_cli`` (WPS202 module surface budget). The
EN/HU option tables + the per-section formatters live here.
"""

from __future__ import annotations

from collections.abc import Mapping

from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

# Header labels for the bilingual --help sections.
HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"
EN_SECTION = "Options:"
HU_SECTION = "Kapcsolók:"
EN_USAGE_BAR = (
    "  hermes-skill-creator-profiles [--apply] [--audit] [--profile NAME]\n"
    "                                  [--json PATH] [--yes] [--skip-install]\n"
    "                                  [--frozen-time ISO] [--help]"
)
HU_USAGE_BAR = (
    "  hermes-skill-creator-profiles [--apply] [--audit] [--profile NÉV]\n"
    "                                  [--json ÚTVONAL] [--yes] [--skip-install]\n"
    "                                  [--frozen-time ISO] [--help]"
)

# (flag_label, i18n_key) pairs — kept short to keep WPS221 quiet.
_EN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply            ", "profiles_opt_apply"),
    ("--audit            ", "profiles_opt_audit"),
    ("--profile NAME     ", "profiles_opt_profile"),
    ("--json PATH        ", "profiles_opt_json"),
    ("--yes              ", "profiles_opt_yes"),
    ("--skip-install     ", "profiles_opt_skip_install"),
    ("--frozen-time ISO  ", "profiles_opt_frozen_time"),
    ("--help             ", "profiles_opt_help"),
)
_HU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply            ", "profiles_opt_apply"),
    ("--profile NÉV      ", "profiles_opt_profile"),
    ("--json ÚTVONAL     ", "profiles_opt_json"),
    ("--yes              ", "profiles_opt_yes"),
    ("--skip-install     ", "profiles_opt_skip_install"),
    ("--frozen-time ISO  ", "profiles_opt_frozen_time"),
    ("--help             ", "profiles_opt_help"),
)


def _format_options_block(
    options: tuple[tuple[str, str], ...],
    messages: Mapping[str, str],
) -> str:
    """Render an options block: ``  FLAG  description`` per line."""
    parts = [_format_option_line(flag, messages[key]) for flag, key in options]
    return "".join(parts)


def _format_option_line(flag: str, description: str) -> str:
    """Format a single ``  FLAG  description\\n`` option line."""
    return f"  {flag}{description}\n"


def _build_en_help() -> str:
    """Build the English --help text body."""
    return (
        f"{EN['profiles_help_short']}\n\n"
        f"{HELP_EN_HEADER}\n"
        f"{EN_USAGE_BAR}\n\n"
        f"{EN['profiles_help_long']}\n\n"
        f"{EN_SECTION}\n"
        f"{_format_options_block(_EN_OPTIONS, EN)}"
    )


def _build_hu_help() -> str:
    """Build the Hungarian --help text body."""
    return (
        f"{HU['profiles_help_short']}\n\n"
        f"{HELP_HU_HEADER}\n"
        f"{HU_USAGE_BAR}\n\n"
        f"{HU['profiles_help_long']}\n\n"
        f"{HU_SECTION}\n"
        f"{_format_options_block(_HU_OPTIONS, HU)}"
    )


_HELP_SECTION_SEP = "\n"


def build_help_text() -> str:
    """Build the bilingual --help text (two mirrored sections)."""
    return f"{_build_en_help()}{_HELP_SECTION_SEP}{_build_hu_help()}"
