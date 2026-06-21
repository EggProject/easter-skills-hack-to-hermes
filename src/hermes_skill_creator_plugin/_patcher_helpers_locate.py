"""Multi-line anchor locator helper extracted from ``_patcher_helpers``.

Extracted so that the orchestrator's ``_patcher_helpers`` module stays
under the wemake WPS202 module-member cap (<=7) while supporting the
E4/E5 anchors (which carry real newline characters and span multiple
physical lines after the WPS342 fix).
"""

from __future__ import annotations

from hermes_skill_creator_plugin._patcher_sites import Anchor


def _lines_equal_at(file_lines: list[str], anchor_lines: list[str], start_idx: int) -> bool:
    span = len(anchor_lines)
    for offset in range(span):
        if file_lines[start_idx + offset] != anchor_lines[offset]:
            return False
    return True


def locate_anchor(text: str, anchor: Anchor) -> int:
    """Return the 1-based line number where ``anchor.text`` appears.

    Returns 0 when the anchor is not found. Matches the FULL line bytes
    (no implicit-concat normalization). If ``anchor.text`` spans multiple
    physical lines (contains real newline characters), matches against
    consecutive file lines starting at the candidate position.
    """
    file_lines = text.splitlines()
    anchor_lines = anchor.text.splitlines()
    span = len(anchor_lines)
    last_start = len(file_lines) - span
    for start_idx in range(last_start + 1):
        if _lines_equal_at(file_lines, anchor_lines, start_idx):
            return start_idx + 1
    return 0
