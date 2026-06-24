"""Option-table constants and per-language help-section headers for the
profiles CLI surface.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). The constants here are pure data and never
import anything runtime-heavy, so importing them from the CLI surface
costs one extra import line in exchange for a smaller module surface.

Module members are kept under WPS202 by exposing only the named tables
that ``_cli_profiles_cli.py`` actually reads.
"""

from __future__ import annotations

# Header labels for the bilingual --help sections.
HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"
EN_SECTION = "Options:"
HU_SECTION = "Kapcsolók:"
EN_USAGE_BAR = (
    "  easter-hermes-sorry-skills-profiles [--dry-run] [--verbose]\n"
    "                                  [--profile NAME] [--help]"
)
HU_USAGE_BAR = (
    "  easter-hermes-sorry-skills-profiles [--dry-run] [--verbose]\n"
    "                                  [--profile NÉV] [--help]"
)
