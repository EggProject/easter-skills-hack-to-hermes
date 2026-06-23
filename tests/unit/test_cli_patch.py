"""Unit tests for the click CLI (cli_patch.py).

Exercises the full flag matrix and the bilingual help output.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner

from easter_hermes_sorry_skills._patcher import (
    EXIT_IO,
    EXIT_OK,
    EXIT_USER_ABORT,
    STATE_SIDECAR,
)
from easter_hermes_sorry_skills.cli_patch import HELP_EN, HELP_HU, main

# --- --help --------------------------------------------------------------


def test_help_sections_present() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "Usage (English)" in r.output
    assert "Használat (magyar)" in r.output


def test_help_options_mirrored() -> None:
    """Each option in HELP_EN must also appear in HELP_HU."""
    options = [
        "--target",
        "--check",
        "--apply",
        "--i-accept-line-drift",
        "--force",
        "--yes",
        "--verbose",
    ]
    for opt in options:
        assert opt in HELP_EN, f"missing in HELP_EN: {opt}"
        assert opt in HELP_HU, f"missing in HELP_HU: {opt}"


# --- --target required (exit 4) -----------------------------------------


def test_cli_target_required_exits_4() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["--check"])
    assert r.exit_code == EXIT_IO
    assert "[en]" in r.output or "[en]" in (r.stderr or "")
    assert "[hu]" in r.output or "[hu]" in (r.stderr or "")


def test_cli_target_hermes_agent_refused() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["--check", "--target", str(Path.home() / ".hermes" / "hermes-agent")])
    assert r.exit_code == EXIT_IO
    combined = r.output + (r.stderr or "")
    assert "hermes-agent" in combined


# --- --apply happy path -------------------------------------------------


def test_cli_apply_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--apply", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    assert (hermes_checkout / STATE_SIDECAR).exists()


def test_cli_check_no_writes(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--check", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


def test_cli_force_without_i_accept_exits_5(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--apply", "--force", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_USER_ABORT


def test_cli_force_with_i_accept_succeeds(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "--apply",
            "--force",
            "--i-accept-line-drift",
            "--target",
            str(hermes_checkout),
        ],
    )
    assert r.exit_code == EXIT_OK


def test_cli_task_e_runs_by_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Task E always runs by default; no opt-out flag exists.

    With only --apply + --target, both S1.cap and all 5 Task E sites
    are written into the state sidecar (E0/E1/E2/E4/E5).
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--apply", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    state = json.loads((hermes_checkout / STATE_SIDECAR).read_text(encoding="utf-8"))
    # All 5 Task E sites must be in the state sidecar — Task E ran by default.
    assert "E0.consult_rule_def" in state
    assert "E1.skills_guidance" in state
    assert "E2.memory_guidance" in state
    assert "E4.skill_review_prompt_opt4" in state
    assert "E5.combined_review_prompt_opt4" in state
    # S1.cap also runs by default (always-on, not opt-out).
    assert "S1.cap" in state


def test_cli_task_e_check_mode_runs_by_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Task E is checked (not just applied) by default — no opt-out flag.

    --check with --target (no Task E flag) must audit Task E sites too,
    producing exit 0 and surfacing every Task E site in the OK diagnostics.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--check", "--verbose", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    # Every Task E site must appear in the verbose OK diagnostics,
    # proving Task E was validated by default with no flag.
    for site_id in (
        "E0.consult_rule_def",
        "E1.skills_guidance",
        "E2.memory_guidance",
        "E4.skill_review_prompt_opt4",
        "E5.combined_review_prompt_opt4",
    ):
        assert site_id in combined, f"Task E site {site_id} not checked by default"


def test_cli_verbose_emits_diagnostics(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--apply", "--verbose", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    # The diagnostics include bilingual OK lines
    assert "OK" in r.output


def test_cli_default_check_mode(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """When neither --check nor --apply is given, the CLI defaults to --check."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(main, ["--target", str(hermes_checkout)])
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


def test_cli_patch_main_entry_returns_main_exit_code(monkeypatch) -> None:
    """Calling the _main_entry function exercises the standalone CLI path."""
    from easter_hermes_sorry_skills import cli_patch

    monkeypatch.setattr(cli_patch, "main", lambda standalone_mode=False: None)
    assert cli_patch._main_entry() == 0
