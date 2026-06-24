"""(flag_label, i18n_key) option-pair tuples for the profiles CLI.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). The tuples here are pure data and never
import anything runtime-heavy.
"""

from __future__ import annotations

_EN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply", "profiles_opt_apply"),
    ("--dry-run", "profiles_opt_dry_run"),
    ("--audit", "profiles_opt_audit"),
    ("--yes", "profiles_opt_yes"),
    ("--skip-install", "profiles_opt_skip_install"),
    ("--verbose", "profiles_opt_verbose"),
    ("--profile NAME", "profiles_opt_profile"),
    ("--json PATH", "profiles_opt_json"),
    ("--help", "profiles_opt_help"),
)
_HU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--apply", "profiles_opt_apply"),
    ("--dry-run", "profiles_opt_dry_run"),
    ("--audit", "profiles_opt_audit"),
    ("--yes", "profiles_opt_yes"),
    ("--skip-install", "profiles_opt_skip_install"),
    ("--verbose", "profiles_opt_verbose"),
    ("--profile NÉV", "profiles_opt_profile"),
    ("--json ÚTVONAL", "profiles_opt_json"),
    ("--help", "profiles_opt_help"),
)
