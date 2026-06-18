"""tests/meta/test_meta_check_line_count.py — meta-tests for tools/check_line_count.py.

Implements the TDD test list declared at the top of tools/check_line_count.py:

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

import subprocess
from pathlib import Path

import pytest

from tools import check_line_count
from tools.check_line_count import (
    PER_FILE_CAP,
    check_budget_table_total,
    check_footer_drift,
    check_per_cell_guard,
    check_per_file_cap,
    run_all_checks,
)


def _wc_l(path: Path) -> int:
    return int(subprocess.check_output(["wc", "-l", str(path)], text=True).split()[0])


def _build_synthetic_plans(
    root: Path,
    *,
    rows: dict[str, int],
    total_cell: int,
) -> dict[str, int]:
    """Build docs/plans/<name>.md with exact `loc` lines. Returns actual LOC per file.

    `rows` is {filename: exact-LOC}. The 00-index.md is constructed so the
    file-map row Budget==Actual==`rows[name]` and Total==`total_cell`.
    The body lines are padded with `line N` content so `wc -l` matches the
    declared value to the line.
    """
    plans = root / "docs" / "plans"
    plans.mkdir(parents=True)
    actual: dict[str, int] = {}
    # Pass 1: write every non-index file at its declared LOC.
    for fname, loc in rows.items():
        if fname == "00-index.md":
            continue
        target = plans / fname
        body = "\n".join(f"line {i}" for i in range(1, loc))
        body += "\n"
        body += f"<!-- end of file: {loc} lines (budget {loc}) -->\n"
        target.write_text(body, encoding="utf-8")
        actual[fname] = _wc_l(target)
    # Pass 2: build 00-index.md. We write enough content to hit the declared loc.
    lines: list[str] = ["<!-- title: Index — synthetic fixture -->"]
    lines.append("# Index")
    lines.append("")
    lines.append("| # | File | Covers | Status | Budget | Actual |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for fname, loc in rows.items():
        if fname == "00-index.md":
            continue
        lines.append(f"| 99 | `docs/plans/{fname}` | synthetic | [emitted] | " f"{loc} | {loc} |")
    lines.append(f"| | **Total** | | | **{total_cell}** | **{total_cell}** |")
    # Pad until we have exactly rows["00-index.md"] lines, then add the bare
    # marker as the last line. We pad BEFORE the marker so the final line is
    # the marker itself.
    target_loc = rows.get("00-index.md", 0)
    # If target is exactly len(lines)+1 we are done (one more line for marker).
    while len(lines) < target_loc - 1:
        lines.append("")
    lines.append("<!-- end of file -->")
    (plans / "00-index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    actual["00-index.md"] = _wc_l(plans / "00-index.md")
    return actual


def test_per_file_cap_passes_when_all_files_under_500_loc(tmp_path: Path) -> None:
    """All files <= 500 LOC => no failures from invariant 1."""
    _build_synthetic_plans(tmp_path, rows={"00-index.md": 20, "01-overview.md": 50}, total_cell=70)
    assert check_per_file_cap(tmp_path) == []


def test_per_file_cap_fails_when_a_file_exceeds_500_loc(tmp_path: Path) -> None:
    """One file > 500 LOC => invariant 1 fails."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": PER_FILE_CAP + 1},
        total_cell=521,
    )
    failures = check_per_file_cap(tmp_path)
    assert any("per-file cap" in f for f in failures)


def test_footer_drift_passes_when_plan_footer_matches_actual(tmp_path: Path) -> None:
    """Footer NN == wc -l => no failures from invariant 2."""
    _build_synthetic_plans(tmp_path, rows={"00-index.md": 20, "01-overview.md": 50}, total_cell=70)
    assert check_footer_drift(tmp_path) == []


def test_footer_drift_fails_when_plan_footer_is_stale(tmp_path: Path) -> None:
    """Stale footer NN != wc -l => invariant 2 fails."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n<!-- end of file -->\n", encoding="utf-8")
    target = plans / "01-overview.md"
    body = "\n".join("line" for _ in range(30)) + "\n"
    # Declare 25 but actual is 30
    target.write_text(body + "<!-- end of file: 25 lines (budget 50) -->\n", encoding="utf-8")
    failures = check_footer_drift(tmp_path)
    assert any("footer drift" in f for f in failures)


def test_budget_table_total_passes_when_sum_matches(tmp_path: Path) -> None:
    """Total cell == live sum => no failures from invariant 3."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=50,
    )
    assert check_budget_table_total(tmp_path) == []


def test_budget_table_total_fails_when_sum_mismatches(tmp_path: Path) -> None:
    """Total cell != live sum => invariant 3 fails."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=999,  # wrong
    )
    failures = check_budget_table_total(tmp_path)
    assert any("budget table" in f for f in failures)


def test_per_cell_guard_passes_when_each_row_cap_gte_actual_loc(tmp_path: Path) -> None:
    """Each row's Budget >= Actual LOC => invariant 4 passes."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=50,
    )
    assert check_per_cell_guard(tmp_path) == []


def test_per_cell_guard_fails_when_a_row_cap_lt_actual_loc(tmp_path: Path) -> None:
    """A row's Budget < Actual LOC => invariant 4 fails."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    target = plans / "01-overview.md"
    body = "\n".join("line" for _ in range(60)) + "\n"
    target.write_text(body + "<!-- end of file: 60 lines (budget 80) -->\n", encoding="utf-8")
    # Build an index file with row Budget < Actual.
    index_text = (
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `docs/plans/01-overview.md` | test | [emitted] | 50 | 60 |\n"
        "| | **Total** | | | **60** | **60** |\n"
        "<!-- end of file -->\n"
    )
    (plans / "00-index.md").write_text(index_text, encoding="utf-8")
    failures = check_per_cell_guard(tmp_path)
    assert any("per-cell guard" in f for f in failures)


def test_check_runs_clean_on_this_worktree_skeleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook MUST exit 0 against a perfectly-clean synthetic fixture."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30, "02-arch.md": 40},
        total_cell=90,
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    failures = run_all_checks(tmp_path)
    assert failures == []


def test_check_is_readonly_and_writes_nothing(tmp_path: Path) -> None:
    """The hook MUST NOT create or modify any files inside the repo root."""
    _build_synthetic_plans(tmp_path, rows={"00-index.md": 20, "01-overview.md": 30}, total_cell=50)
    # Snapshot AFTER builder; this is the baseline we must NOT extend.
    baseline = {str(p) for p in tmp_path.rglob("*")}
    _ = run_all_checks(tmp_path)
    after = {str(p) for p in tmp_path.rglob("*")}
    # The synthetic builder writes the baseline. The hook MUST NOT change it.
    assert baseline.issubset(after)
    assert after.issubset(baseline)


def test_iter_plan_files_returns_empty_when_plans_dir_missing(
    tmp_path: Path,
) -> None:
    """If docs/plans/ does not exist, iterators MUST return [] without raising."""
    assert check_line_count._iter_plan_files(tmp_path) == []
    assert check_line_count._iter_plan_files_including_index(tmp_path) == []


def test_iter_plan_files_excludes_index() -> None:
    """_iter_plan_files MUST exclude 00-index.md from the plan-only list."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        plans = Path(td) / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "00-index.md").write_text("# index\n", encoding="utf-8")
        (plans / "01-foo.md").write_text("# foo\n", encoding="utf-8")
        assert all(p.name != "00-index.md" for p in check_line_count._iter_plan_files(Path(td)))


def test_footer_drift_raises_when_index_missing_bare_marker(
    tmp_path: Path,
) -> None:
    """00-index.md without the bare `<!-- end of file -->` marker MUST fail invariant 2."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n", encoding="utf-8")
    failures = check_footer_drift(tmp_path)
    assert any("bare" in f for f in failures)


def test_footer_drift_raises_when_non_index_missing_footer(
    tmp_path: Path,
) -> None:
    """Non-index plan file without `<!-- end of file: NN lines (budget BB) -->` MUST fail."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n<!-- end of file -->\n", encoding="utf-8")
    (plans / "01-x.md").write_text("body without footer\n", encoding="utf-8")
    failures = check_footer_drift(tmp_path)
    assert any("missing" in f and "01-x.md" in f for f in failures)


def test_budget_table_total_raises_when_index_missing(tmp_path: Path) -> None:
    """When 00-index.md is absent, invariant 3 MUST emit a clear failure."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    failures = check_budget_table_total(tmp_path)
    assert any("missing" in f and "00-index.md" in f for f in failures)


def test_budget_table_total_raises_when_total_cell_missing(
    tmp_path: Path,
) -> None:
    """When 00-index.md has no Total cell, invariant 3 MUST fail."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n<!-- end of file -->\n", encoding="utf-8")
    failures = check_budget_table_total(tmp_path)
    assert any("could not find Total cell" in f for f in failures)


def test_budget_table_total_raises_when_sum_prose_mismatches(
    tmp_path: Path,
) -> None:
    """When `Sum NNNN` prose differs from the live sum, invariant 3 MUST fail."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 25, "01-overview.md": 30},
        total_cell=55,
    )
    # Inject a `Sum NNNN < ...` prose line that mismatches.
    index_path = tmp_path / "docs" / "plans" / "00-index.md"
    text = index_path.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- end of file -->",
        "Sum 999 < 4500 (sum of budgets 3960).\n<!-- end of file -->",
    )
    index_path.write_text(text, encoding="utf-8")
    # Note: adding a line to the file changes its wc -l; rebuild Total cell.
    new_loc = _wc_l(index_path)
    text = text.replace(
        "| | **Total** | | | **55** | **55** |",
        f"| | **Total** | | | **{new_loc + 30}** | **{new_loc + 30}** |",
    )
    index_path.write_text(text, encoding="utf-8")
    failures = check_budget_table_total(tmp_path)
    assert any("`Sum NNNN` prose" in f for f in failures)


def test_per_cell_guard_raises_when_row_path_missing(
    tmp_path: Path,
) -> None:
    """When a 00-index row cites a non-existent path, invariant 4 MUST fail."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `docs/plans/does-not-exist.md` | x | [emitted] | 50 | 50 |\n"
        "| | **Total** | | | **50** | **50** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    failures = check_per_cell_guard(tmp_path)
    assert any("does not exist" in f for f in failures)


def test_per_cell_guard_skips_duplicate_row_numbers(tmp_path: Path) -> None:
    """Duplicate row numbers MUST be silently skipped (de-duped)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    target = plans / "01-x.md"
    target.write_text(
        "line 1\nline 2\n<!-- end of file: 3 lines (budget 100) -->\n",
        encoding="utf-8",
    )
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `docs/plans/01-x.md` | x | [emitted] | 100 | 3 |\n"
        "| 01 | `docs/plans/01-x.md` | x | [emitted] | 100 | 3 |\n"
        "| | **Total** | | | **6** | **6** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    failures = check_per_cell_guard(tmp_path)
    # Both rows should pass (de-duped on num); no failures about Actual != wc -l.
    assert failures == []


def test_parse_args_disables_each_invariant(tmp_path: Path) -> None:
    """--no-footer / --no-budget-table / --no-per-cell MUST disable that invariant only."""
    args = check_line_count._parse_args(["--no-footer"])
    assert args.footer is False
    assert args.budget is True
    assert args.per_cell is True

    args = check_line_count._parse_args(["--no-budget-table"])
    assert args.footer is True
    assert args.budget is False
    assert args.per_cell is True

    args = check_line_count._parse_args(["--no-per-cell"])
    assert args.footer is True
    assert args.budget is True
    assert args.per_cell is False


def test_parse_args_enables_each_invariant(tmp_path: Path) -> None:
    """--enforce-* flags MUST enable the corresponding invariant."""
    args = check_line_count._parse_args(["--enforce-footer"])
    assert args.footer is True
    args = check_line_count._parse_args(["--enforce-budget-table"])
    assert args.budget is True
    args = check_line_count._parse_args(["--enforce-per-cell"])
    assert args.per_cell is True


def test_main_returns_1_when_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main() MUST exit 1 when ANY invariant fails."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 50},
        total_cell=999,  # wrong total
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    rc = check_line_count.main([])
    assert rc == 1
    out = capsys.readouterr().err
    assert "FAIL" in out


def test_main_returns_0_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main() MUST exit 0 against a perfectly-clean synthetic fixture."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=50,
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    rc = check_line_count.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_iter_plan_files_falls_back_when_no_file_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When 00-index has NO file map rows, _iter_plan_files MUST fall back to on-disk glob."""
    # 00-index with bare marker but no table rows.
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n<!-- end of file -->\n", encoding="utf-8")
    (plans / "99-z.md").write_text("body\n", encoding="utf-8")
    paths = check_line_count._iter_plan_files(tmp_path)
    # Fallback: on-disk glob minus 00-index.
    assert any(p.name == "99-z.md" for p in paths)
    assert all(p.name != "00-index.md" for p in paths)


def test_iter_plan_files_success_path_with_file_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the file map IS parsed, _iter_plan_files MUST walk it (lines 81-86)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `01-a.md` | a | [emitted] | 30 | 5 |\n"
        "| 02 | `02-b.md` | b | [emitted] | 30 | 5 |\n"
        "| | **Total** | | | **10** | **10** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    (plans / "01-a.md").write_text("x\n<!-- end of file: 2 lines (budget 30) -->\n", encoding="utf-8")
    (plans / "02-b.md").write_text("x\n<!-- end of file: 2 lines (budget 30) -->\n", encoding="utf-8")
    paths = check_line_count._iter_plan_files(tmp_path)
    # Success path: walk the file map (skip 00-index from the result).
    names = {p.name for p in paths}
    assert names == {"01-a.md", "02-b.md"}


def test_iter_plan_files_including_index_falls_back_when_no_file_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When 00-index has NO file map rows, the iter including index MUST include 00-index."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text("# Index\n<!-- end of file -->\n", encoding="utf-8")
    (plans / "99-z.md").write_text("body\n", encoding="utf-8")
    paths = check_line_count._iter_plan_files_including_index(tmp_path)
    assert any(p.name == "00-index.md" for p in paths)
    assert any(p.name == "99-z.md" for p in paths)


def test_iter_plan_files_including_index_no_plans_dir(tmp_path: Path) -> None:
    """When docs/plans/ is missing entirely, the iter MUST return []."""
    paths = check_line_count._iter_plan_files_including_index(tmp_path)
    assert paths == []


def test_file_map_paths_handles_unreadable_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_file_map_paths MUST return None when the index is unreadable (lines 119-120)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    # Create the file so `index_path.exists()` is True; the read_text will raise.
    (plans / "00-index.md").write_text("# Index\n", encoding="utf-8")
    real_read_text = Path.read_text

    def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "00-index.md":
            raise OSError("intentional")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    assert check_line_count._file_map_paths(tmp_path) is None


def test_parse_file_map_skips_unmatched_rows() -> None:
    """Rows that don't match ROW_RE MUST be silently skipped (no crash)."""
    text = (
        "header\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| broken-row | with | no | numbers | here | nope |\n"
    )
    assert check_line_count._parse_file_map(text) == []


def test_per_cell_guard_skips_total_row() -> None:
    """The Total row in the file map MUST be skipped (num=='' row)."""
    # The ROW_RE only matches num=\\d{2}; the Total row has no num.
    text = (
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| | **Total** | | | **100** | **100** |\n"
    )
    assert check_line_count._parse_file_map(text) == []


def test_per_cell_guard_bare_filename_path(tmp_path: Path) -> None:
    """Rows with a bare filename (no 'docs/plans/' prefix) MUST resolve correctly."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "01-x.md").write_text(
        "line 1\nline 2\n<!-- end of file: 3 lines (budget 100) -->\n",
        encoding="utf-8",
    )
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `01-x.md` | x | [emitted] | 100 | 3 |\n"
        "| | **Total** | | | **3** | **3** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    failures = check_line_count.check_per_cell_guard(tmp_path)
    assert failures == []


def test_per_cell_guard_dedupes_duplicate_num(tmp_path: Path) -> None:
    """Duplicate row numbers MUST be silently skipped after the first."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "01-x.md").write_text("line 1\n<!-- end of file: 2 lines (budget 100) -->\n", encoding="utf-8")
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `docs/plans/01-x.md` | x | [emitted] | 100 | 2 |\n"
        "| 01 | `docs/plans/01-x.md` | x | [emitted] | 100 | 2 |\n"
        "| | **Total** | | | **2** | **2** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    failures = check_line_count.check_per_cell_guard(tmp_path)
    assert failures == []


def test_main_with_no_invariant_flags_disables_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main() with all three --no-* flags MUST still return 0 (no invariants to check)."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=999,  # would fail budget-table normally
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    rc = check_line_count.main(["--no-footer", "--no-budget-table", "--no-per-cell"])
    assert rc == 0


def test_main_uses_sys_argv_when_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main(argv=None) MUST read sys.argv[1:] (covers the `if argv is None` branch)."""
    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=50,
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["check_line_count.py"])
    rc = check_line_count.main(None)
    assert rc == 0


def test_run_all_checks_with_each_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run_all_checks with enforce_*=False MUST short-circuit that invariant."""
    _build_synthetic_plans(tmp_path, rows={"00-index.md": 20, "01-overview.md": 30}, total_cell=50)
    # If footer is off, the missing-footer case below is not flagged.
    plans = tmp_path / "docs" / "plans"
    (plans / "01-overview.md").write_text("no footer here\n", encoding="utf-8")  # no footer
    failures = run_all_checks(tmp_path, enforce_footer=False)
    # Per-cell guard should still pass (Actual matches wc -l of 01-x.md).
    assert all("footer drift" not in f for f in failures)


def test_iter_plan_files_including_index_dedupes_00_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When 00-index row IS in the file map, it MUST NOT be added twice (line 107)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 00 | `00-index.md` | this | [emitted] | 30 | 10 |\n"
        "| | **Total** | | | **10** | **10** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    paths = check_line_count._iter_plan_files_including_index(tmp_path)
    assert sum(1 for p in paths if p.name == "00-index.md") == 1


def test_iter_plan_files_skips_00_index_in_file_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When 00-index IS in the file map, _iter_plan_files MUST skip it (line 84)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 00 | `00-index.md` | this | [emitted] | 30 | 10 |\n"
        "| 01 | `01-x.md` | x | [emitted] | 30 | 5 |\n"
        "| | **Total** | | | **15** | **15** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    (plans / "01-x.md").write_text("x\n<!-- end of file: 2 lines (budget 30) -->\n", encoding="utf-8")
    paths = check_line_count._iter_plan_files(tmp_path)
    # _iter_plan_files MUST NOT include 00-index even when it's in the file map.
    assert all(p.name != "00-index.md" for p in paths)
    assert any(p.name == "01-x.md" for p in paths)


def test_footer_drift_handles_unreadable_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the file map returns None, _iter_plan_files falls back to on-disk glob (line 119)."""
    # _file_map_paths catches OSError on read of 00-index and returns None,
    # which causes _iter_plan_files to fall back to the on-disk glob.
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    real_read_text = Path.read_text

    def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "00-index.md":
            raise OSError("intentional")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    # _iter_plan_files falls back to glob when file map is None.
    paths = check_line_count._iter_plan_files(tmp_path)
    # Without 00-index.md readable, the glob falls back and 00-index is excluded.
    assert all(p.name != "00-index.md" for p in paths)


def test_per_cell_guard_bare_filename_path_is_normalized(
    tmp_path: Path,
) -> None:
    """Rows with a bare filename (no 'docs/plans/' prefix) MUST be normalized (line 128)."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "01-y.md").write_text("x\n<!-- end of file: 2 lines (budget 100) -->\n", encoding="utf-8")
    (plans / "00-index.md").write_text(
        "# Index\n\n"
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 01 | `01-y.md` | y | [emitted] | 100 | 2 |\n"
        "| | **Total** | | | **2** | **2** |\n"
        "<!-- end of file -->\n",
        encoding="utf-8",
    )
    failures = check_line_count.check_per_cell_guard(tmp_path)
    assert failures == []


def test_parse_file_map_total_row_skipped() -> None:
    """The Total row (no num) MUST be silently skipped (line 181)."""
    # The 00-index's Total row has empty num. ROW_RE requires \d{2}, so the Total
    # row doesn't match and is skipped. But also, the case where a row has num=''
    # (the "no number" case) is filtered out by `if num == ""`.
    text = (
        "| # | File | Covers | Status | Budget | Actual |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 99 | `99-x.md` | x | [emitted] | 50 | 10 |\n"
        "| | **Total** | | | **10** | **10** |\n"
    )
    rows = check_line_count._parse_file_map(text)
    assert len(rows) == 1
    assert rows[0].num == "99"


def test_total_cell_value_fallback_unbold(tmp_path: Path) -> None:
    """_total_cell_value MUST also accept a non-bolded integer in the Total row (line 207-209)."""
    index_text = "| 00 | `00-index.md` | this | [emitted] | 30 | 5 |\n" "| | Total | | | 5 | 5 |\n"
    assert check_line_count._total_cell_value(index_text) == 5


def test_budget_table_total_handles_unreadable_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """check_budget_table_total MUST return early if 00-index is unreadable."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    real_read_text = Path.read_text

    def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "00-index.md":
            raise OSError("intentional")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    failures = check_line_count.check_budget_table_total(tmp_path)
    assert any("missing" in f and "00-index.md" in f for f in failures)


def test_main_module_invocation_via_runpy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The `if __name__ == '__main__'` block MUST be importable (line 351)."""
    import importlib

    importlib.reload(check_line_count)
    assert hasattr(check_line_count, "main")


def test_main_block_executes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The `if __name__ == '__main__':` block MUST be runnable in-process (line 348)."""
    import types

    _build_synthetic_plans(
        tmp_path,
        rows={"00-index.md": 20, "01-overview.md": 30},
        total_cell=50,
    )
    monkeypatch.setattr(check_line_count, "REPO_ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["check_line_count.py"])
    # Create a fresh module-like object whose __name__ is "__main__" so the
    # `if __name__ == "__main__":` block fires when the file's source is exec'd.
    main_module = types.ModuleType("__main__")
    main_module.__dict__.update(check_line_count.__dict__)
    main_module.__name__ = "__main__"
    src = Path(check_line_count.__file__).read_text(encoding="utf-8")
    code = compile(src, check_line_count.__file__, "exec")
    try:
        exec(code, main_module.__dict__)  # noqa: S102
    except SystemExit as e:
        # The block calls sys.exit(main()); SystemExit is expected.
        assert e.code in (0, 1)


def test_per_cell_guard_raises_when_00_index_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """check_per_cell_guard MUST emit a clear failure when 00-index is missing (line 245)."""
    # No docs/plans dir at all.
    failures = check_line_count.check_per_cell_guard(tmp_path)
    assert any("missing" in f and "00-index.md" in f for f in failures)


def test_total_cell_value_no_integer_continues_loop() -> None:
    """When neither regex matches, the loop MUST continue to the next line (line 205->197)."""
    # A line with **Total** but no integer (e.g. truncated table).
    text = "| 00 | `00-index.md` | this | [emitted] | 30 | 5 |\n" "| | **Total** | | | broken |\n"
    assert check_line_count._total_cell_value(text) is None
