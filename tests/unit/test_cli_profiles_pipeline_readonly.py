"""Unit tests for ``_cli_profiles_pipeline._run_audit_phase`` (READ-ONLY).

TDD list (Phase D):
- ``test_run_audit_phase_profile_filter_none_returns_loop`` — no filter, loop over all.
- ``test_run_audit_phase_profile_filter_default_one_profile`` — ``--profile default``.
- ``test_run_audit_phase_empty_profile_list`` — zero profiles.
- ``test_run_audit_phase_one_profile`` — single profile, one entry.
- ``test_run_audit_phase_multiple_profiles`` — multiple profiles, stable order.
- ``test_run_audit_phase_in_process_loop`` — exercise the loop body directly.

These tests bypass the click surface (``run_audit``) and target the
``_run_audit_phase`` orchestrator directly so the loop body + the
per-profile summary shape can be asserted in isolation.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from rich.table import Table


@dataclass
class _FakeProfileInfo:
    name: str
    path: Path
    is_default: bool = False
    gateway_running: bool = False


@dataclass
class _CallLog:
    do_install_calls: list[dict] = field(default_factory=list)
    clear_cache_calls: list[dict] = field(default_factory=list)
    save_disabled_calls: list[dict] = field(default_factory=list)
    save_config_calls: list[dict] = field(default_factory=list)


def _install_pipeline_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile_paths: list[Path],
    profile_names: list[str],
    call_log: _CallLog | None = None,
    skill_to_description: dict[str, str] | None = None,
) -> _CallLog:
    """Install fakes for ``hermes_cli`` + ``_enabled_detection`` + helpers."""
    log = call_log or _CallLog()

    # 1) hermes_cli.profiles
    fake_profiles = types.ModuleType("hermes_cli.profiles")
    infos = [
        _FakeProfileInfo(name=name, path=path, is_default=(name == "hermes"))
        for name, path in zip(profile_names, profile_paths, strict=False)
    ]

    def list_profiles() -> list[_FakeProfileInfo]:
        return list(infos)

    fake_profiles.list_profiles = list_profiles
    fake_profiles.ProfileInfo = _FakeProfileInfo
    monkeypatch.setitem(sys.modules, "hermes_cli.profiles", fake_profiles)
    fake_hermes_cli = types.ModuleType("hermes_cli")
    monkeypatch.setitem(sys.modules, "hermes_cli", fake_hermes_cli)

    # 2) _enabled_detection.get_enabled_skills
    skills_per_profile: dict[Path, set[str]] = {}
    for path in profile_paths:
        skills_dir = path / "skills"
        if skills_dir.is_dir():
            skills_per_profile[path] = {child.name for child in skills_dir.iterdir() if child.is_dir()}
        else:
            skills_per_profile[path] = set()

    def get_enabled_skills(profile_path: Path, *, platform: str | None = None) -> frozenset[str]:
        return frozenset(skills_per_profile.get(profile_path, set()))

    fake_ed = types.ModuleType("easter_hermes_sorry_skills._enabled_detection")
    fake_ed.get_enabled_skills = get_enabled_skills
    monkeypatch.setitem(
        sys.modules,
        "easter_hermes_sorry_skills._enabled_detection",
        fake_ed,
    )

    # 3) _cli_report_helpers_paths.load_skill_description
    descriptions = skill_to_description or {}

    def load_skill_description(skills_dir: Path, skill_name: str) -> str:
        return descriptions.get(skill_name, f"description of {skill_name}")

    fake_hp = types.ModuleType("easter_hermes_sorry_skills._cli_report_helpers_paths")
    fake_hp.load_skill_description = load_skill_description
    monkeypatch.setitem(
        sys.modules,
        "easter_hermes_sorry_skills._cli_report_helpers_paths",
        fake_hp,
    )

    # 4) WRITE-path fakes — recorded but never called.
    def do_install(*args: object, **kwargs: object) -> None:
        log.do_install_calls.append({"args": args, "kwargs": kwargs})

    def save_disabled_skills(config: dict, disabled: set, platform: str | None = None) -> None:
        log.save_disabled_calls.append({"config": dict(config), "disabled": set(disabled), "platform": platform})

    def save_config(cfg: dict) -> None:
        log.save_config_calls.append(dict(cfg))

    def clear_skills_system_prompt_cache(*, clear_snapshot: bool = False) -> None:
        log.clear_cache_calls.append({"clear_snapshot": clear_snapshot})

    fake_sh = types.ModuleType("hermes_cli.skills_hub")
    fake_sh.do_install = do_install
    fake_sk = types.ModuleType("hermes_cli.skills_config")
    fake_sk.save_disabled_skills = save_disabled_skills
    fake_cfg = types.ModuleType("hermes_cli.config")
    fake_cfg.save_config = save_config
    fake_hermes_cli.skills_hub = fake_sh
    fake_hermes_cli.skills_config = fake_sk
    fake_hermes_cli.config = fake_cfg
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_hub", fake_sh)
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_config", fake_sk)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_cfg)

    fake_pb = types.ModuleType("agent.prompt_builder")
    fake_pb.clear_skills_system_prompt_cache = clear_skills_system_prompt_cache
    agent_pkg = types.ModuleType("agent")
    agent_pkg.prompt_builder = fake_pb
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.prompt_builder", fake_pb)

    return log


@pytest.fixture
def pipeline_setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Yield a callable that returns ``(log, results)`` after running the pipeline."""
    setups: list[Any] = []

    def _setup(
        *,
        profile_paths: list[Path] | None = None,
        profile_names: list[str] | None = None,
        skill_to_description: dict[str, str] | None = None,
        profile_filter: str | None = None,
        verbose: bool = False,
    ) -> tuple[_CallLog, list[tuple[str, Table, dict[str, object]]]]:
        if profile_paths is None:
            profile_paths = [tmp_path / "default"]
        if profile_names is None:
            profile_names = ["hermes"]
        # Ensure the skills/ subdir exists for each profile path so the
        # walker behaves realistically (the default-profile case uses
        # an empty profile which is exercised separately).
        for p in profile_paths:
            # Create the parent profile dir, then the skills/ subdir.
            p.mkdir(parents=True, exist_ok=True)
            (p / "skills").mkdir(parents=True, exist_ok=True)
        log = _install_pipeline_fakes(
            monkeypatch,
            profile_paths=profile_paths,
            profile_names=profile_names,
            skill_to_description=skill_to_description,
        )
        import importlib

        # Force a fresh import so the freshly-patched sys.modules wins.
        for module_name in list(sys.modules):
            if (
                module_name.startswith("easter_hermes_sorry_skills._cli_profiles")
                or module_name == "easter_hermes_sorry_skills._enabled_detection"
                or module_name == "easter_hermes_sorry_skills._cli_report_helpers_paths"
            ):
                del sys.modules[module_name]
        if "easter_hermes_sorry_skills.cli_profiles" in sys.modules:
            del sys.modules["easter_hermes_sorry_skills.cli_profiles"]
        pipeline = importlib.import_module("easter_hermes_sorry_skills._cli_profiles_pipeline")

        results = pipeline._run_audit_phase(
            {"profile": profile_filter},
            verbose=verbose,
            as_json=False,
        )
        setups.append(results)
        return log, results

    return _setup


# ---------------------------------------------------------------------------
# TDD list — profile_filter=None (loop over all profiles).
# ---------------------------------------------------------------------------


def test_run_audit_phase_profile_filter_none_returns_loop(pipeline_setup, tmp_path: Path) -> None:
    """``profile_filter=None`` runs the loop over every profile returned by ``list_profiles``."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    log, results = pipeline_setup(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        profile_filter=None,
    )
    assert [entry[0] for entry in results] == ["alpha", "beta"]
    # Each entry is (name, Table, summary).
    for name, table, summary in results:
        assert isinstance(name, str)
        assert isinstance(table, Table)
        assert isinstance(summary, dict)
        assert "skill_count" in summary
        assert "token_total" in summary
        assert "token_source" in summary
        assert "warnings" in summary


# ---------------------------------------------------------------------------
# TDD list — --profile default (one profile).
# ---------------------------------------------------------------------------


def test_run_audit_phase_profile_filter_default_one_profile(pipeline_setup, tmp_path: Path) -> None:
    """``profile_filter='hermes'`` returns exactly one entry."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    log, results = pipeline_setup(
        profile_paths=[p1, p2],
        profile_names=["alpha", "hermes"],
        profile_filter="hermes",
    )
    assert len(results) == 1
    assert results[0][0] == "hermes"


# ---------------------------------------------------------------------------
# TDD list — empty profile list.
# ---------------------------------------------------------------------------


def test_run_audit_phase_empty_profile_list(pipeline_setup) -> None:
    """Zero profiles → empty result list."""
    log, results = pipeline_setup(
        profile_paths=[],
        profile_names=[],
        profile_filter=None,
    )
    assert results == []


# ---------------------------------------------------------------------------
# TDD list — one profile.
# ---------------------------------------------------------------------------


def test_run_audit_phase_one_profile(pipeline_setup, tmp_path: Path) -> None:
    """A single profile yields a single (name, Table, summary) entry."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    (profile / "skills" / "alpha").mkdir()
    (profile / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: x\n---\n")

    log, results = pipeline_setup(
        profile_paths=[profile],
        profile_names=["hermes"],
        profile_filter=None,
    )
    assert len(results) == 1
    name, table, summary = results[0]
    assert name == "hermes"
    assert isinstance(table, Table)
    print(f"DEBUG summary={summary} rows_count={len(table.rows)}")
    assert summary["skill_count"] == 1
    assert summary["token_total"] >= 0


# ---------------------------------------------------------------------------
# TDD list — multiple profiles.
# ---------------------------------------------------------------------------


def test_run_audit_phase_multiple_profiles(pipeline_setup, tmp_path: Path) -> None:
    """Multiple profiles yield multiple entries in stable order."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    p3 = tmp_path / "c"
    for p in (p1, p2, p3):
        (p / "skills").mkdir(parents=True)

    log, results = pipeline_setup(
        profile_paths=[p1, p2, p3],
        profile_names=["alpha", "beta", "gamma"],
        profile_filter=None,
    )
    assert [entry[0] for entry in results] == ["alpha", "beta", "gamma"]
    # Every summary carries the documented keys.
    for _name, _table, summary in results:
        assert set(summary.keys()) >= {
            "skill_count",
            "token_total",
            "token_source",
            "warnings",
        }


# ---------------------------------------------------------------------------
# TDD list — in-process loop (direct _run_audit_phase call).
# ---------------------------------------------------------------------------


def test_run_audit_phase_in_process_loop(pipeline_setup, tmp_path: Path) -> None:
    """The in-process loop exercises ``_run_audit_phase`` directly with verbose=False."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")

    log, results = pipeline_setup(
        profile_paths=[profile],
        profile_names=["hermes"],
        profile_filter=None,
        verbose=False,
        skill_to_description={"alpha": "the alpha skill", "beta": "the beta skill"},
    )

    assert len(results) == 1
    _name, _table, summary = results[0]
    assert summary["skill_count"] == 2
    assert summary["token_total"] >= 0
    # No write-path calls were issued.
    assert log.do_install_calls == []
    assert log.save_disabled_calls == []
    assert log.save_config_calls == []
    assert log.clear_cache_calls == []


# ---------------------------------------------------------------------------
# TDD list — verbose path covers extra branches.
# ---------------------------------------------------------------------------


def test_run_audit_phase_verbose_emits_diagnostics(
    pipeline_setup, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``verbose=True`` writes ``[verbose]`` lines to stderr."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, results = pipeline_setup(
        profile_paths=[profile],
        profile_names=["hermes"],
        profile_filter=None,
        verbose=True,
    )
    assert len(results) == 1
    captured = capsys.readouterr()
    assert "[verbose] HERMES_HOME=" in captured.err
    assert "[verbose] resolved profiles:" in captured.err
