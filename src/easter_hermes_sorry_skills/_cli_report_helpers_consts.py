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

HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Használat (magyar):"

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
