"""scripts/utils.py — shared helpers for the migrated skill-creator scripts.

Bilingual console messages (single-line `[en] ... / [hu] ...`).

TDD test cases for this module:
  test_emit_bilingual_console_emits_en_then_hu
  test_console_log_lines_match_bilingual_regex
"""

from __future__ import annotations

import sys

BILINGUAL_PATTERN = r"^\[en\] .+ / \[hu\] .+$"


def emit(en: str, hu: str) -> None:
    """Print a bilingual console message on a single line: `[en] ... / [hu] ...`.

    Args:
        en: English message.
        hu: Hungarian message.
    """
    sys.stdout.write(f"[en] {en} / [hu] {hu}\n")
    sys.stdout.flush()


__all__ = ["BILINGUAL_PATTERN", "emit"]
