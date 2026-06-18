"""Unit tests for the click CLI (cli_patch.py).

Exercises the full flag matrix and the bilingual help output.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from hermes_skill_creator_plugin._patcher import (
    EXIT_IO,
    EXIT_OK,
    EXIT_USER_ABORT,
    STATE_SIDECAR,
)
from hermes_skill_creator_plugin.cli_patch import HELP_EN, HELP_HU, main

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
        "--task-e-redirect",
        "--i-accept-line-drift",
        "--force",
        "--emit-migration-note",
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


def test_cli_task_e_redirect(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "--apply",
            "--task-e-redirect",
            "--target",
            str(hermes_checkout),
        ],
    )
    assert r.exit_code == EXIT_OK
    state = json.loads((hermes_checkout / STATE_SIDECAR).read_text(encoding="utf-8"))
    assert "E1.skills_guidance" in state
    assert "E7.skills_doc_section" in state


def test_cli_no_schema_redirect(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "--apply",
            "--task-e-redirect",
            "--no-schema-redirect",
            "--target",
            str(hermes_checkout),
        ],
    )
    assert r.exit_code == EXIT_OK
    state = json.loads((hermes_checkout / STATE_SIDECAR).read_text(encoding="utf-8"))
    assert "E6.skill_manage_schema_desc" not in state


# --- --emit-migration-note ----------------------------------------------


def test_cli_emit_migration_note_default(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        # runner.isolated_filesystem sets cwd to a tmp dir
        r = runner.invoke(
            main,
            [
                "--emit-migration-note",
                "--target",
                str(hermes_checkout),
            ],
        )
        assert r.exit_code == EXIT_OK
        out_path = Path(td) / "MIGRATION.hermes-patch.md"
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        cap_table = text.split("## Task E sites")[0]
        cap_rows = [ln for ln in cap_table.splitlines() if ln.startswith("| S1.")]
        assert len(cap_rows) == 1


def test_cli_emit_migration_note_target_required() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["--emit-migration-note"])
    assert r.exit_code == EXIT_IO


def test_cli_emit_migration_note_hermes_agent_refused() -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "--emit-migration-note",
            "--target",
            str(Path.home() / ".hermes" / "hermes-agent"),
        ],
    )
    assert r.exit_code == EXIT_IO


# --- --verbose (already emits diagnostics) -------------------------------


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


def test_cli_emit_migration_note_with_git_failure(hermes_checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When _git_head raises, the emit-migration-note path catches it
    and continues with an empty git_head."""
    from hermes_skill_creator_plugin import cli_patch

    def boom(target: Path) -> str:
        raise RuntimeError("simulated git failure")

    monkeypatch.setattr(cli_patch, "_git_head", boom)
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        r = runner.invoke(
            main,
            [
                "--emit-migration-note",
                "--target",
                str(hermes_checkout),
            ],
        )
        assert r.exit_code == EXIT_OK
        out_path = Path(td) / "MIGRATION.hermes-patch.md"
        assert out_path.exists()


def test_cli_patch_main_entry_returns_main_exit_code(monkeypatch) -> None:
    """Calling the _main_entry function exercises the standalone CLI path."""
    from hermes_skill_creator_plugin import cli_patch

    monkeypatch.setattr(cli_patch.main, "main", lambda standalone_mode=False: 0)
    assert cli_patch._main_entry() == 0
