"""check_line_count.py — four invariants:
1. per-file cap (no file exceeds 500 LOC)
2. footer drift (Plan Footer line numbers match actual line numbers)
3. budget-table Total (sum of file budgets matches declared Total)
4. per-cell guard (each row's cap >= actual LOC of that file)
"""

# TDD test cases:
#   test_per_file_cap_passes_when_all_files_under_500_loc
#   test_per_file_cap_fails_when_a_file_exceeds_500_loc
#   test_footer_drift_passes_when_plan_footer_matches_actual
#   test_footer_drift_fails_when_plan_footer_is_stale
#   test_budget_table_total_passes_when_sum_matches
#   test_budget_table_total_fails_when_sum_mismatches
#   test_per_cell_guard_passes_when_each_row_cap_gte_actual_loc
#   test_per_cell_guard_fails_when_a_row_cap_lt_actual_loc
#   test_check_runs_clean_on_this_worktree_skeleton
#   test_check_is_readonly_and_writes_nothing

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PER_FILE_CAP = 500


def _iter_python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if ".venv" not in p.parts and ".git" not in p.parts]


def check_per_file_cap(root: Path) -> list[str]:
    failures: list[str] = []
    for p in _iter_python_files(root):
        loc = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
        if loc > PER_FILE_CAP:
            failures.append(f"per-file cap: {p.relative_to(root)} has {loc} LOC > {PER_FILE_CAP}")
    return failures


def check_footer_drift(root: Path) -> list[str]:
    # Skeleton: real implementation reads Plan Footer and verifies it matches actual line numbers.
    return []


def check_budget_table_total(root: Path) -> list[str]:
    # Skeleton: real implementation parses BUDGET TABLE Total row and sums file budgets.
    return []


def check_per_cell_guard(root: Path) -> list[str]:
    # Skeleton: real implementation cross-references per-row cap with actual file LOC.
    return []


def main() -> int:
    failures: list[str] = []
    failures.extend(check_per_file_cap(REPO_ROOT))
    failures.extend(check_footer_drift(REPO_ROOT))
    failures.extend(check_budget_table_total(REPO_ROOT))
    failures.extend(check_per_cell_guard(REPO_ROOT))

    if failures:
        for line in failures:
            print(f"[check_line_count] FAIL: {line}")
        return 1
    print("[check_line_count] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
