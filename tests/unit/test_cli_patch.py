"""Unit tests for the click CLI (cli_patch.py).

Exercises the full flag matrix and the ``--lang`` single-language
help output.

The CLI help output is single-language per ``--lang``. The patcher
diagnostic stream is bilingual in format (``[en] X / [hu] Y``); the
``--lang`` flag is plumbed through to ``run_patch`` for future single-
language emission (when the patcher i18n refactor lands). The tests
pin the current bilingual diagnostic format AND assert the ``--lang``
flag is required on every ``runner.invoke`` call.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from easter_hermes_sorry_skills._patcher import (
    EXIT_OK,
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


@pytest.mark.parametrize(
    ("lang", "expected_text", "other_lang_text"),
    [
        ("en", "WARNING: target is the live hermes-agent checkout", "FIGYELEM"),
        ("hu", "FIGYELEM: a target az élő hermes-agent checkout", "WARNING"),
    ],
)
def test_cli_target_required_emits_warning_in_selected_language(
    lang: str,
    expected_text: str,
    other_lang_text: str,
) -> None:
    """``--dry-run`` with the default ``--target`` (the hermes-agent
    soft-safety warning path) emits the WARNING diagnostic in the
    selected language (single-language, no bilingual
    ``[en] / [hu]`` prefix).

    The CLI threads ``--lang`` through to the preflight pipeline via
    :class:`PatchRunInputs.lang`; the preflight ``DRY_RUN_PREFLIGHT_WARNING``
    is selected from the language-specific module via ``pick(lang)``.
    For ``--lang en`` the operator sees the English WARNING; for
    ``--lang hu`` they see the Hungarian FIGYELEM line. The OTHER
    language's marker must NOT appear in the output.
    """
    runner = CliRunner()
    r = runner.invoke(main, ["--lang", lang, "--dry-run"])
    combined = r.output + (r.stderr or "")
    assert expected_text in combined
    assert other_lang_text not in combined


# REMOVED (user-requested preflight protection removal): apply mode
# (dry_run=False) no longer hard-refuses the live hermes-agent
# checkout — the operator is the authority on which checkout to
# patch. The previous test ``test_cli_apply_target_hermes_agent_refused``
# asserted EXIT_IO for ``--target ~/.hermes/hermes-agent``; that
# refusal is now gone.


@pytest.mark.parametrize(
    ("lang", "warning_marker", "patch_header"),
    [
        ("en", "WARNING:", "would patch:"),
        ("hu", "FIGYELEM:", "patchelné:"),
    ],
)
def test_cli_dry_run_target_hermes_agent_warns(
    lang: str,
    warning_marker: str,
    patch_header: str,
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Soft safety: ``--dry-run --target ~/.hermes/hermes-agent`` -> EXIT_OK.

    The patcher must NOT hard-refuse the live hermes-agent checkout
    under ``--dry-run``: the audit-only run should warn (soft safety)
    and proceed to print the plan so the operator sees the planned
    changes before deciding whether to apply. The warning is emitted
    in single-language format selected by ``--lang``: ``en`` shows
    ``WARNING:``, ``hu`` shows ``FIGYELEM:``.
    """
    runner = CliRunner()
    from unittest.mock import patch as _patch

    real_resolve = hermes_checkout.resolve()

    with _patch(
        "easter_hermes_sorry_skills._patcher_preflight.is_hermes_agent",
        return_value=True,
    ):
        r = runner.invoke(
            main,
            ["--lang", lang, "--dry-run", "--target", str(real_resolve)],
        )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    # Soft safety warning names the no-touch sentinel in single-language format.
    assert "hermes-agent" in combined
    assert warning_marker in combined
    # Plan body still renders the per-site header in the selected language.
    assert patch_header in combined


# --- default (write) happy path -----------------------------------------


def test_cli_apply_default(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", "en", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK


def test_cli_check_no_writes(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", "en", "--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


@pytest.mark.parametrize(
    ("lang", "patch_header", "trailing_summary"),
    [
        ("en", "would patch:", "would be applied"),
        ("hu", "patchelné:", "kerülne alkalmazásra"),
    ],
)
def test_cli_dry_run_emits_plan_with_files_and_lines(
    lang: str,
    patch_header: str,
    trailing_summary: str,
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """``--dry-run`` emits a plan with file paths + line numbers.

    The plan body MUST contain the language-specific ``<patch header>: <file>``
    line for every site and the old/new diff preview with explicit
    ``line N:`` prefixes so the operator sees the exact changes that
    WOULD be applied. The output is single-language (selected via
    ``--lang``) with no ``[en]`` / ``[hu]`` prefix.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", lang, "--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    # Plan header is single-language.
    assert patch_header in combined
    # Per-site file path appears at least once.
    assert "agent/skill_utils.py" in combined
    # Diff preview with explicit line numbers.
    assert "line " in combined
    assert "- " in combined
    assert "+ " in combined
    assert 'return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."' in combined
    # Trailing NOT-APPLIED summary (dry_run mode) in the selected language.
    assert trailing_summary in combined


@pytest.mark.parametrize(
    ("lang", "plan_header", "dry_tail", "apply_tail"),
    [
        ("en", "plan for ", "would be applied", "patches applied"),
        ("hu", "terv a ", "kerülne alkalmazásra", "alkalmazva"),
    ],
)
def test_cli_dry_run_and_apply_both_emit_plan(
    lang: str,
    plan_header: str,
    dry_tail: str,
    apply_tail: str,
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Both ``--dry-run`` and apply modes render the plan header.

    The plan emitter is shared across modes so the operator can diff
    the two outputs visually — the only difference is the trailing
    tail (dry-run: NOT-APPLIED, apply: APPLIED). Single-language
    emission: no ``[en]`` / ``[hu]`` prefix on the plan header line.
    """
    runner = CliRunner()
    r_dry = runner.invoke(
        main,
        ["--lang", lang, "--dry-run", "--target", str(hermes_checkout)],
    )
    r_apply = runner.invoke(
        main,
        ["--lang", lang, "--target", str(hermes_checkout)],
    )
    assert r_dry.exit_code == EXIT_OK
    assert r_apply.exit_code == EXIT_OK
    dry_combined = r_dry.output + (r_dry.stderr or "")
    apply_combined = r_apply.output + (r_apply.stderr or "")
    # Plan header (single-string format) renders in both modes.
    assert plan_header in dry_combined
    assert plan_header in apply_combined
    # Trailing tails differ per language.
    assert dry_tail in dry_combined
    assert apply_tail in apply_combined


@pytest.mark.parametrize(
    ("lang", "applied_tail"),
    [
        ("en", "patches applied"),
        ("hu", "alkalmazva"),
    ],
)
def test_cli_apply_emits_applied_summary(
    lang: str,
    applied_tail: str,
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Apply mode emits the ``N patches applied`` summary.

    The tail message differs from ``--dry-run``: instead of the
    NOT-APPLIED warning, the apply path renders the
    ``N patches applied`` line so the operator knows the writes
    happened. Single-language emission: no ``[en]`` / ``[hu]`` prefix.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", lang, "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    assert applied_tail in combined


def test_cli_dry_run_no_writes_to_target(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Belt-and-suspenders: ``--dry-run`` writes ZERO bytes to the target."""
    runner = CliRunner()
    targets = [
        hermes_checkout / "agent" / "skill_utils.py",
        hermes_checkout / "agent" / "prompt_builder.py",
        hermes_checkout / "agent" / "background_review.py",
    ]
    pre_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    r = runner.invoke(
        main,
        ["--lang", "en", "--dry-run", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    for path in targets:
        post = hashlib.sha256(path.read_bytes()).hexdigest()
        assert pre_hashes[str(path)] == post, f"{path} was mutated by --dry-run"


def test_cli_task_e_check_mode_runs_by_default(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Task E is checked (not just applied) by default — no opt-out flag.

    ``--dry-run`` with ``--target`` (no Task E flag) must audit Task E
    sites too, producing exit 0 and surfacing every Task E site in the
    OK diagnostics.
    """
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", "en", "--dry-run", "--verbose", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    combined = r.output + (r.stderr or "")
    for site_id in (
        "E0.consult_rule_def",
        "E1.skills_guidance",
        "E2.memory_guidance",
        "E4.skill_review_prompt_opt4",
        "E5.combined_review_prompt_opt4",
    ):
        assert site_id in combined, f"Task E site {site_id} not checked by default"


def test_cli_verbose_emits_diagnostics(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--lang", "en", "--verbose", "--target", str(hermes_checkout)],
    )
    assert r.exit_code == EXIT_OK
    assert "OK" in r.output


def test_cli_default_writes(
    hermes_checkout: Path,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """When no flag is given, the CLI defaults to WRITES (exit 0 on success)."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    runner = CliRunner()
    r = runner.invoke(main, ["--lang", "en", "--target", str(hermes_checkout)])
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre != post


def test_cli_patch_main_entry_returns_main_exit_code(monkeypatch) -> None:
    """Calling the _main_entry function exercises the standalone CLI path."""
    from easter_hermes_sorry_skills import cli_patch

    monkeypatch.setattr(cli_patch, "main", lambda standalone_mode=False: None)
    assert cli_patch._main_entry() == 0
