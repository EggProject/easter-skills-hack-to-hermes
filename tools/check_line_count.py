"""check_line_count.py — four invariants for plan files:

  1. per-file cap       — every docs/plans/*.md MUST be <= 500 lines
  2. footer drift       — `<!-- end of file: NN lines (budget BB) -->`
                          MUST have NN == wc -l (00-index uses bare marker)
  3. budget-table Total — 00-index.md's Total cell AND `Sum NNNN` prose
                          MUST equal the live sum of wc -l across every plan
  4. per-cell guard     — for every file-map row in 00-index.md, Actual MUST
                          equal `wc -l`, Budget MUST equal the cell value.

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
PLANS_DIR_PARTS = ("docs", "plans")
INDEX_FILE = "docs/plans/00-index.md"
INDEX_BASENAME = "00-index.md"
WC_BIN = "wc"
WC_L_FLAG = "-l"

FOOTER_RE = re.compile(
    r"<!--\s*end of file:\s*(\d+)\s*lines(?:\s*\(budget\s*(\d+)\))?\s*-->",
)
BARE_FOOTER_RE = re.compile(r"<!--\s*end of file\s*-->")
ROW_RE = re.compile(
    r"^\|\s*(?P<num>\d{2})\s*\|"
    r"\s*`?(?P<path>[^`]+?)`?\s*\|"
    r".*?"
    r"\|\s*(?P<status>\[[^\]]+\])\s*\|"
    r"\s*(?P<budget>\d+)\s*\|"
    r"\s*(?P<actual>\d+)\s*\|\s*$",
)
TOTAL_BOLD_RE = re.compile(r"\|\s*\*\*(\d+)\*\*\s*\|")
TOTAL_PLAIN_RE = re.compile(r"\|\s*(\d+)\s*\|\s*$")
TOTAL_BOLD_MARKER = "**Total**"
TOTAL_PLAIN_MARKER = " | Total |"
SUM_PROSE_RE = re.compile(r"Sum\s+(\d+)\s*<\s*(\d+)")


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
    out = subprocess.check_output(
        [WC_BIN, WC_L_FLAG, str(path)],
        text=True,
    )
    return int(out.split()[0])


def _iter_plan_files(root: Path) -> list[Path]:
    """Iterate plan files in 00-index file map (deterministic order).

    Auxiliary archive files (e.g. ``_diagnose.md``) under ``docs/plans/``
    are NOT plan files in the budget-table sense and are excluded. If
    00-index is missing or the file map cannot be parsed, the iterator
    falls back to the on-disk listing minus 00-index.
    """
    listed = _file_map_paths(root)
    if listed is None:
        return _fallback_plan_glob(root)
    return [rel for rel in listed if rel.name != INDEX_BASENAME]


def _fallback_plan_glob(root: Path) -> list[Path]:
    """Return on-disk plan listing, sorted, minus 00-index."""
    plans_dir = Path(root, *PLANS_DIR_PARTS)
    if not plans_dir.exists():
        return []
    return sorted(p for p in plans_dir.glob("*.md") if p.name != INDEX_BASENAME)


def _iter_plan_files_including_index(root: Path) -> list[Path]:
    """Iterate every plan file (00-index + file-map rows), deterministic.

    The 00-index file map is the contract source of truth; we always also
    include ``00-index.md`` itself (it is the budget-table carrier and is
    counted in the Total per D2). Archive files like ``_diagnose.md`` are
    excluded.
    """
    listed = _file_map_paths(root)
    index_path = root / INDEX_FILE
    if listed is None:
        return _fallback_including_index(root, index_path)
    out: list[Path] = list(listed)
    if index_path.exists() and index_path not in out:
        out.append(index_path)
    return sorted(out, key=lambda p: (p.name != INDEX_BASENAME, p.name))


def _fallback_including_index(root: Path, index_path: Path) -> list[Path]:
    """Return on-disk plan listing sorted, with 00-index first."""
    plans_dir = Path(root, *PLANS_DIR_PARTS)
    if not plans_dir.exists():
        return [index_path] if index_path.exists() else []
    files = sorted(plans_dir.glob("*.md"))
    return sorted(files, key=lambda p: (p.name != INDEX_BASENAME, p.name))


def _file_map_paths(root: Path) -> list[Path] | None:
    """Return the per-row paths from the 00-index file map, or None on miss."""
    index_path = root / INDEX_FILE
    if not index_path.exists():
        return None
    try:
        text = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return _paths_from_rows(_parse_file_map(text), root)


def _paths_from_rows(rows: list[Row], root: Path) -> list[Path] | None:
    """Map Row.path values to absolute Path; None when no rows."""
    if not rows:
        return None
    out: list[Path] = []
    for row in rows:
        rel = _normalize_row_path(row.path)
        out.append(root / rel)
    return out


def _normalize_row_path(raw: str) -> Path:
    """If the row's path is bare, prefix it with docs/plans/."""
    rel = Path(raw)
    if rel.parent == Path(""):
        return Path(*PLANS_DIR_PARTS) / raw
    return rel


def check_per_file_cap(root: Path) -> list[str]:
    """Invariant 1: every plan file <= PER_FILE_CAP lines."""
    failures: list[str] = []
    for p in _iter_plan_files_including_index(root):
        loc = _wc_l(p)
        if loc > PER_FILE_CAP:
            rel = p.relative_to(root)
            msg = f"per-file cap: {rel} has {loc} LOC > {PER_FILE_CAP}"
            failures.append(msg)
    return failures


def _check_index_bare_marker(rel: Path, text: str) -> list[str]:
    """00-index.md MUST carry a bare `<!-- end of file -->` marker."""
    if BARE_FOOTER_RE.search(text):
        return []
    return [
        f"footer drift: {rel} missing bare `<!-- end of file -->` marker",
    ]


def _check_footer_for_file(rel: Path, text: str, loc: int) -> list[str]:
    """One non-index plan file MUST have a declared footer matching wc -l."""
    m = FOOTER_RE.search(text)
    if m is None:
        prefix = "footer drift: "
        suffix = f"{rel} missing `<!-- end of file: NN lines` footer"
        return [prefix + suffix]
    declared = int(m.group(1))
    if declared == loc:
        return []
    return [
        f"footer drift: {rel} footer says {declared} lines but wc -l is {loc}",
    ]


def check_footer_drift(root: Path) -> list[str]:
    """Invariant 2: footer NN matches live wc -l; 00-index uses bare marker."""
    failures: list[str] = []
    for p in _iter_plan_files_including_index(root):
        rel = p.relative_to(root)
        loc = _wc_l(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        if rel.name == INDEX_BASENAME:
            failures.extend(_check_index_bare_marker(rel, text))
            continue
        failures.extend(_check_footer_for_file(rel, text, loc))
    return failures


def _parse_file_map(index_text: str) -> list[Row]:
    """Parse every row of the 00-index file map table."""
    rows: list[Row] = []
    for line in index_text.splitlines():
        m = ROW_RE.match(line)
        if m is None:
            continue
        rows.append(
            Row(
                num=m.group("num"),
                path=m.group("path").strip(),
                status=m.group("status").strip(),
                budget=int(m.group("budget")),
                actual=int(m.group("actual")),
            ),
        )
    return rows


def _total_cell_value(index_text: str) -> int | None:
    """Extract the Total cell from the budget table's bottom row.

    The Total row has empty Status and **Total** in the path column;
    we accept either `**Total**` or `Total` in the path cell.
    """
    for line in index_text.splitlines():
        if TOTAL_BOLD_MARKER not in line and TOTAL_PLAIN_MARKER not in line:
            continue
        bold = TOTAL_BOLD_RE.search(line)
        if bold is not None:
            return int(bold.group(1))
        plain = TOTAL_PLAIN_RE.search(line)
        if plain is not None:
            return int(plain.group(1))
    return None


def _sum_prose_value(index_text: str) -> int | None:
    """Extract the `Sum NNNN < Total` prose near the bottom of the file."""
    m = SUM_PROSE_RE.search(index_text)
    if m is None:
        return None
    return int(m.group(1))


def _total_cell_failure(total_cell: int | None, live_total: int) -> list[str]:
    """Build failures for the Total cell mismatch (or missing) case."""
    if total_cell is None:
        return ["budget table: could not find Total cell in 00-index.md"]
    if total_cell == live_total:
        return []
    msg = f"budget table: 00-index Total cell is {total_cell} " f"but live sum is {live_total}"
    return [msg]


def _sum_prose_failure(sum_prose: int | None, live_total: int) -> list[str]:
    """Build failures for the `Sum NNNN` prose mismatch case."""
    if sum_prose is None or sum_prose == live_total:
        return []
    msg = f"budget table: `Sum NNNN` prose is {sum_prose} " f"but live sum is {live_total}"
    return [msg]


def _live_plan_total(root: Path) -> int:
    """Sum of wc -l across every plan file (00-index included)."""
    return sum(_wc_l(p) for p in _iter_plan_files_including_index(root))


def _load_index_text(root: Path) -> str | None:
    """Read 00-index.md text; return None when file is missing."""
    index_path = root / INDEX_FILE
    if not index_path.exists():
        return None
    return index_path.read_text(encoding="utf-8", errors="replace")


def check_budget_table_total(root: Path) -> list[str]:
    """Invariant 3: 00-index.md Total cell == live sum of wc -l."""
    index_text = _load_index_text(root)
    if index_text is None:
        return [f"budget table: missing {INDEX_FILE}"]
    live_total = _live_plan_total(root)
    total_cell = _total_cell_value(index_text)
    sum_prose = _sum_prose_value(index_text)
    failures: list[str] = []
    failures.extend(_total_cell_failure(total_cell, live_total))
    failures.extend(_sum_prose_failure(sum_prose, live_total))
    return failures


def _check_row_actual(row: Row, rel: Path, loc: int) -> list[str]:
    """Per-row Actual cell MUST equal the live wc -l of the cited path."""
    if row.actual == loc:
        return []
    msg = f"per-cell guard: row {row.num} ({rel}) " f"Actual cell is {row.actual} but wc -l is {loc}"
    return [msg]


def _check_row_budget(row: Row, rel: Path, loc: int) -> list[str]:
    """Per-row Budget cell MUST be >= live wc -l (cap not violated)."""
    if row.budget >= loc:
        return []
    msg = f"per-cell guard: row {row.num} ({rel}) " f"Budget {row.budget} < Actual {loc}"
    return [msg]


@dataclass(frozen=True)
class _RowCheckInputs:
    """Inputs for one per-cell guard iteration."""

    row: Row
    root: Path
    rel: Path
    target: Path


def _check_row_target(inputs: _RowCheckInputs) -> list[str]:
    """Apply per-row Actual + Budget checks to a resolved target path."""
    loc = _wc_l(inputs.target)
    failures: list[str] = []
    failures.extend(_check_row_actual(inputs.row, inputs.rel, loc))
    failures.extend(_check_row_budget(inputs.row, inputs.rel, loc))
    return failures


def _missing_target_finding(row: Row, rel: Path) -> list[str]:
    """Per-cell guard finding for a row whose target path does not exist."""
    msg = f"per-cell guard: row {row.num} cites {rel} which does not exist"
    return [msg]


def _resolve_row_target(root: Path, row: Row) -> tuple[Path, Path]:
    """Return (rel, target) for one row's file-map path entry."""
    rel = _normalize_row_path(row.path)
    return rel, root / rel


def _check_one_row(
    row: Row,
    root: Path,
    seen: set[str],
    failures: list[str],
) -> None:
    """Run the per-row Actual + Budget checks, mutating seen/failures."""
    if row.num in seen:
        return
    seen.add(row.num)
    rel, target = _resolve_row_target(root, row)
    if not target.exists():
        failures.extend(_missing_target_finding(row, rel))
        return
    inputs = _RowCheckInputs(row=row, root=root, rel=rel, target=target)
    failures.extend(_check_row_target(inputs))


def check_per_cell_guard(root: Path) -> list[str]:
    """Invariant 4: per-row Actual==wc -l AND per-row Budget==budget value."""
    index_text = _load_index_text(root)
    if index_text is None:
        return [f"per-cell guard: missing {INDEX_FILE}"]
    rows = _parse_file_map(index_text)
    failures: list[str] = []
    seen: set[str] = set()
    for row in rows:
        _check_one_row(row, root, seen, failures)
    return failures


def run_all_checks(
    root: Path,
    *,
    enforce_footer: bool = True,
    enforce_budget_table: bool = True,
    enforce_per_cell: bool = True,
) -> list[str]:
    """Run all four invariants; return the list of failure messages."""
    failures: list[str] = []
    failures.extend(check_per_file_cap(root))
    if enforce_footer:
        failures.extend(check_footer_drift(root))
    if enforce_budget_table:
        failures.extend(check_budget_table_total(root))
    if enforce_per_cell:
        failures.extend(check_per_cell_guard(root))
    return failures


def _add_enforce_flag(
    parser: argparse.ArgumentParser,
    *,
    flag: str,
    dest: str,
) -> None:
    """Register both --no-X and --enforce-X flags for a boolean invariant."""
    parser.add_argument(f"--no-{flag}", dest=dest, action="store_false")
    parser.add_argument(
        f"--enforce-{flag}",
        dest=dest,
        action="store_true",
        default=True,
    )


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    _add_enforce_flag(parser, flag="footer", dest="footer")
    _add_enforce_flag(parser, flag="budget-table", dest="budget")
    _add_enforce_flag(parser, flag="per-cell", dest="per_cell")
    parser.set_defaults(footer=True, budget=True, per_cell=True)
    return parser.parse_args(list(argv))


def _emit_error(message: str) -> None:
    sys.stderr.write(message + "\n")


def _emit_ok(message: str) -> None:
    sys.stdout.write(message + "\n")


def _emit_failure_summary(failures: list[str]) -> None:
    """Emit one FAIL line per failure + the summary count to stderr."""
    for line in failures:
        _emit_error(f"[check_line_count] FAIL: {line}")
    summary = f"[check_line_count] {len(failures)} invariant(s) violated"
    _emit_error(summary)


def _run_main(args: argparse.Namespace) -> int:
    """Run all checks against REPO_ROOT; return 0/1."""
    failures = run_all_checks(
        REPO_ROOT,
        enforce_footer=args.footer,
        enforce_budget_table=args.budget,
        enforce_per_cell=args.per_cell,
    )
    if failures:
        _emit_failure_summary(failures)
        return 1
    ok_msg = "[check_line_count] OK"
    _emit_ok(ok_msg + " (per-file cap + footer + budget table + per-cell)")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = _parse_args(argv)
    return _run_main(args)


if __name__ == "__main__":
    sys.exit(main())
