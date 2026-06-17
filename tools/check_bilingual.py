"""check_bilingual.py — enforce that all console messages are bilingual
(en/hu on a single line: '[en] ... / [hu] ...').

Skeletal implementation: only the entry point and TDD contract live here.
The full detector is added in a later Phase 5 iteration of the F-meta workstream.
"""

# TDD test cases:
#   test_console_message_with_both_locales_passes
#   test_console_message_missing_hu_fails
#   test_console_message_missing_en_fails
#   test_console_message_with_hu_on_separate_line_fails
#   test_click_echo_calls_in_src_have_bilingual_argument
#   test_help_text_has_english_and_magyar_sections
#   test_check_runs_clean_on_this_worktree_skeleton

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    # Skeleton: real checks are added in a later F-meta iteration.
    # For now, treat the skeleton as clean so pre-commit doesn't false-positive
    # before the detector is implemented.
    src = REPO_ROOT / "src" / "hermes_skill_creator_plugin"
    if not src.exists():
        print("[check_bilingual] SKIP: src/ not yet present")
        return 0
    print("[check_bilingual] OK (skeleton)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
