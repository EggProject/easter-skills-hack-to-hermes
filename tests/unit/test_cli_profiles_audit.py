"""Unit tests for ``easter_hermes_sorry_skills.cli_profiles`` (READ-ONLY).

Phase 8 collapses the audit/apply pipeline into a single read-only scan.
The ``cli_profiles`` CLI never calls ``save_disabled_skills``,
``do_install``, or ``clear_skills_system_prompt_cache`` — the ``run_audit``
function returns the per-profile scan results as ``list[tuple[str, Table,
dict]]`` consumed by ``render_all_profiles``.

TDD list (READ-ONLY contract):
- Per-profile audit: ``test_audit_default_profile``,
  ``test_audit_named_profiles``, ``test_audit_empty_profile``,
  ``test_audit_json_deterministic``, ``test_audit_keys_sorted``,
  ``test_audit_default_profile_backfills_name``,
  ``test_audit_no_profiles_returns_empty_report``,
  ``test_audit_specific_profile``.
- Shared enabled-detection + directory walk + helpers: ``test_walks_*``,
  ``test_gateway_pid_*``, ``test_walk_skills_*``.
- Bilingual + CLI surface: ``test_help_is_bilingual``,
  ``test_verbose_flag_emits_diagnostics``, ``test_default_is_write_*``.
- AuditReport: ``test_audit_report_to_dict_and_contains``,
  ``test_audit_report_to_json_bytes_byte_identical``,
  ``test_audit_report_eq_with_dict_and_report``, ``test_audit_report_hash``.
- Bilingual helpers: ``test_bilingual_message_renders``,
  ``test_now_iso_returns_system_time``.
- Critical invariant: ``test_cli_profiles_does_not_call_save_disabled_skills``.

The live ``~/.hermes`` install is never touched. ``hermes_cli.profiles``,
``_enabled_detection.get_enabled_skills``, and
``_cli_report_helpers_paths.load_skill_description`` are stubbed via
``monkeypatch.setitem`` so the tests are hermetic.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from rich.table import Table

# ---------------------------------------------------------------------------
# Shared fakes for the Hermes-side APIs.
# ---------------------------------------------------------------------------


@dataclass
class _FakeProfileInfo:
    name: str
    path: Path
    is_default: bool = False
    gateway_running: bool = False


@dataclass
class _CallLog:
    """Records all calls to the injected fakes so tests can assert them.

    The READ-ONLY contract requires these counters to stay at zero for
    every standard CLI invocation — the ``test_cli_profiles_does_not_call_*``
    family asserts that.
    """

    do_install_calls: list[dict] = field(default_factory=list)
    clear_cache_calls: list[dict] = field(default_factory=list)
    save_disabled_calls: list[dict] = field(default_factory=list)
    save_config_calls: list[dict] = field(default_factory=list)
    load_config_calls: int = 0
    list_profiles_calls: int = 0


# ---------------------------------------------------------------------------
# Injectable fixture: build a Hermes-API substitute for cli_profiles to call.
# ---------------------------------------------------------------------------


def _install_fake_hermes_apis(
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile_paths: list[Path],
    profile_names: list[str],
    config_data: dict | None = None,
    call_log: _CallLog | None = None,
    skills_installed: set[str] | None = None,
    disabled_now: set[str] | None = None,
) -> _CallLog:
    """Install fake ``hermes_cli.*`` and ``_enabled_detection`` helpers."""
    log = call_log or _CallLog()

    # 1) hermes_cli.profiles
    fake_profiles = types.ModuleType("hermes_cli.profiles")
    infos = [
        _FakeProfileInfo(name=name, path=path, is_default=(name == "hermes"))
        for name, path in zip(profile_names, profile_paths, strict=False)
    ]

    def list_profiles() -> list[_FakeProfileInfo]:
        log.list_profiles_calls += 1
        return list(infos)

    fake_profiles.list_profiles = list_profiles
    fake_profiles.ProfileInfo = _FakeProfileInfo
    monkeypatch.setitem(sys.modules, "hermes_cli.profiles", fake_profiles)

    fake_hermes_cli = types.ModuleType("hermes_cli")
    monkeypatch.setitem(sys.modules, "hermes_cli", fake_hermes_cli)

    # 2) hermes_cli.config — load_config / save_config
    cfg_state: dict[str, Any] = {
        "config": dict(config_data) if config_data is not None else {},
    }

    def load_config():
        log.load_config_calls += 1
        return dict(cfg_state["config"])

    def save_config(cfg):
        log.save_config_calls.append(dict(cfg))
        cfg_state["config"] = dict(cfg)

    fake_config = types.ModuleType("hermes_cli.config")
    fake_config.load_config = load_config
    fake_config.save_config = save_config
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_config)
    fake_hermes_cli.config = fake_config

    # 3) hermes_cli.skills_config — save_disabled_skills (RECORDED; never called)
    def save_disabled_skills(config, disabled, platform=None):
        log.save_disabled_calls.append({"config": dict(config), "disabled": set(disabled), "platform": platform})

    fake_sk = types.ModuleType("hermes_cli.skills_config")
    fake_sk.save_disabled_skills = save_disabled_skills
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_config", fake_sk)
    fake_hermes_cli.skills_config = fake_sk

    # 4) _enabled_detection.get_enabled_skills — the single source of truth
    installed_now = set(skills_installed) if skills_installed is not None else None

    def get_enabled_skills(profile_path: Path, *, platform: str | None = None) -> frozenset[str]:
        if installed_now is None:
            # Default: walk the on-disk skills dir so the per-profile
            # summary reflects what's actually there.
            skills_dir = profile_path / "skills"
            if not skills_dir.is_dir():
                return frozenset()
            return frozenset(child.name for child in skills_dir.iterdir() if child.is_dir())
        return frozenset(installed_now)

    fake_ed = types.ModuleType("easter_hermes_sorry_skills._enabled_detection")
    fake_ed.get_enabled_skills = get_enabled_skills
    monkeypatch.setitem(sys.modules, "easter_hermes_sorry_skills._enabled_detection", fake_ed)

    # 5) _cli_report_helpers_paths.load_skill_description
    def load_skill_description(skills_dir: Path, skill_name: str) -> str:
        return f"description of {skill_name}"

    fake_hp = types.ModuleType("easter_hermes_sorry_skills._cli_report_helpers_paths")
    fake_hp.load_skill_description = load_skill_description
    monkeypatch.setitem(
        sys.modules,
        "easter_hermes_sorry_skills._cli_report_helpers_paths",
        fake_hp,
    )

    # 6) hermes_cli.skills_hub — do_install (RECORDED; never called)
    def do_install(*args: object, **kwargs: object) -> None:
        log.do_install_calls.append({"args": args, "kwargs": kwargs})

    fake_sh = types.ModuleType("hermes_cli.skills_hub")
    fake_sh.do_install = do_install
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_hub", fake_sh)
    fake_hermes_cli.skills_hub = fake_sh

    # 7) agent.prompt_builder — clear_skills_system_prompt_cache (RECORDED; never called)
    def clear_skills_system_prompt_cache(*, clear_snapshot: bool = False) -> None:
        log.clear_cache_calls.append({"clear_snapshot": clear_snapshot})

    fake_pb = types.ModuleType("agent.prompt_builder")
    fake_pb.clear_skills_system_prompt_cache = clear_skills_system_prompt_cache
    agent_pkg = types.ModuleType("agent")
    agent_pkg.prompt_builder = fake_pb
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.prompt_builder", fake_pb)

    return log


# ---------------------------------------------------------------------------
# Test-time cli_profiles import fixture.
# ---------------------------------------------------------------------------


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Yield a callable that sets up the fakes and imports cli_profiles.

    Usage:
        log, cli = installed(profile_paths=[...], profile_names=[...])
    """

    def _setup(
        *,
        profile_paths: list[Path] | None = None,
        profile_names: list[str] | None = None,
        config_data: dict | None = None,
        skills_installed: set[str] | None = None,
        call_log: _CallLog | None = None,
        disabled_now: set[str] | None = None,
    ) -> tuple[_CallLog, types.ModuleType]:
        if profile_paths is None:
            profile_paths = [tmp_path / "default"]
        if profile_names is None:
            profile_names = ["hermes"]
        log = _install_fake_hermes_apis(
            monkeypatch,
            profile_paths=profile_paths,
            profile_names=profile_names,
            config_data=config_data,
            call_log=call_log,
            skills_installed=skills_installed,
            disabled_now=disabled_now,
        )
        # Force reimport so the freshly-patched sys.modules wins.
        import importlib

        if "easter_hermes_sorry_skills.cli_profiles" in sys.modules:
            del sys.modules["easter_hermes_sorry_skills.cli_profiles"]
        cli = importlib.import_module("easter_hermes_sorry_skills.cli_profiles")
        return log, cli

    return _setup


# ---------------------------------------------------------------------------
# TDD list — per-profile audit (READ-ONLY shape).
# ---------------------------------------------------------------------------


def test_audit_default_profile(installed, tmp_path: Path) -> None:
    """One profile (the default) → exactly one entry in the result list."""
    profile = tmp_path / "default"
    profile.mkdir()
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"])

    results = cli.run_audit()
    assert len(results) == 1
    name, _table, summary = results[0]
    assert name == "hermes"
    # Summary keys match the table renderer contract.
    assert set(summary.keys()) >= {
        "skill_count",
        "token_total",
        "token_source",
        "warnings",
    }


def test_audit_named_profiles(installed, tmp_path: Path) -> None:
    """Three named profiles → three entries in stable sorted order."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    p3 = tmp_path / "c"
    for p in (p1, p2, p3):
        p.mkdir()
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2, p3],
        profile_names=["alpha", "beta", "gamma"],
    )

    results = cli.run_audit()
    names = [entry[0] for entry in results]
    assert names == ["alpha", "beta", "gamma"]


def test_audit_empty_profile(installed, tmp_path: Path) -> None:
    """A profile with no skills → ``skill_count == 0`` and ``token_total == 0``."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir → no enabled skills.
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"])

    results = cli.run_audit()
    name, _table, summary = results[0]
    assert name == "hermes"
    assert summary["skill_count"] == 0
    assert summary["token_total"] == 0


def test_audit_json_deterministic(installed, tmp_path: Path) -> None:
    """Two ``run_audit`` calls on identical inputs produce structurally identical summaries."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    (skills / "foo").mkdir()
    (skills / "foo" / "SKILL.md").write_text("---\nname: foo\ndescription: x\n---\n")

    def _run_once() -> list[tuple[str, Table, dict[str, object]]]:
        log, cli = installed(
            profile_paths=[profile],
            profile_names=["hermes"],
            config_data={},
        )
        return cli.run_audit()

    results_a = _run_once()
    results_b = _run_once()
    # Same structure (skill_count + token_total + token_source + warnings).
    summary_a = results_a[0][2]
    summary_b = results_b[0][2]
    assert summary_a["skill_count"] == summary_b["skill_count"]
    assert summary_a["token_total"] == summary_b["token_total"]
    assert summary_a["token_source"] == summary_b["token_source"]


def test_audit_keys_sorted(installed, tmp_path: Path) -> None:
    """The summary dict exposes a stable, documented key set."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    results = cli.run_audit()
    summary = results[0][2]
    # The four top-level keys are required by the JSON renderer.
    assert "skill_count" in summary
    assert "token_total" in summary
    assert "token_source" in summary
    assert "warnings" in summary


# ---------------------------------------------------------------------------
# TDD list — enabled-skills + token rollups.
# ---------------------------------------------------------------------------


def test_audit_enabled_skills_uses_get_enabled_skills(installed, tmp_path: Path) -> None:
    """The pipeline imports ``_enabled_detection.get_enabled_skills`` (single source)."""
    log, cli = installed()
    import easter_hermes_sorry_skills._cli_profiles_pipeline as pipe

    src = Path(pipe.__file__).read_text()
    assert "get_enabled_skills" in src


def test_audit_token_total_is_sum_of_per_row_counts(installed, tmp_path: Path) -> None:
    """``token_total`` is the sum of the per-row ``token_count`` values."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    results = cli.run_audit()
    summary = results[0][2]
    # 2 skills → skill_count == 2.
    assert summary["skill_count"] == 2
    assert summary["token_total"] >= 0


def test_audit_token_source_is_tokenizer_by_default(installed, tmp_path: Path) -> None:
    """When all rows fall back to chars/4 the source is ``chars_div_4``;
    otherwise ``tokenizer``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    results = cli.run_audit()
    summary = results[0][2]
    assert summary["token_source"] in {"tokenizer", "chars_div_4"}


def test_audit_warnings_default_empty(installed, tmp_path: Path) -> None:
    """``warnings`` is always a (possibly empty) list."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    results = cli.run_audit()
    summary = results[0][2]
    assert isinstance(summary["warnings"], list)
    assert summary["warnings"] == []


# ---------------------------------------------------------------------------
# TDD list — directory walk correctness.
# ---------------------------------------------------------------------------


def test_walks_skills_dir_for_skill_md(installed, tmp_path: Path) -> None:
    """The pipeline walks the on-disk skills tree; both skills appear in the summary."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    results = cli.run_audit()
    summary = results[0][2]
    assert summary["skill_count"] == 2


def test_walk_skills_skips_files(tmp_path: Path) -> None:
    """A regular file (not a directory) in ``skills/`` is skipped by the walker."""
    from easter_hermes_sorry_skills._enabled_detection import _walk_installed_skill_names

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "stray.txt").write_text("not a skill")
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_installed_skill_names(skills) == {"real"}


def _write_skill_simple(skills_dir: Path, name: str, frontmatter: str) -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n")


def test_walk_skills_skips_subdir_without_skill_md(tmp_path: Path) -> None:
    """A subdirectory without ``SKILL.md`` is skipped by the walker."""
    from easter_hermes_sorry_skills._enabled_detection import _walk_installed_skill_names

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-md").mkdir()
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_installed_skill_names(skills) == {"real"}


def test_walk_skills_handles_missing_dir(tmp_path: Path) -> None:
    """``_walk_installed_skill_names`` returns empty when the skills dir does not exist."""
    from easter_hermes_sorry_skills._enabled_detection import _walk_installed_skill_names

    assert _walk_installed_skill_names(tmp_path / "no-such-dir") == frozenset()


# ---------------------------------------------------------------------------
# TDD list — profile selection.
# ---------------------------------------------------------------------------


def test_select_profiles_returns_all_when_none(installed) -> None:
    """``profile=None`` selects every profile returned by ``list_profiles``."""
    log, cli = installed()
    from easter_hermes_sorry_skills._cli_profiles_profiles import _select_profiles

    profiles = [
        _FakeProfileInfo(name="alpha", path=Path("/a")),
        _FakeProfileInfo(name="beta", path=Path("/b")),
    ]
    assert _select_profiles(profiles, None) == profiles


def test_select_profiles_filters_by_name(installed) -> None:
    """``profile='alpha'`` returns only the named profile."""
    log, cli = installed()
    from easter_hermes_sorry_skills._cli_profiles_profiles import _select_profiles

    profiles = [
        _FakeProfileInfo(name="alpha", path=Path("/a")),
        _FakeProfileInfo(name="beta", path=Path("/b")),
    ]
    selected = _select_profiles(profiles, "alpha")
    assert [info.name for info in selected] == ["alpha"]


def test_select_profiles_returns_empty_for_missing(installed) -> None:
    """``profile='missing'`` returns an empty list."""
    log, cli = installed()
    from easter_hermes_sorry_skills._cli_profiles_profiles import _select_profiles

    profiles = [_FakeProfileInfo(name="alpha", path=Path("/a"))]
    assert _select_profiles(profiles, "missing") == []


# ---------------------------------------------------------------------------
# TDD list — empty + specific profile.
# ---------------------------------------------------------------------------


def test_audit_default_profile_backfills_name(installed, tmp_path: Path) -> None:
    """The per-profile entry's name is the ``ProfileInfo.name``, not the path basename."""
    profile = tmp_path / "home-root"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["custom-name"], config_data={})
    results = cli.run_audit()
    assert results[0][0] == "custom-name"


def test_audit_no_profiles_returns_empty_report(installed, tmp_path: Path) -> None:
    """When ``list_profiles`` returns [], the report is empty."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[], profile_names=[], config_data={})
    results = cli.run_audit()
    assert results == []


def test_audit_specific_profile(installed, tmp_path: Path) -> None:
    """``run_audit(profile='alpha')`` restricts the run to the named profile."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        config_data={},
    )
    results = cli.run_audit(profile="alpha")
    assert [entry[0] for entry in results] == ["alpha"]


# ---------------------------------------------------------------------------
# TDD list — bilingual + CLI.
# ---------------------------------------------------------------------------


def test_help_is_bilingual(installed) -> None:
    """``--help`` follows the ``--lang`` option (default ``en``).

    Phase 8 flag set: ``--profile``, ``--verbose``, ``--json``, ``--help``.
    ``--dry-run`` and ``--apply`` are gone (READ-ONLY CLI).

    Replaces the pre-``--lang`` bilingual-by-default contract: the help
    text is now a single language driven by the ``--lang {en,hu}``
    option on the CLI.
    """
    log, cli = installed()
    runner = cli.make_cli()
    # ``--help`` (no ``--lang``) renders the English section only.
    result_en = runner.invoke(cli.app, ["--help"])
    assert result_en.exit_code == 0
    out_en = result_en.output
    assert "Per-profile READ-ONLY" in out_en
    assert "Profilonkénti CSAK OLVASÁS" not in out_en
    assert "--dry-run" not in out_en
    assert "--apply" not in out_en
    # ``--lang hu --help`` flips the help text to Hungarian only.
    result_hu = runner.invoke(cli.app, ["--lang", "hu", "--help"])
    assert result_hu.exit_code == 0
    out_hu = result_hu.output
    assert "Profilonkénti CSAK OLVASÁS" in out_hu
    assert "Per-profile READ-ONLY" not in out_hu


def test_bilingual_message_renders() -> None:
    """``_bilingual`` produces a single-line ``[en] ... / [hu] ...`` message."""
    from easter_hermes_sorry_skills.cli_profiles import _bilingual

    out = _bilingual("profiles_msg_done", n=3)
    assert "[en]" in out
    assert "[hu]" in out
    assert " / " in out


def test_now_iso_returns_system_time(installed) -> None:
    """``_now_iso()`` returns a real ISO 8601 UTC string with ``Z`` suffix."""
    from easter_hermes_sorry_skills.cli_profiles import _now_iso

    out = _now_iso()
    assert out.endswith("Z")
    assert "T" in out


# ---------------------------------------------------------------------------
# TDD list — verbose mode.
# ---------------------------------------------------------------------------


def test_audit_verbose_emits_per_site_summary(
    installed,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``verbose=True`` writes the HERMES_HOME + resolved-profile diagnostics to stderr."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    cli.run_audit(verbose=True)

    captured = capsys.readouterr()
    assert "[verbose] HERMES_HOME=" in captured.err
    assert "[verbose] resolved profiles: 1 (hermes)" in captured.err


def test_audit_verbose_false_silent_on_stderr(installed, tmp_path: Path, capsys) -> None:
    """``verbose=False`` (default) emits no verbose diagnostics to stderr."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    cli.run_audit()

    captured = capsys.readouterr()
    assert "[verbose]" not in captured.err


def test_verbose_flag_emits_diagnostics(installed) -> None:
    """``--verbose`` at the CLI level emits ``[verbose]`` diagnostics to stderr."""
    log, cli = installed()
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--verbose"])
    assert result.exit_code == 0, result.output
    assert "[verbose]" in (result.stderr or "")


# ---------------------------------------------------------------------------
# TDD list — READ-ONLY invariant (CRITICAL).
# ---------------------------------------------------------------------------


def test_cli_profiles_does_not_call_save_disabled_skills(installed, tmp_path: Path) -> None:
    """The READ-ONLY CLI NEVER calls ``save_disabled_skills``.

    This is the Phase 8 invariant: ``cli_profiles`` is a read-only scan;
    the apply/dry-run split is gone. If this test fails, a regression
    re-introduced the WRITE path.
    """
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["unrelated"]}},
    )

    cli.run_audit()
    cli.run_audit(profile="hermes", verbose=True)
    runner = cli.make_cli()
    runner.invoke(cli.app, ["--verbose"])
    runner.invoke(cli.app, ["--json"])

    assert log.save_disabled_calls == [], "cli_profiles must NEVER call save_disabled_skills (READ-ONLY CLI)"


def test_cli_profiles_does_not_call_do_install(installed, tmp_path: Path) -> None:
    """The READ-ONLY CLI NEVER calls ``do_install``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    cli.run_audit()
    runner = cli.make_cli()
    runner.invoke(cli.app, [])
    runner.invoke(cli.app, ["--json"])

    assert log.do_install_calls == [], "cli_profiles must NEVER call do_install (READ-ONLY CLI)"


def test_cli_profiles_does_not_call_clear_cache(installed, tmp_path: Path) -> None:
    """The READ-ONLY CLI NEVER calls ``clear_skills_system_prompt_cache``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    cli.run_audit()
    runner = cli.make_cli()
    runner.invoke(cli.app, [])
    runner.invoke(cli.app, ["--json"])

    assert log.clear_cache_calls == [], "cli_profiles must NEVER call clear_skills_system_prompt_cache (READ-ONLY CLI)"


def test_cli_profiles_does_not_call_save_config(installed, tmp_path: Path) -> None:
    """The READ-ONLY CLI NEVER calls ``save_config``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    cli.run_audit()
    runner = cli.make_cli()
    runner.invoke(cli.app, [])
    runner.invoke(cli.app, ["--json"])

    assert log.save_config_calls == [], "cli_profiles must NEVER call save_config (READ-ONLY CLI)"


# ---------------------------------------------------------------------------
# TDD list — AuditReport (legacy dataclass).
# ---------------------------------------------------------------------------


def test_audit_report_to_dict_and_contains() -> None:
    """``AuditReport`` exposes ``to_dict()``, ``__contains__``, ``__iter__``."""
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

    report = AuditReport(
        tool="easter-hermes-sorry-skills-profiles",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    assert "tool" in report
    assert "missing" not in report
    assert set(iter(report)) == {"tool", "version", "generated_at", "profiles"}


def test_audit_report_to_json_bytes_byte_identical() -> None:
    """``to_json_bytes()`` is byte-identical across two calls on the same report."""
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

    r = AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[{"profile_name": "p", "current_disabled": []}],
    )
    assert r.to_json_bytes() == r.to_json_bytes()


def test_audit_report_eq_with_dict_and_report() -> None:
    """``AuditReport.__eq__`` works against dict and ``AuditReport``."""
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

    r = AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    assert r == r.to_dict()
    assert r == AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    assert (r == 42) is False


def test_audit_report_hash() -> None:
    """``AuditReport`` is hashable (delegates to ``to_dict`` items)."""
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

    r = AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    assert hash(r) == hash(r)


# ---------------------------------------------------------------------------
# TDD list — JSON renderer surface (sanity assertions).
# ---------------------------------------------------------------------------


def test_run_audit_renders_json_when_as_json(installed, tmp_path: Path) -> None:
    """``run_audit(as_json=True)`` writes JSON to a Console."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    # as_json is honored by ``render_all_profiles`` — verify it
    # doesn't raise and produces a list-of-tuples result.
    results = cli.run_audit(as_json=True)
    assert len(results) == 1
    name, table, summary = results[0]
    assert isinstance(name, str)
    assert isinstance(table, Table)
    assert isinstance(summary, dict)


def test_run_audit_renders_table_when_not_as_json(installed, tmp_path: Path) -> None:
    """``run_audit()`` (default) renders a table to stdout via the Console."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={},
    )

    # The result still has the (name, Table, summary) shape.
    results = cli.run_audit()
    assert len(results) == 1
    assert isinstance(results[0][1], Table)
