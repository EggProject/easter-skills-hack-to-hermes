"""Total-row builder for the text-format reporter.

Extracted from :mod:`._reporter_format_text` to keep that file under
wemake WPS202 (module members <= 7). Provides ``_build_total_cells``,
the function that emits the bottom ``total`` row of a
``format_text`` table.
"""

from __future__ import annotations

from easter_hermes_sorry_skills._reporter_format_consts import (
    COL_PCT_OF_CAP,
    COL_PROFILE,
    COL_TOKENS,
)
from easter_hermes_sorry_skills._tokenizer import MAX_DESCRIPTION_LENGTH


def _build_total_cells(
    columns: tuple[str, ...],
    total_tokens: int,
) -> list[str]:
    """Build the bottom ``total`` row (profile=tokens=pct filled, rest blank)."""
    total_cells: list[str] = ["" for _ in columns]
    for idx, column_name in enumerate(columns):
        if column_name == COL_PROFILE:
            total_cells[idx] = "total"
        elif column_name == COL_TOKENS:
            total_tokens_str = str(total_tokens)
            total_cells[idx] = total_tokens_str
        elif column_name == COL_PCT_OF_CAP:
            pct_value = (total_tokens / MAX_DESCRIPTION_LENGTH) * 100
            total_cells[idx] = f"{pct_value:.1f}"
        else:
            total_cells[idx] = ""
    return total_cells
