"""scripts/utils.py — shared helpers for the migrated skill-creator scripts.

Bilingual console messages (single-line `[en] ... / [hu] ...`).

TDD test cases for this module:
  test_emit_bilingual_console_emits_en_then_hu_on_one_line
  test_emit_bilingual_console_format_matches_regex
  test_emit_bilingual_console_handles_no_args
  test_emit_bilingual_console_writes_to_stdout
  test_help_section_english_and_magyar_both_present
  test_help_section_mirrors_options
"""

from __future__ import annotations

import sys
from typing import Any

BILINGUAL_PATTERN = r"^\[en\] .+ / \[hu\] .+$"


def emit(en: str, hu: str) -> None:
    """Print a bilingual console message on a single line: `[en] ... / [hu] ...`.

    Args:
        en: English message.
        hu: Hungarian message.
    """
    sys.stdout.write(f"[en] {en} / [hu] {hu}\n")
    sys.stdout.flush()


def bilingual_help(english: str, magyar: str) -> str:
    """Return a two-section help string with mirrored content.

    The returned string contains both `Usage (English)` and `Hasznalat (magyar)`
    sections. The English and Magyar option tables are provided by the caller
    in the `english` and `magyar` arguments; this helper joins them with
    bilingual section headers.

    Args:
        english: English help text (e.g. argparse --help formatted).
        magyar: Hungarian help text (e.g. argparse --help in hu).

    Returns:
        A string with two top-level sections in order: English first, Magyar
        second. Both sections are present so the bilingual help test passes.
    """
    return (
        "Usage (English)\n"
        "---------------\n"
        f"{english}\n"
        "\n"
        "Hasznalat (magyar)\n"
        "------------------\n"
        f"{magyar}\n"
    )


def parse_args_and_emit_help(parser: Any, *, en_help: str, hu_help: str) -> None:
    """If `--help` is in argv, print the bilingual help and exit 0.

    Helper for click-style or argparse-style CLIs that want bilingual help.
    """
    if "--help" in sys.argv or "-h" in sys.argv:
        sys.stdout.write(bilingual_help(en_help, hu_help))
        sys.exit(0)


__all__ = ["BILINGUAL_PATTERN", "emit", "bilingual_help", "parse_args_and_emit_help"]
