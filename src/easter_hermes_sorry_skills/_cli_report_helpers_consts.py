"""Constants for the reporter CLI helpers.

Extracted from ``_cli_report_helpers.py`` to keep that module under wemake
WPS202 (≤7 module members).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

REJECTED_FLAGS: MappingProxyType[str, str] = MappingProxyType(
    {
        "--apply": "apply",
        "--emit-migration-note": "emit-migration-note",
        "--write-report": "write-report",
    },
)

HELP_EN_HEADER = (
    "Per-profile READ-ONLY report for the migrated skill-creator skill.\n"
    "Walks every Hermes profile and prints a bilingual EN/HU report."
)

HELP_HU_HEADER = (
    "Profilonkénti CSAK OLVASÁS riport a migrált skill-creator skillhez.\n"
    "Végigmegy minden Hermes profil és kétnyelvű EN/HU riportot ír."
)

_EN_DESCRIPTIONS: MappingProxyType[str, str] = MappingProxyType(
    {
        "--profile": (
            "Report a single profile; default iterates the `hermes` (default) profile AND every named profile."
        ),
        "--sort": "Reorder rows: tokens | use_count | last_used_at. Default: tokens.",
        "--format": "Output format: text (default) | json.",
        "--json": ("Write the report to PATH (default: ./skill-report.json when --format=json; otherwise ignored)."),
        "--verbose": ("Print detailed per-cell diagnostics to stderr (every cell value + section summary)."),
        "--help": "Show this message and exit.",
    },
)
_HU_DESCRIPTIONS: MappingProxyType[str, str] = MappingProxyType(
    {
        "--profile": (
            "Egyetlen profil riportja; alapértelmezetten a `hermes` (alap) profil ÉS minden elnevezett profil."
        ),
        "--sort": ("Sorok rendezése: tokens | use_count | last_used_at. Alapértelmezett: tokens."),
        "--format": "Kimeneti formátum: text (alapértelmezett) | json.",
        "--json": (
            "A riport kiírása PATH-ba (alapértelmezett: ./skill-report.json, "
            "ha --format=json; egyébként figyelmen kívül hagyva)."
        ),
        "--verbose": (
            "Részletes cella-szintű diagnosztika kiírása stderr-re (minden cellaérték + szekció-összefoglaló)."
        ),
        "--help": "Megjeleníti ezt az üzenetet és kilép.",
    },
)

EMPTY_USAGE: MappingProxyType[str, Any | None] = MappingProxyType(
    {
        "use_count": None,
        "view_count": None,
        "patch_count": None,
        "last_used_at": None,
        "last_viewed_at": None,
        "last_patched_at": None,
    },
)
PERSISTED_KEY = "_persisted"

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SORT_TOKENS = "tokens"
SORT_KEYS: tuple[str, ...] = (SORT_TOKENS, "use_count", "last_used_at")
FORMAT_KEYS: tuple[str, ...] = (FORMAT_TEXT, FORMAT_JSON)
TOOL_NAME = "easter-hermes-sorry-skills-report"
TOOL_VERSION = "0.1.0"
DEFAULT_JSON_NAME = "./skill-report.json"

LANG_EN = "en"
LANG_HU = "hu"
LANG_OPT_DESC_EN = "Help language (en or hu)."
LANG_OPT_DESC_HU = "Súgó nyelve (en vagy hu)."
OPTIONS_HEADER_EN = "Options"
OPTIONS_HEADER_HU = "Opciók"


def resolve_descriptions(lang: str) -> MappingProxyType[str, str]:
    """Return the lang-specific option description map."""
    return _HU_DESCRIPTIONS if lang == LANG_HU else _EN_DESCRIPTIONS


def resolve_lang_opt_desc(lang: str) -> str:
    """Return the lang-specific ``--lang`` option description."""
    return LANG_OPT_DESC_HU if lang == LANG_HU else LANG_OPT_DESC_EN


def options_header(lang: str) -> str:
    """Return the lang-specific ``Options:`` / ``Opciók:`` section header."""
    return OPTIONS_HEADER_HU if lang == LANG_HU else OPTIONS_HEADER_EN


def help_header(lang: str) -> str:
    """Return the lang-specific short help header (HELP_EN_HEADER / HELP_HU_HEADER)."""
    return HELP_HU_HEADER if lang == LANG_HU else HELP_EN_HEADER
