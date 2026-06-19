"""Migration-note render constants + helper functions.

Plain module (no submodule imports) so any submodule can import
from it without triggering circular-import chains.
"""

from __future__ import annotations

# Cap-raise row anchor (the primary 8+ char anchor for S1.cap).
# The 5-column schema is: site_id | location | current | replacement | anchor.
S1_CAP_ROW_ANCHOR = "if len(desc) > 60:"
# Default truncate widths for the ``current`` / ``replacement`` columns
# (per plans/08 §MIGRATION.hermes-patch.md row schema).
ANCHOR_COL_WIDTH = 60
INSERTION_COL_WIDTH = 80
# Replacement literal shown to operators (cap-row column).
MAX_DESC_LENGTH_HINT = (
    "`MAX_DESCRIPTION_LENGTH` defined locally, e.g. "
    "`MAX_DESCRIPTION_LENGTH = 1024`, to avoid a circular import from "
    "`tools.skills_tool`"
)
# Ellipsis character for _truncate().
ELLIPSIS_CHAR = "…"
# Raw-string newline escape for the markdown LF -> ``\\n`` rendering.
NEWLINE_ESCAPE = r"\n"
# Actual LF character (real newline).
LF = "\n"


def _truncate(text: str, max_len: int) -> str:
    """Escape LF and truncate to ``max_len`` (suffix with ellipsis when over)."""
    text = text.replace(LF, NEWLINE_ESCAPE)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + ELLIPSIS_CHAR
