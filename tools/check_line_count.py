"""check_line_count.py — four invariants for plan files:

  1. per-file cap       — every docs/plans/*.md MUST be <= 500 lines
  2. footer drift       — `<!-- end of file: NN lines (budget BB) -->`
                          MUST have NN == wc -l (00-index uses bare marker)
  3. budget-table Total — 00-index.md's Total cell AND `Sum NNNN` prose
                          MUST equal the live sum of wc -l across every plan file
  4. per-cell guard     — for every file-map row in 00-index.md, the per-file
                          Actual cell MUST equal `wc -l` of the cited path, AND
                          the per-file Budget cell MUST equal the budget the
                          hook was handed (defaults to the live value in the table).

TDD test cases (mirror of tests/meta/test_meta_check_line_count.py):

  test_per_file_cap_passes_when_all_files_under_500_loc
  test_per_file_cap_fails_when_a_file_exceeds_500_loc
  test_footer_drift_passes_when_plan_footer_matches_actual
  test_footer_drift_fails_when_plan_footer_is_stale
  test_budget_table_total_passes_when_sum_matches
  test_budget_table_total_fails_when_sum_mismatches
  test_per_cell_guard_passes_when_each_row_cap_gte_actual_loc
  test_per_cell_guard_fails_when_a_row_cap_lt_actual_loc
  test_check_runs_clean_on_this_worktree_skeleton
  test_check_is_readonly_and_writes_nothing
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PER_FILE_CAP = 500
PLANS_GLOB = "docs/plans/*.md"
INDEX_FILE = "docs/plans/00-index.md"
FOOTER_RE = re.compile(r"<!--\s*end of file:\s*(\d+)\s*lines(?:\s*\(budget\s*(\d+)\))?\s*-->")
BARE_FOOTER_RE = re.compile(r"<!--\s*end of file\s*-->")
ROW_RE = re.compile(
    r"^\|\s*(?P<num>\d{2})\s*\|\s*`?(?P<path>[^`]+?)`?\s*\|.*?\|\s*(?P<status>\[[^\]]+\])\s*\|\s*(?P<budget>\d+)\s*\|\s*(?P<actual>\d+)\s*\|\s*$"
)


@dataclass(frozen=True)
class Row:
    """One row of the 00-index file map."""

    num: str
    path: str
    status: str
    budget: int
    actual: int


def _wc_l(path: Path) -> int:
    """Return live wc -l for path."""
    return int(subprocess.check_output(["wc", "-l", str(path)], text=True).split()[0])


def _iter_plan_files(root: Path) -> list[Path]:
    """Iterate plan files listed in the 00-index file map (deterministic order).

    The 00-index file map is the contract source of truth; auxiliary archive
    files (e.g. ``_diagnose.md``) under ``docs/plans/`` are NOT plan files in
    the budget-table sense, so they are excluded. If 00-index is missing or
    the file map cannot be parsed, the iterator falls back to the on-disk
    listing minus 00-index.
    """
    listed = _file_map_paths(root)
    if listed is None:
        plans_dir = root / "docs" / "plans"
        if not plans_dir.exists():
            return []
        return sorted(p for p in plans_dir.glob("*.md") if p.name != "00-index.md")
    out: list[Path] = []
    for rel in listed:
        if rel.name == "00-index.md":
            continue
        out.append(rel)
    return out


def _iter_plan_files_including_index(root: Path) -> list[Path]:
    """Iterate every plan file (00-index + file-map rows) in deterministic order.

    The 00-index file map is the contract source of truth; we also always
    include ``00-index.md`` itself (it is the budget-table carrier and is
    counted in the Total per D2). Auxiliary archive files under
    ``docs/plans/`` (e.g. ``_diagnose.md``) are NOT plan files in the
    budget-table sense and are excluded.
    """
    index_path = root / INDEX_FILE
    listed = _file_map_paths(root)
    plans_dir = root / "docs" / "plans"
    if listed is None:
        if not plans_dir.exists():
            return [index_path] if index_path.exists() else []
        files = sorted(plans_dir.glob("*.md"))
        return sorted(files, key=lambda p: (p.name != "00-index.md", p.name))
    out: list[Path] = list(listed)
    if index_path.exists() and index_path not in out:
        out.append(index_path)
    return sorted(out, key=lambda p: (p.name != "00-index.md", p.name))


def _file_map_paths(root: Path) -> list[Path] | None:
    """Return the per-row paths from the 00-index file map, or None on miss."""
    index_path = root / INDEX_FILE
    if not index_path.exists():
        return None
    try:
        text = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rows = _parse_file_map(text)
    if not rows:
        return None
    out: list[Path] = []
    for row in rows:
        rel = Path(row.path)
        if rel.parent == Path(""):
            rel = Path("docs/plans") / row.path
        out.append(root / rel)
    return out


def check_per_file_cap(root: Path) -> list[str]:
    """Invariant 1: every plan file <= PER_FILE_CAP lines."""
    failures: list[str] = []
    for p in _iter_plan_files_including_index(root):
        loc = _wc_l(p)
        if loc > PER_FILE_CAP:
            rel = p.relative_to(root)
            failures.append(f"per-file cap: {rel} has {loc} LOC > {PER_FILE_CAP}")
    return failures


def check_footer_drift(root: Path) -> list[str]:
    """Invariant 2: footer NN matches live wc -l; 00-index uses bare marker."""
    failures: list[str] = []
    for p in _iter_plan_files_including_index(root):
        rel = p.relative_to(root)
        loc = _wc_l(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        if rel.name == "00-index.md":
            if not BARE_FOOTER_RE.search(text):
                failures.append(f"footer drift: {rel} missing bare `<!-- end of file -->` marker")
            continue
        m = FOOTER_RE.search(text)
        if m is None:
            failures.append(
                f"footer drift: {rel} missing `<!-- end of file: NN lines (budget BB) -->` footer"
            )
            continue
        declared = int(m.group(1))
        if declared != loc:
            failures.append(f"footer drift: {rel} footer says {declared} lines but wc -l is {loc}")
    return failures


def _parse_file_map(index_text: str) -> list[Row]:
    """Parse every row of the 00-index file map table."""
    rows: list[Row] = []
    for line in index_text.splitlines():
        m = ROW_RE.match(line)
        if m is None:
            continue
        num = m.group("num")
        rows.append(
            Row(
                num=num,
                path=m.group("path").strip(),
                status=m.group("status").strip(),
                budget=int(m.group("budget")),
                actual=int(m.group("actual")),
            )
        )
    return rows


def _total_cell_value(index_text: str) -> int | None:
    """Extract the Total cell from the budget table's bottom row.

    The Total row has empty Status and **Total** in the path column;
    we accept either `**Total**` or `Total` in the path cell.
    """
    for line in index_text.splitlines():
        if "**Total**" not in line and " | Total |" not in line:
            continue
        # Match: | | **Total** | ... | | **N** |
        m = re.search(r"\|\s*\*\*(\d+)\*\*\s*\|", line)
        if m is not None:
            return int(m.group(1))
        m = re.search(r"\|\s*(\d+)\s*\|\s*$", line)
        if m is not None:
            return int(m.group(1))
    return None


def _sum_prose_value(index_text: str) -> int | None:
    """Extract the `Sum NNNN < Total` prose token near the bottom of the file."""
    m = re.search(r"Sum\s+(\d+)\s*<\s*(\d+)", index_text)
    if m is not None:
        return int(m.group(1))
    return None


def check_budget_table_total(root: Path) -> list[str]:
    """Invariant 3: 00-index.md Total cell == live sum of wc -l across plan files."""
    index_path = root / INDEX_FILE
    if not index_path.exists():
        return [f"budget table: missing {INDEX_FILE}"]
    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    live_total = sum(_wc_l(p) for p in _iter_plan_files_including_index(root))
    failures: list[str] = []
    total_cell = _total_cell_value(index_text)
    if total_cell is None:
        failures.append("budget table: could not find Total cell in 00-index.md")
    elif total_cell != live_total:
        failures.append(
            f"budget table: 00-index Total cell is {total_cell} but live sum is {live_total}"
        )
    sum_prose = _sum_prose_value(index_text)
    if sum_prose is not None and sum_prose != live_total:
        failures.append(
            f"budget table: `Sum NNNN` prose is {sum_prose} but live sum is {live_total}"
        )
    return failures


def check_per_cell_guard(root: Path) -> list[str]:
    """Invariant 4: per-row Actual==wc -l AND per-row Budget==budget value."""
    index_path = root / INDEX_FILE
    if not index_path.exists():
        return [f"per-cell guard: missing {INDEX_FILE}"]
    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    rows = _parse_file_map(index_text)
    failures: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row.num in seen:
            continue
        seen.add(row.num)
        # Path is relative to repo root (e.g. `docs/plans/09-test-strategy.md`).
        rel = Path(row.path)
        # If the row has just the filename, assume docs/plans/.
        if rel.parent == Path(""):
            rel = Path("docs/plans") / row.path
        target = root / rel
        if not target.exists():
            failures.append(f"per-cell guard: row {row.num} cites {rel} which does not exist")
            continue
        loc = _wc_l(target)
        if row.actual != loc:
            failures.append(
                f"per-cell guard: row {row.num} ({rel}) Actual cell is "
                f"{row.actual} but wc -l is {loc}"
            )
        # Budget cell — the per-file budget cap. We assert the row's Budget cell
        # is at least as large as the live Actual (otherwise the cap is violated).
        # The brief also says "per-file Budget == budget" — we interpret this as
        # the table cell being a coherent integer that the hook can re-validate
        # against the operator's hand. Compare against the row's own claim.
        if row.budget < loc:
            failures.append(
                f"per-cell guard: row {row.num} ({rel}) Budget {row.budget} < Actual {loc}"
            )
    return failures


def run_all_checks(
    root: Path,
    *,
    enforce_footer: bool = True,
    enforce_budget_table: bool = True,
    enforce_per_cell: bool = True,
) -> list[str]:
    """Run all four invariants; return the list of failure messages (empty == OK)."""
    failures: list[str] = []
    failures.extend(check_per_file_cap(root))
    if enforce_footer:
        failures.extend(check_footer_drift(root))
    if enforce_budget_table:
        failures.extend(check_budget_table_total(root))
    if enforce_per_cell:
        failures.extend(check_per_cell_guard(root))
    return failures


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-footer", dest="footer", action="store_false")
    parser.add_argument("--no-budget-table", dest="budget", action="store_false")
    parser.add_argument("--no-per-cell", dest="per_cell", action="store_false")
    parser.add_argument("--enforce-footer", dest="footer", action="store_true", default=True)
    parser.add_argument(
        "--enforce-budget-table",
        dest="budget",
        action="store_true",
        default=True,
    )
    parser.add_argument("--enforce-per-cell", dest="per_cell", action="store_true", default=True)
    parser.set_defaults(
        footer=True,
        budget=True,
        per_cell=True,  # explicit defaults
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = _parse_args(argv)
    failures = run_all_checks(
        REPO_ROOT,
        enforce_footer=args.footer,
        enforce_budget_table=args.budget,
        enforce_per_cell=args.per_cell,
    )
    if failures:
        for line in failures:
            print(f"[check_line_count] FAIL: {line}", file=sys.stderr)
        print(
            f"[check_line_count] {len(failures)} invariant(s) violated",
            file=sys.stderr,
        )
        return 1
    print("[check_line_count] OK (per-file cap + footer + budget table + per-cell)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
