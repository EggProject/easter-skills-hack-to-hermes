"""(flag_label, i18n_key) option-pair tuples for the profiles CLI.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). The tuples here are pure data and never
import anything runtime-heavy.
"""

from __future__ import annotations

_EN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--dry-run", "profiles_opt_dry_run"),
    ("--verbose", "profiles_opt_verbose"),
    ("--profile NAME", "profiles_opt_profile"),
    ("--help", "profiles_opt_help"),
)
_HU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--dry-run", "profiles_opt_dry_run"),
    ("--verbose", "profiles_opt_verbose"),
    ("--profile NÉV", "profiles_opt_profile"),
    ("--help", "profiles_opt_help"),
)
