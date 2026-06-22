"""Column-name + group constants for the reporter format helpers.

Extracted from :mod:`._reporter_format` to keep the parent under wemake
WPS202 (module members <= 7).
"""

from __future__ import annotations

# Column-name constants (extracted to keep WPS226 quiet; used in the
# ``_format_value_for_text`` dispatch + the ``format_text`` total row).
COL_PROFILE = "profile"
COL_NAME = "name"
COL_DESCRIPTION = "description"
COL_TOKENS = "tokens"
COL_USE_COUNT = "use_count"
COL_VIEW_COUNT = "view_count"
COL_PATCH_COUNT = "patch_count"
COL_LAST_USED_AT = "last_used_at"
COL_LAST_VIEWED_AT = "last_viewed_at"
COL_LAST_PATCHED_AT = "last_patched_at"
COL_PCT_OF_CAP = "pct_of_cap"
NA_TEXT = "n/a"

# Default columns tuple (mirrors ``_reporter.TEXT_COLUMNS``); we can't
# import the constant from ``_reporter`` here (circular import risk), so
# it is duplicated. Keep both definitions in lock-step.
DEFAULT_TEXT_COLUMNS: tuple[str, ...] = (
    COL_PROFILE,
    COL_NAME,
    COL_DESCRIPTION,
    COL_TOKENS,
    COL_USE_COUNT,
    COL_VIEW_COUNT,
    COL_PATCH_COUNT,
    COL_LAST_USED_AT,
    COL_LAST_VIEWED_AT,
    COL_LAST_PATCHED_AT,
    COL_PCT_OF_CAP,
)

_COUNT_COLUMNS: frozenset[str] = frozenset((COL_USE_COUNT, COL_VIEW_COUNT, COL_PATCH_COUNT))
_TIMESTAMP_COLUMNS: frozenset[str] = frozenset(
    (COL_LAST_USED_AT, COL_LAST_VIEWED_AT, COL_LAST_PATCHED_AT),
)

# Public aliases for sibling-module imports.
COUNT_COLUMNS = _COUNT_COLUMNS
TIMESTAMP_COLUMNS = _TIMESTAMP_COLUMNS
