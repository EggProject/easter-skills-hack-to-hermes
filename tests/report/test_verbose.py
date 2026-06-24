"""tests/report/test_verbose.py

TDD: tests for ``--verbose`` per-cell stderr diagnostics in the reporter
CLI. Stdout / JSON output MUST remain untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from easter_hermes_sorry_skills import cli_report
from easter_hermes_sorry_skills.cli_report import main
from tests.report._fixtures import _write_profile


def test_verbose_emits_per_cell_diagnostics_to_stderr(hermes_home: Path) -> None:
    """When ``--verbose`` is set, stderr carries one line per cell."""
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"alpha": "x" * 10, "beta": "y" * 5},
    )
    result = CliRunner().invoke(
        main,
        ["--verbose", "--profile", "hermes", "--format", "text"],
    )
    assert result.exit_code == 0
    err_text = result.stderr or ""
    # Per-cell line format: [verbose] profile=X section=Y cell=Z=V
    assert "[verbose] profile=hermes section=hermes cell=name=alpha" in err_text
    assert "[verbose] profile=hermes section=hermes cell=name=beta" in err_text
    # Per-section summary line: [verbose] section=Y rows=N skipped_empty=K
    assert "[verbose] section=hermes rows=" in err_text


def test_verbose_summary_reports_row_count(hermes_home: Path) -> None:
    """The section summary must reflect the actual row count."""
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"alpha": "x" * 10, "beta": "y" * 5, "gamma": "z" * 7},
    )
    result = CliRunner().invoke(
        main,
        ["--verbose", "--profile", "hermes", "--format", "text"],
    )
    assert result.exit_code == 0
    err_text = result.stderr or ""
    # Expect exactly 3 rows in the summary.
    assert "[verbose] section=hermes rows=3 skipped_empty=0" in err_text


def test_verbose_does_not_pollute_stdout(hermes_home: Path) -> None:
    """``[verbose]`` lines must NEVER appear on stdout."""
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"alpha": "x" * 10},
    )
    result = CliRunner().invoke(
        main,
        ["--verbose", "--profile", "hermes", "--format", "text"],
    )
    assert result.exit_code == 0
    out_text = result.stdout or ""
    assert "[verbose]" not in out_text


def test_verbose_does_not_pollute_json_output(
    hermes_home: Path,
    tmp_path: Path,
) -> None:
    """JSON output must be a pure, parseable JSON document — no diagnostics."""
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"alpha": "x" * 10},
    )
    out = tmp_path / "report.json"
    result = CliRunner().invoke(
        main,
        [
            "--verbose",
            "--profile",
            "hermes",
            "--format",
            "json",
            "--json",
            str(out),
        ],
    )
    assert result.exit_code == 0
    # File is parseable as a single JSON object.
    obj = json.loads(out.read_text(encoding="utf-8"))
    assert obj["tool"] == "easter-hermes-sorry-skills-report"
    # Verbose markers must not be embedded in the JSON file.
    assert "[verbose]" not in out.read_text(encoding="utf-8")


def test_no_verbose_means_no_diagnostics(hermes_home: Path) -> None:
    """When ``--verbose`` is omitted, stderr carries NO ``[verbose]`` lines."""
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"alpha": "x" * 10},
    )
    result = CliRunner().invoke(
        main,
        ["--profile", "hermes", "--format", "text"],
    )
    assert result.exit_code == 0
    err_text = result.stderr or ""
    assert "[verbose]" not in err_text


def test_report_inputs_verbose_defaults_to_false() -> None:
    """The ``ReportInputs.verbose`` field MUST default to False."""
    inputs = cli_report.ReportInputs()
    assert inputs.verbose is False
