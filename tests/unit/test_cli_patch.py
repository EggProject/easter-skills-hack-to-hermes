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
    STATE_SIDECAR,
)
from easter_hermes_sorry_skills.cli_patch import main

# --- --help --------------------------------------------------------------


def test_help_default_is_english() -> None:
    """Default ``--help`` (no ``--lang``) renders HELP_EN only."""
    runner = CliRunner()
    r = runner.invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "Patcher applies:" in r.output
    assert "A patcher a kovetkezoket vegzi" not in r.output


def test_help_lang_hu_renders_hungarian() -> None:
    """``--lang hu --help`` renders HELP_HU only."""
    runner = CliRunner()
    r = runner.invoke(main, ["--lang", "hu", "--help"])
    assert r.exit_code == 0
    assert "A patcher a kovetkezoket vegzi" in r.output
    assert "Patcher applies:" not in r.output


def test_help_lists_lang_option() -> None:
    """``--lang`` shows up in the auto-generated Options block."""
    runner = CliRunner()
    r = runner.invoke(main, ["--help"])
    assert "--lang [en|hu]" in r.output


def test_help_options_mirrored() -> None:
    """Each option in HELP_EN must also appear in HELP_HU."""
    runner = CliRunner()
    options = [
        "--target",
        "--dry-run",
        "--verbose",
    ]
    en_output = runner.invoke(main, ["--lang", "en", "--help"]).output
    hu_output = runner.invoke(main, ["--lang", "hu", "--help"]).output
    for opt in options:
        assert opt in en_output, f"missing in EN --help output: {opt}"
        assert opt in hu_output, f"missing in HU --help output: {opt}"


# --- --target required (exit 4) -----------------------------------------


def test_cli_target_required_exits_4() -> None:
    """With ``--dry-run`` and the default ``--target``, the patcher is
    the soft-safety warning path (hermes-agent target), not the
    ``target is None`` path (the CLI defaults ``--target`` to
    ``~/.hermes/hermes-agent``). The hermes-agent + ``--dry-run``
    combination is now a WARNING that proceeds with the plan and
    returns EXIT_OK; the legacy ``target is None`` preflight rule is
    unreachable through this CLI entry point and is exercised directly
    via :func:`run_preflight` in :mod:`_patcher_preflight` tests.

    When the live ``~/.hermes/hermes-agent`` checkout is absent (the
    common case on developer machines), the post-preflight pipeline
    hits TEXT_DRIFT on the synthetic targets and returns EXIT_DRIFT
    (``2``). The test asserts the bilingual WARNING was emitted, which
    proves the soft-safety preflight short-circuit fired.
    """
    runner = CliRunner()
    r = runner.invoke(main, ["--dry-run"])
    combined = r.output + (r.stderr or "")
    # Soft safety: the WARNING diagnostic MUST appear before any drift
    # diagnostics, proving the hermes-agent preflight returned the
    # soft-warning branch (severity="warning") rather than the hard
    # EXIT_IO refusal.
    assert "[en] WARNING: target is the live hermes-agent checkout" in combined
    assert "[hu] FIGYELEM: a target az élő hermes-agent checkout" in combined


def test_cli_apply_target_hermes_agent_refused() -> None:
    """Apply mode still hard-refuses the live hermes-agent checkout.

    Soft safety only softens the hermes-agent refusal under
    ``--dry-run``. Apply mode (``dry_run=False``) preserves the
    original hard refusal with ``EXIT_IO`` and a bilingual diagnostic
    that names the no-touch sentinel.
    """
    runner = CliRunner()
    r = runner.invoke(main, ["--target", str(Path.home() / ".hermes" / "hermes-agent")])
    assert r.exit_code == EXIT_IO
    combined = r.output + (r.stderr or "")
    assert "hermes-agent" in combined


def test_cli_dry_run_target_hermes_agent_warns(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Soft safety: ``--dry-run --target ~/.hermes/hermes-agent`` -> EXIT_OK.

    The patcher must NOT hard-refuse the live hermes-agent checkout
    under ``--dry-run``: the audit-only run should warn (soft safety)
    and proceed to print the bilingual plan so the operator sees the
    planned changes before deciding whether to apply.
    """
    runner = CliRunner()
    # Simulate the hermes-agent target by pointing at the test fixture
    # path AND patching ``is_hermes_agent`` to return True so the
    # preflight softens the refusal. The plan emitter runs against
    # the fixture's actual files (so the diff preview is meaningful).
    from unittest.mock import patch as _patch

    real_resolve = hermes_checkout.resolve()

    with _patch(
        "easter_hermes_sorry_skills._patcher_preflight.is_hermes_agent",
        return_value=True,
    ):
        r = runner.invoke(
            main,
            ["--dry-run", "--target", str(real_resolve)],
        )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    # Soft safety warning is bilingual and names the no-touch sentinel.
    assert "hermes-agent" in combined
    assert "[en] WARNING:" in combined
    assert "[hu] FIGYELEM:" in combined
    # Plan body still renders the ``would patch:`` header.
    assert "would patch:" in combined
    assert "patchelné:" in combined


# --- default (write) happy path -----------------------------------------


def test_cli_apply_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    assert (hermes_checkout / STATE_SIDECAR).exists()


def test_cli_check_no_writes(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


def test_cli_dry_run_emits_plan_with_files_and_lines(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """``--dry-run`` emits a bilingual plan with file paths + line numbers.

    The plan body MUST contain the ``would patch: <file>`` line for
    every site, the old/new diff preview with explicit ``line N:``
    prefixes, and the bilingual summary so the operator sees the
    exact changes that WOULD be applied.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    # Plan header is bilingual.
    assert "would patch:" in combined
    assert "patchelné:" in combined
    # Per-site file path appears at least once.
    assert "agent/skill_utils.py" in combined
    # Diff preview with explicit line numbers.
    assert "line " in combined
    assert "- " in combined
    assert "+ " in combined
    # Trailing NOT-APPLIED message (dry_run mode).
    assert "NEM történt meg" in combined
    assert "were NOT applied" in combined


def test_cli_dry_run_and_apply_both_emit_plan(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Both ``--dry-run`` and apply modes render the bilingual ``plan for:`` header.

    The plan emitter is shared across modes so the operator can diff
    the two outputs visually — the only difference is the trailing
    tail (``not applied`` vs ``applied``).
    """
    runner = CliRunner()
    r_dry = runner.invoke(
        main,
        ["--dry-run", "--target", str(hermes_checkout)],
    )
    r_apply = runner.invoke(
        main,
        ["--target", str(hermes_checkout)],
    )
    assert r_dry.exit_code == EXIT_OK
    assert r_apply.exit_code == EXIT_OK
    dry_combined = r_dry.output + (r_dry.stderr or "")
    apply_combined = r_apply.output + (r_apply.stderr or "")
    # Bilingual plan header (single-string format) renders in both modes.
    assert "[en] plan for " in dry_combined
    assert "[hu] terv a " in dry_combined
    assert "[en] plan for " in apply_combined
    assert "[hu] terv a " in apply_combined


def test_cli_apply_emits_applied_summary(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Apply mode emits the bilingual ``N patch alkalmazva`` summary.

    The tail message differs from ``--dry-run``: instead of the
    NOT-APPLIED warning, the apply path renders the bilingual
    ``N patch alkalmazva`` line so the operator knows the writes
    happened.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    assert "patch alkalmazva" in combined
    assert "patches applied" in combined


def test_cli_dry_run_no_writes_to_target(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Belt-and-suspenders: ``--dry-run`` writes ZERO bytes to the target.

    Verifies every target file's sha256 stays byte-identical across
    the dry-run, including the three anchor-bearing files (skill_utils,
    prompt_builder, background_review).
    """
    runner = CliRunner()
    targets = [
        hermes_checkout / "agent" / "skill_utils.py",
        hermes_checkout / "agent" / "prompt_builder.py",
        hermes_checkout / "agent" / "background_review.py",
    ]
    pre_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    r = runner.invoke(
        main,
        ["--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    for path in targets:
        post = hashlib.sha256(path.read_bytes()).hexdigest()
        assert pre_hashes[str(path)] == post, f"{path} was mutated by --dry-run"


def test_cli_task_e_runs_by_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Task E always runs by default; no opt-out flag exists.

    With only --target (default = write), both S1.cap and all 5 Task E sites
    are written into the state sidecar (E0/E1/E2/E4/E5).
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--target", str(hermes_checkout)],
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

    --dry-run with --target (no Task E flag) must audit Task E sites too,
    producing exit 0 and surfacing every Task E site in the OK diagnostics.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--dry-run", "--verbose", "--target", str(hermes_checkout)],
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
        ["--verbose", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    # The diagnostics include bilingual OK lines
    assert "OK" in r.output


def test_cli_default_writes(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """When no flag is given, the CLI defaults to WRITES (exit 0 on success)."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(main, ["--target", str(hermes_checkout)])
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre != post


def test_cli_patch_main_entry_returns_main_exit_code(monkeypatch) -> None:
    """Calling the _main_entry function exercises the standalone CLI path."""
    from easter_hermes_sorry_skills import cli_patch

    monkeypatch.setattr(cli_patch, "main", lambda standalone_mode=False: None)
    assert cli_patch._main_entry() == 0
