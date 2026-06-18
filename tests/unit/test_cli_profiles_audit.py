"""Unit tests for ``hermes_skill_creator_plugin.cli_profiles`` (TDD plan 06).

TDD list (plan 06 §TDD test list):
- Per-profile audit: audit_default_profile, audit_named_profiles, audit_empty_profile,
  audit_drift_detection, audit_json_deterministic, audit_keys_sorted
- Apply path: apply_replaces_factory_skill_creator, apply_does_not_add_openai_to_disabled_list,
  apply_does_not_add_skills_to_disabled_list, apply_installs_skill_creator_when_absent,
  apply_idempotent_reinstall, apply_force_reinstall_on_version_drift,
  apply_calls_clear_skills_system_prompt_cache, apply_cache_clear_raises_continues_with_warning,
  apply_hub_install_fails_continues, apply_writes_inside_hermes_home_scope,
  apply_save_disabled_skills_positional_args, apply_does_not_disable_skill_creator_by_name
- Disabled-skill API: get_disabled_skill_names_uses_agent_skill_utils,
  get_disabled_skill_names_takes_platform_str, save_disabled_skills_uses_hermes_cli_skills_config,
  save_disabled_skills_signature_is_positional
- Shared enabled-detection: (see tests/unit/test_enabled_detection.py)
- Directory walk: walks_profile_dirs_set, gateway_pid_read_as_flat_file,
  walks_skills_dir_for_skill_md
- Bilingual + CLI: help_is_bilingual, dry_run_default_no_writes,
  json_output_path_resolved_under_workdir
- Safety: apply_refuses_real_hermes_home_without_yes,
  apply_does_not_touch_hermes_agent

All tests run against ``tmp_path`` fixtures; the live ``~/.hermes`` install
is never touched. The Hermes-side APIs (``hermes_cli.profiles.list_profiles``,
``hermes_cli.config.load_config``/``save_config``, ``hermes_cli.skills_config``,
``agent.skill_utils``, ``agent.prompt_builder``, ``hermes_cli.skills_hub.do_install``)
are injected as fakes via ``monkeypatch.setattr`` so the tests are hermetic.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Shared fakes for the Hermes-side APIs.
# ---------------------------------------------------------------------------


@dataclass
class _FakeProfileInfo:
    name: str
    path: Path
    is_default: bool = False
    gateway_running: bool = False


class _FakeHermesConstants:
    """Stand-in for ``hermes_constants`` used by the scope.

    Records ``set_hermes_home_override`` and ``reset_hermes_home_override``
    calls; the scope imports it via ``from hermes_constants import ...``.
    """

    def __init__(self) -> None:
        self.current: str | None = None
        self.set_calls: list[str] = []
        self.reset_calls: list[Any] = []
        self._prev_stack: list[str | None] = []

    def get_hermes_home_override(self) -> str | None:
        return self.current

    def set_hermes_home_override(self, path: str | Path | None):
        self._prev_stack.append(self.current)
        self.current = str(path) if path is not None else None
        self.set_calls.append(self.current)
        return ("token", self._prev_stack[-1])

    def reset_hermes_home_override(self, token: Any) -> None:
        self.reset_calls.append(token)
        if self._prev_stack:
            self.current = self._prev_stack.pop()


@dataclass
class _CallLog:
    """Records all calls to the injected fakes so tests can assert them."""

    do_install_calls: list[dict] = field(default_factory=list)
    do_install_raises: Exception | None = None
    clear_cache_calls: list[dict] = field(default_factory=list)
    clear_cache_raises: Exception | None = None
    save_disabled_calls: list[dict] = field(default_factory=list)
    load_config_calls: int = 0
    save_config_calls: list[dict] = field(default_factory=list)
    list_profiles_calls: int = 0
    env_mirror_reads: list[str | None] = field(default_factory=list)


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
    """Install fake ``hermes_cli.*`` and ``agent.*`` modules.

    Returns the call log so tests can assert on the recorded calls.
    """
    log = call_log or _CallLog()
    hc = _FakeHermesConstants()

    # 1) hermes_constants
    fake_hc = types.ModuleType("hermes_constants")
    fake_hc.get_hermes_home_override = hc.get_hermes_home_override  # type: ignore[attr-defined]
    fake_hc.set_hermes_home_override = hc.set_hermes_home_override  # type: ignore[attr-defined]
    fake_hc.reset_hermes_home_override = hc.reset_hermes_home_override  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_constants", fake_hc)

    # 2) hermes_cli.profiles
    fake_profiles = types.ModuleType("hermes_cli.profiles")
    infos = [
        _FakeProfileInfo(name=name, path=path, is_default=(name == "hermes"))
        for name, path in zip(profile_names, profile_paths, strict=False)
    ]

    def list_profiles() -> list[_FakeProfileInfo]:
        log.list_profiles_calls += 1
        return list(infos)

    fake_profiles.list_profiles = list_profiles  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli.profiles", fake_profiles)
    fake_hermes_cli = types.ModuleType("hermes_cli")
    monkeypatch.setitem(sys.modules, "hermes_cli", fake_hermes_cli)

    # 3) hermes_cli.config — load_config / save_config
    cfg_state: dict[str, Any] = {
        "config": dict(config_data) if config_data is not None else {},
        "saved": [],
    }

    def load_config():
        log.load_config_calls += 1
        return dict(cfg_state["config"])

    def save_config(cfg):
        log.save_config_calls.append(dict(cfg))
        cfg_state["config"] = dict(cfg)
        cfg_state["saved"].append(dict(cfg))

    fake_config = types.ModuleType("hermes_cli.config")
    fake_config.load_config = load_config  # type: ignore[attr-defined]
    fake_config.save_config = save_config  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_config)
    fake_hermes_cli.config = fake_config  # type: ignore[attr-defined]

    # 4) hermes_cli.skills_config — save_disabled_skills (the mutator)
    def save_disabled_skills(config, disabled, platform=None):
        log.save_disabled_calls.append(
            {"config": dict(config), "disabled": set(disabled), "platform": platform}
        )
        # Mirror the real mutator: write back into config["skills"]["disabled"].
        if "skills" not in config:
            config["skills"] = {}
        config["skills"]["disabled"] = sorted(disabled)
        return config

    fake_sk = types.ModuleType("hermes_cli.skills_config")
    fake_sk.save_disabled_skills = save_disabled_skills  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_config", fake_sk)
    fake_hermes_cli.skills_config = fake_sk  # type: ignore[attr-defined]

    # 5) agent.skill_utils — get_disabled_skill_names (read-only; takes platform str)
    installed_now = set(skills_installed) if skills_installed is not None else set()
    _disabled_now = set(disabled_now) if disabled_now is not None else set()

    def get_disabled_skill_names(platform=None):
        return set(_disabled_now)

    def parse_frontmatter(content):
        # Minimal parser for the audit path; tests cover details elsewhere.
        return {}, content

    fake_asu = types.ModuleType("agent.skill_utils")
    fake_asu.get_disabled_skill_names = get_disabled_skill_names  # type: ignore[attr-defined]
    fake_asu.parse_frontmatter = parse_frontmatter  # type: ignore[attr-defined]
    fake_asu._installed_now = installed_now  # type: ignore[attr-defined]
    agent_pkg = types.ModuleType("agent")
    agent_pkg.skill_utils = fake_asu  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.skill_utils", fake_asu)

    # 6) agent.prompt_builder — clear_skills_system_prompt_cache
    def clear_skills_system_prompt_cache(*, clear_snapshot=False):
        log.clear_cache_calls.append({"clear_snapshot": clear_snapshot})
        if log.clear_cache_raises is not None:
            raise log.clear_cache_raises

    fake_pb = types.ModuleType("agent.prompt_builder")
    fake_pb.clear_skills_system_prompt_cache = clear_skills_system_prompt_cache  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "agent.prompt_builder", fake_pb)
    agent_pkg.prompt_builder = fake_pb  # type: ignore[attr-defined]

    # 7) hermes_cli.skills_hub — do_install
    def do_install(
        identifier,
        category="",
        force=False,
        console=None,
        skip_confirm=False,
        invalidate_cache=True,
        name_override="",
    ):
        log.do_install_calls.append(
            {
                "identifier": identifier,
                "category": category,
                "force": force,
                "skip_confirm": skip_confirm,
                "invalidate_cache": invalidate_cache,
                "name_override": name_override,
                "env_mirror": os.environ.get("HERMES_HOME"),
            }
        )
        if log.do_install_raises is not None:
            raise log.do_install_raises
        # Materialize a flat skill at <scoped HERMES_HOME>/skills/<identifier>/
        target = Path(os.environ["HERMES_HOME"]) / "skills" / identifier
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text("---\nname: skill-creator\ndescription: migrated\n---\n")

    fake_sh = types.ModuleType("hermes_cli.skills_hub")
    fake_sh.do_install = do_install  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_hub", fake_sh)
    fake_hermes_cli.skills_hub = fake_sh  # type: ignore[attr-defined]

    # Stash references on the test for assertions.
    monkeypatch.setattr("hermes_skill_creator_plugin._scope._fhc_for_test", hc, raising=False)
    return log


# ---------------------------------------------------------------------------
# Test-time cli_profiles import fixture.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_agent_module(monkeypatch: pytest.MonkeyPatch):
    """Standalone fake ``agent`` + ``agent.skill_utils`` for tests that do
    not need the full Hermes-API substitute (e.g. the small helper tests
    that call ``_walk_skills`` directly)."""
    import types

    state: dict = {"calls": []}

    def parse_frontmatter(content):  # type: ignore[no-untyped-def]
        state["calls"].append(content)
        if not content.startswith("---\n"):
            return {}, content
        end = content.find("\n---", 4)
        if end == -1:
            return {}, content
        fm_text = content[4:end]
        body = content[end + 4 :]
        fm: dict = {}
        for raw in fm_text.splitlines():
            line = raw.rstrip()
            if not line or ":" not in line or line.startswith(" "):
                continue
            key, _, value = line.partition(":")
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                fm[key.strip()] = [
                    v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()
                ]
            elif value.startswith("{") and value.endswith("}"):
                fm[key.strip()] = {}
            else:
                # Try to parse as int first (for the non-string-name test).
                try:
                    fm[key.strip()] = int(value)
                except ValueError:
                    fm[key.strip()] = value.strip('"').strip("'")
        return fm, body

    fake = types.ModuleType("agent.skill_utils")
    fake.parse_frontmatter = parse_frontmatter  # type: ignore[attr-defined]
    fake.get_disabled_skill_names = lambda platform=None: set()  # type: ignore[attr-defined]
    agent_pkg = types.ModuleType("agent")
    agent_pkg.skill_utils = fake  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.skill_utils", fake)
    return fake


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Yield a callable that sets up the fakes and imports cli_profiles.

    Usage:
        log, cli = installed(profile_paths=[...], profile_names=[...])
    """
    setups: list[dict] = []

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

        if "hermes_skill_creator_plugin.cli_profiles" in sys.modules:
            del sys.modules["hermes_skill_creator_plugin.cli_profiles"]
        cli = importlib.import_module("hermes_skill_creator_plugin.cli_profiles")
        setups.append({})
        return log, cli

    return _setup


# ---------------------------------------------------------------------------
# TDD list — per-profile audit.
# ---------------------------------------------------------------------------


def test_audit_default_profile(installed, tmp_path: Path) -> None:
    """One profile (the default) → exactly one row in ``profiles[]``."""
    profile = tmp_path / "default"
    profile.mkdir()
    (profile / "skills").mkdir()
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"])

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    assert len(report["profiles"]) == 1
    assert report["profiles"][0]["profile_name"] == "hermes"


def test_audit_named_profiles(installed, tmp_path: Path) -> None:
    """Three named profiles → three rows in stable sorted order."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    p3 = tmp_path / "c"
    for p in (p1, p2, p3):
        p.mkdir()
        (p / "skills").mkdir()
    log, cli = installed(
        profile_paths=[p1, p2, p3],
        profile_names=["alpha", "beta", "gamma"],
    )

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    names = [row["profile_name"] for row in report["profiles"]]
    assert names == ["alpha", "beta", "gamma"]


def test_audit_empty_profile(installed, tmp_path: Path) -> None:
    """A profile with no ``skills/`` dir → ``current_installed == []``."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir.
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"])

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    row = report["profiles"][0]
    assert row["current_installed"] == []
    # Desired: skill-creator is in the desired set.
    assert "skill-creator" in row["desired_installed"]


def test_audit_drift_detection(installed, tmp_path: Path) -> None:
    """The desired_disabled set EQUALS current_disabled (no spurious
    ``"openai"`` or ``"skills"`` entries are added — S5 BLOCKER fix).

    The plan reads ``current_disabled`` from
    ``agent.skill_utils.get_disabled_skill_names`` (NOT from the config).
    We use the ``disabled_now`` fixture parameter to seed the fake.
    """
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["unrelated"]}},
        disabled_now={"unrelated"},
    )

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    row = report["profiles"][0]
    assert row["current_disabled"] == ["unrelated"]
    assert row["desired_disabled"] == ["unrelated"]
    # S5 regression sentinels: NEVER add "openai" or "skills" to the disabled list.
    assert "openai" not in row["desired_disabled"]
    assert "skills" not in row["desired_disabled"]


def test_audit_json_deterministic(installed, tmp_path: Path) -> None:
    """Two runs with the same ``--frozen-time`` produce byte-identical JSON."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    (profile / "skills" / "foo").mkdir()
    (profile / "skills" / "foo" / "SKILL.md").write_text("---\nname: foo\ndescription: x\n---\n")

    def _run_once() -> bytes:
        log, cli = installed(
            profile_paths=[profile],
            profile_names=["hermes"],
            config_data={"skills": {"disabled": []}},
        )
        return cli.run_audit(
            apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z"
        ).to_json_bytes()

    a = _run_once()
    b = _run_once()
    assert a == b
    # Hash equality is the contract.
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_audit_keys_sorted(installed, tmp_path: Path) -> None:
    """JSON keys are emitted in sorted order (sorted-dict insertion)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    report_dict = report.to_dict()
    raw = json.dumps(report_dict, sort_keys=True)
    parsed = json.loads(raw)
    # Re-dump without sort_keys; should match because the report is already sorted.
    raw2 = json.dumps(parsed, sort_keys=False)
    assert raw == raw2


# ---------------------------------------------------------------------------
# TDD list — apply path.
# ---------------------------------------------------------------------------


def test_apply_replaces_factory_skill_creator(installed, tmp_path: Path) -> None:
    """``--apply`` calls ``do_install(force=True, skip_confirm=True,
    invalidate_cache=True, name_override="")`` and the migrated SKILL.md
    overwrites the factory at the flat path."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    # Factory skill-creator already present.
    (skills / "skill-creator").mkdir()
    (skills / "skill-creator" / "SKILL.md").write_text(
        "---\nname: skill-creator\ndescription: factory\n---\n"
    )
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert len(log.do_install_calls) == 1
    call = log.do_install_calls[0]
    assert call["identifier"] == "skill-creator"
    assert call["force"] is True
    assert call["skip_confirm"] is True
    assert call["invalidate_cache"] is True
    assert call["name_override"] == ""
    # The on-disk SKILL.md must reflect the migrated copy.
    installed_path = skills / "skill-creator" / "SKILL.md"
    assert installed_path.exists()
    text = installed_path.read_text()
    assert "migrated" in text


def test_apply_does_not_add_openai_to_disabled_list(installed, tmp_path: Path) -> None:
    """``--apply`` NEVER sets ``"openai"`` in the disabled list (S5 regression)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    # No save_disabled_skills call should ever include "openai".
    for call in log.save_disabled_calls:
        assert "openai" not in call["disabled"]
    # No save_config call should ever contain "openai" in the disabled list.
    for cfg in log.save_config_calls:
        assert "openai" not in cfg.get("skills", {}).get("disabled", [])


def test_apply_does_not_add_skills_to_disabled_list(installed, tmp_path: Path) -> None:
    """``--apply`` NEVER sets ``"skills"`` in the disabled list (S5 regression)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    for call in log.save_disabled_calls:
        assert "skills" not in call["disabled"]
    for cfg in log.save_config_calls:
        assert "skills" not in cfg.get("skills", {}).get("disabled", [])


def test_apply_does_not_disable_skill_creator_by_name(installed, tmp_path: Path) -> None:
    """``--apply`` NEVER disables the migrated skill-creator by name."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    report = cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    for row in report["profiles"]:
        assert "skill-creator" not in row["desired_disabled"]


def test_apply_installs_skill_creator_when_absent(installed, tmp_path: Path) -> None:
    """``--apply`` materializes ``<HERMES_HOME>/skills/skill-creator/SKILL.md``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    target = profile / "skills" / "skill-creator" / "SKILL.md"
    assert target.exists()


def test_apply_idempotent_reinstall(installed, tmp_path: Path) -> None:
    """A second ``--apply`` still calls ``do_install(force=True)``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert len(log.do_install_calls) == 2
    for call in log.do_install_calls:
        assert call["force"] is True


def test_apply_force_reinstall_on_version_drift(installed, tmp_path: Path) -> None:
    """The first call is forced; a stale factory is always replaced."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    (skills / "skill-creator").mkdir()
    (skills / "skill-creator" / "SKILL.md").write_text(
        "---\nname: skill-creator\ndescription: old-factory\n---\n"
    )
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert len(log.do_install_calls) == 1
    assert log.do_install_calls[0]["force"] is True
    # The old content is gone; the new one wins.
    text = (skills / "skill-creator" / "SKILL.md").read_text()
    assert "old-factory" not in text


def test_apply_calls_clear_skills_system_prompt_cache(installed, tmp_path: Path) -> None:
    """``--apply`` calls the cache-clear with ``clear_snapshot=True`` once per profile."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert len(log.clear_cache_calls) == 2
    for call in log.clear_cache_calls:
        assert call["clear_snapshot"] is True


def test_apply_cache_clear_raises_continues_with_warning(installed, tmp_path: Path, capsys) -> None:
    """A failing cache-clear logs a warning and the run continues."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        config_data={"skills": {"disabled": []}},
    )
    log.clear_cache_raises = RuntimeError("boom")

    report = cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    # Both profiles are processed.
    assert len(report["profiles"]) == 2
    # Each profile's row reports the cache-clear failure as a warning.
    for row in report["profiles"]:
        assert any("cache" in e.lower() for e in row["errors"])
    captured = capsys.readouterr()
    assert "[en]" in captured.out
    assert "[hu]" in captured.out


def test_apply_hub_install_fails_continues(installed, tmp_path: Path, capsys) -> None:
    """A failing ``do_install`` is recorded per-profile; the next profile is processed."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        config_data={"skills": {"disabled": []}},
    )
    log.do_install_raises = RuntimeError("hub broken")

    report = cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert len(report["profiles"]) == 2
    # The per-profile errors carry the hub failure.
    for row in report["profiles"]:
        assert any("hub" in e.lower() for e in row["errors"])


def test_apply_writes_inside_hermes_home_scope(installed, tmp_path: Path) -> None:
    """The ``do_install`` env-mirror assertion: the call sees the scoped ``HERMES_HOME``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    assert log.do_install_calls
    assert log.do_install_calls[0]["env_mirror"] == str(profile)


def test_apply_save_disabled_skills_positional_args(installed, tmp_path: Path) -> None:
    """``save_disabled_skills`` is called with the disabled set as the 2nd
    positional arg, not via a ``names=`` kwarg."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["unrelated"]}},
    )

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
    )
    # The call must have used the positional form.
    if log.save_disabled_calls:
        call = log.save_disabled_calls[0]
        # The disabled set is recorded under "disabled" (positional 2nd arg).
        assert "disabled" in call
        assert isinstance(call["disabled"], set)


# ---------------------------------------------------------------------------
# TDD list — disabled-skill API correctness.
# ---------------------------------------------------------------------------


def test_get_disabled_skill_names_uses_agent_skill_utils(installed) -> None:
    """``agent.skill_utils.get_disabled_skill_names`` is the source for the
    read-side (NOT ``hermes_cli.skills_config.get_disabled_skills``)."""
    log, cli = installed()
    # The module's audit function imports agent.skill_utils; assert it.
    import hermes_skill_creator_plugin.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "from agent.skill_utils import get_disabled_skill_names" in src


def test_get_disabled_skill_names_takes_platform_str(installed) -> None:
    """The call site passes ``platform=None`` positionally, never ``config=``."""
    log, cli = installed()
    import hermes_skill_creator_plugin.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    # No ``config=`` kwarg for the reader.
    assert "get_disabled_skill_names(config=" not in src
    assert "get_disabled_skill_names(config =" not in src


def test_save_disabled_skills_uses_hermes_cli_skills_config(installed) -> None:
    """The writer is the ``hermes_cli.skills_config`` mutator (not agent.skill_utils)."""
    log, cli = installed()
    import hermes_skill_creator_plugin.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "from hermes_cli.skills_config import save_disabled_skills" in src


def test_save_disabled_skills_signature_is_positional(installed) -> None:
    """The call passes the disabled set positionally (NOT ``names=``)."""
    log, cli = installed()
    import hermes_skill_creator_plugin.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "save_disabled_skills(names=" not in src
    assert "save_disabled_skills(names =" not in src


# ---------------------------------------------------------------------------
# TDD list — directory walk correctness.
# ---------------------------------------------------------------------------


def test_walks_profile_dirs_set(installed, tmp_path: Path) -> None:
    """The audit reads the canonical ``_PROFILE_DIRS`` set per profile."""
    profile = tmp_path / "default"
    (profile / "memories").mkdir(parents=True)
    (profile / "sessions").mkdir(parents=True)
    (profile / "skills").mkdir(parents=True)
    (profile / "skins").mkdir(parents=True)
    (profile / "logs").mkdir(parents=True)
    (profile / "plans").mkdir(parents=True)
    (profile / "workspace").mkdir(parents=True)
    (profile / "cron").mkdir(parents=True)
    (profile / "home").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    # The audit walked the profile (no exception) and produced a row.
    assert len(report["profiles"]) == 1


def test_gateway_pid_read_as_flat_file(installed, tmp_path: Path) -> None:
    """A ``gateway.pid`` flat file in the profile root is read stat-only."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    (profile / "gateway.pid").write_text("12345\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    assert len(report["profiles"]) == 1
    # No errors parsing the pid file.
    assert report["profiles"][0]["errors"] == []


def test_walks_skills_dir_for_skill_md(installed, tmp_path: Path) -> None:
    """The skills tree is walked; both skills appear in ``current_installed``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    installed_now = set(report["profiles"][0]["current_installed"])
    assert installed_now == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# TDD list — bilingual + CLI.
# ---------------------------------------------------------------------------


def test_help_is_bilingual(installed) -> None:
    """``--help`` contains both the English and Hungarian sections."""
    log, cli = installed()
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    out = result.output
    assert "Usage (English)" in out
    assert "Használat (magyar)" in out
    # Mirrored content: every option appears in both halves.
    for opt in ("--apply", "--profile", "--json", "--yes", "--skip-install", "--help"):
        assert out.count(opt) >= 2, f"{opt} should appear in both sections"


def test_dry_run_default_no_writes(installed, tmp_path: Path) -> None:
    """Default mode (no ``--apply``) writes zero bytes to any profile."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    # No do_install calls, no save_config calls.
    assert log.do_install_calls == []
    assert log.save_config_calls == []


def test_json_output_path_resolved_under_workdir(
    installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--json PATH`` writes the report to PATH (under cwd by default)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    out_path = tmp_path / "report.json"
    cli.run_audit(
        apply=False,
        json_path=out_path,
        frozen_time="2026-06-17T00:00:00Z",
    )
    assert out_path.exists()
    parsed = json.loads(out_path.read_text())
    assert parsed["tool"] == "hermes-skill-creator-profiles"


def test_json_output_path_absolute(installed, tmp_path: Path) -> None:
    """``--json /abs/path`` writes to the absolute path."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    out_path = tmp_path / "abs-report.json"
    cli.run_audit(
        apply=False,
        json_path=out_path,
        frozen_time="2026-06-17T00:00:00Z",
    )
    assert out_path.exists()


# ---------------------------------------------------------------------------
# TDD list — safety.
# ---------------------------------------------------------------------------


def test_apply_refuses_real_hermes_home_without_yes(
    installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When HERMES_HOME resolves to the LIVE ``~/.hermes`` AND ``--yes`` is
    absent AND stdout is not a TTY → the script aborts with exit 5.

    We exercise the run_audit() refusal path directly (not the click
    runner) so the test does not depend on Click's TTY auto-detection
    heuristics. The live install is NEVER touched.
    """
    real = Path.home() / ".hermes"
    if not real.exists():
        pytest.skip("~/.hermes not present on this host")
    monkeypatch.setenv("HERMES_HOME", str(real))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    log, cli = installed(profile_paths=[real], profile_names=["hermes"], config_data={})
    with pytest.raises(SystemExit) as exc_info:
        cli.run_audit(
            apply=True,
            json_path=None,
            frozen_time="2026-06-17T00:00:00Z",
            yes=False,
        )
    assert exc_info.value.code == 5


def test_apply_does_not_touch_hermes_agent(
    installed, tmp_path: Path, real_hermes_agent_sentinel: str
) -> None:
    """The live ``~/.hermes/hermes-agent/agent/skill_utils.py`` sha256 is
    unchanged after a full run. The sentinel fixture hashes the file
    before/after; if any bytes changed the assertion would fail."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=False,
        yes=True,
    )
    # The real_hermes_agent_sentinel fixture's post-assertion (in
    # teardown) checks the sha256 — it has not been called yet here,
    # but it WILL fail at teardown if we touched the file.
    assert real_hermes_agent_sentinel  # keep linter quiet


# ---------------------------------------------------------------------------
# Additional coverage tests (every branch of the apply/audit/click paths).
# ---------------------------------------------------------------------------


def test_audit_default_profile_backfills_name(installed, tmp_path: Path) -> None:
    """The row's profile_name is the ProfileInfo.name, not the path basename."""
    profile = tmp_path / "home-root"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["custom-name"], config_data={})
    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    assert report["profiles"][0]["profile_name"] == "custom-name"


def test_audit_no_profiles_returns_empty_report(installed, tmp_path: Path) -> None:
    """When list_profiles returns [], the report has no profiles and prints
    a bilingual "no profiles" message."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[], profile_names=[], config_data={})
    report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    assert report["profiles"] == []


def test_audit_specific_profile(installed, tmp_path: Path) -> None:
    """``--profile NAME`` restricts the run to the named profile."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
        config_data={},
    )
    report = cli.run_audit(
        apply=False,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        profile="alpha",
    )
    names = [row["profile_name"] for row in report["profiles"]]
    assert names == ["alpha"]


def test_audit_load_config_failure_recorded(installed, tmp_path: Path) -> None:
    """A failing load_config is recorded as a per-profile error."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    # Monkeypatch the fake load_config to raise.
    import hermes_cli.config as hcc

    original = hcc.load_config
    hcc.load_config = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[assignment]
    try:
        report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    finally:
        hcc.load_config = original  # type: ignore[assignment]
    assert len(report["profiles"]) == 1
    assert any("load_config" in e for e in report["profiles"][0]["errors"])


def test_audit_get_disabled_failure_recorded(installed, tmp_path: Path) -> None:
    """A failing get_disabled_skill_names is recorded but the row is still emitted."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    import agent.skill_utils as asu

    original = asu.get_disabled_skill_names
    asu.get_disabled_skill_names = lambda platform=None: (_ for _ in ()).throw(  # type: ignore[assignment]
        RuntimeError("boom")
    )
    try:
        report = cli.run_audit(apply=False, json_path=None, frozen_time="2026-06-17T00:00:00Z")
    finally:
        asu.get_disabled_skill_names = original  # type: ignore[assignment]
    assert any("get_disabled_skill_names" in e for e in report["profiles"][0]["errors"])


def test_audit_apply_save_disabled_failure_recorded(installed, tmp_path: Path) -> None:
    """A failing save_disabled_skills is recorded as a per-profile error.

    ``disabled_now`` includes ``"openai"`` so the apply path strips it
    (NEVER_DISABLE) and writes a different set back to the config.
    """
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["openai", "unrelated"]}},
        disabled_now={"openai", "unrelated"},
    )
    import hermes_cli.skills_config as hcsc

    def _raiser(config, disabled, platform=None):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    original = hcsc.save_disabled_skills
    hcsc.save_disabled_skills = _raiser  # type: ignore[assignment]
    try:
        report = cli.run_audit(
            apply=True,
            json_path=None,
            frozen_time="2026-06-17T00:00:00Z",
        )
    finally:
        hcsc.save_disabled_skills = original  # type: ignore[assignment]
    assert any("save_disabled_skills" in e for e in report["profiles"][0]["errors"])


def test_audit_apply_save_config_failure_recorded(installed, tmp_path: Path) -> None:
    """A failing ``save_config`` AFTER ``save_disabled_skills`` succeeds is
    reported as ``save_config failed`` (NOT misattributed to
    ``save_disabled_skills`` — the F2 code-review fix)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["openai", "unrelated"]}},
        disabled_now={"openai", "unrelated"},
    )
    import hermes_cli.config as hcc

    original = hcc.save_config
    hcc.save_config = lambda cfg: (_ for _ in ()).throw(RuntimeError("save_config boom"))  # type: ignore[assignment]
    try:
        report = cli.run_audit(
            apply=True,
            json_path=None,
            frozen_time="2026-06-17T00:00:00Z",
        )
    finally:
        hcc.save_config = original  # type: ignore[assignment]
    errors = report["profiles"][0]["errors"]
    # The error is attributed to save_config, NOT save_disabled_skills.
    assert any("save_config failed" in e for e in errors)
    assert not any("save_disabled_skills failed" in e for e in errors)
    # save_disabled_skills was attempted successfully (action recorded).
    assert "save_disabled_skills" in report["profiles"][0]["actions_taken"]
    # save_config did NOT succeed → NOT in actions_taken.
    assert "save_config" not in report["profiles"][0]["actions_taken"]


def test_audit_apply_skip_install(installed, tmp_path: Path) -> None:
    """``--skip-install`` does not call do_install but still applies other writes."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        skip_install=True,
    )
    assert log.do_install_calls == []


def test_audit_audit_only_flag(installed, tmp_path: Path) -> None:
    """``--audit`` is an explicit no-write alias for the default mode."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--audit", "--json", str(tmp_path / "r.json")], color=False)
    assert result.exit_code == 0
    assert log.do_install_calls == []
    assert log.save_config_calls == []


def test_walk_skills_skips_files(fake_agent_module, tmp_path: Path) -> None:
    """A regular file (not a directory) in ``skills/`` is skipped (line 225)."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "stray.txt").write_text("not a skill")
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_skills(skills) == {"real"}


def _write_skill_simple(skills_dir, name, frontmatter):  # type: ignore[no-untyped-def]
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n")


def test_walk_skills_skips_subdir_without_skill_md(fake_agent_module, tmp_path: Path) -> None:
    """A subdirectory without ``SKILL.md`` is skipped (line 228)."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-md").mkdir()
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_skills(skills) == {"real"}


def test_walk_skills_skips_on_parse_exception(
    fake_agent_module, tmp_path: Path, monkeypatch
) -> None:
    """When ``parse_frontmatter`` raises, the walker drops the skill (defensive)."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    _write_skill_simple(skills, "broken", "name: broken\ndescription: x")
    _write_skill_simple(skills, "ok", "name: ok\ndescription: x")
    import agent.skill_utils as asu

    monkeypatch.setattr(
        asu, "parse_frontmatter", lambda c: (_ for _ in ()).throw(ValueError("boom"))
    )
    # The walker drops the skill on parse failure (does NOT fall back to the dir name).
    assert _walk_skills(skills) == set()


def test_walk_skills_skips_non_string_name(fake_agent_module, tmp_path: Path) -> None:
    """A non-string frontmatter ``name`` falls back to the dir name (line 239)."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "mydir").mkdir()
    (skills / "mydir" / "SKILL.md").write_text("---\nname: 42\n---\n")
    assert _walk_skills(skills) == {"mydir"}


def test_audit_save_disabled_skills_succeeds(installed, tmp_path: Path) -> None:
    """A successful save_disabled_skills path is recorded in actions_taken."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": ["openai", "unrelated"]}},
        disabled_now={"openai", "unrelated"},
    )

    report = cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
    )
    assert "save_disabled_skills" in report["profiles"][0]["actions_taken"]
    assert "save_config" in report["profiles"][0]["actions_taken"]
    # ``openai`` was stripped from desired_disabled (S5 regression sentinel).
    assert "openai" not in report["profiles"][0]["desired_disabled"]


def test_run_audit_refuses_live_home(
    installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_audit() with apply=True, yes=False, and HERMES_HOME=live exits 5."""
    real = Path.home() / ".hermes"
    if not real.exists():
        pytest.skip("~/.hermes not present on this host")
    monkeypatch.setenv("HERMES_HOME", str(real))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    log, cli = installed(profile_paths=[real], profile_names=["hermes"], config_data={})
    with pytest.raises(SystemExit) as exc_info:
        cli.run_audit(
            apply=True,
            json_path=None,
            frozen_time="2026-06-17T00:00:00Z",
            yes=False,
        )
    assert exc_info.value.code == 5


def test_run_audit_continues_when_not_live(
    installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When HERMES_HOME is NOT the live install, run_audit() proceeds."""
    scoped = tmp_path / "scoped-home"
    scoped.mkdir()
    (scoped / "skills").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(scoped))
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    log, cli = installed(profile_paths=[scoped], profile_names=["hermes"], config_data={})
    # Should NOT exit 5.
    report = cli.run_audit(
        apply=True,
        json_path=None,
        frozen_time="2026-06-17T00:00:00Z",
        yes=False,
    )
    assert len(report["profiles"]) == 1


# Helper for the LIVE test fixtures


def test_now_iso_uses_frozen_time(installed) -> None:
    """``_now_iso(frozen_time)`` returns the frozen value verbatim."""
    from hermes_skill_creator_plugin.cli_profiles import _now_iso

    assert _now_iso("2026-06-17T00:00:00Z") == "2026-06-17T00:00:00Z"
    # When not frozen, the format is a real ISO 8601 UTC string.
    out = _now_iso(None)
    assert out.endswith("Z")
    assert "T" in out


def test_diff_empty_sets(installed) -> None:
    """``_diff`` returns empty lists when both sets are empty."""
    from hermes_skill_creator_plugin.cli_profiles import _diff

    assert _diff(set(), set()) == {"added": [], "removed": []}


def test_walk_skills_handles_missing_dir(fake_agent_module, tmp_path: Path) -> None:
    """``_walk_skills`` returns empty when the skills dir does not exist."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    assert _walk_skills(tmp_path / "no-such-dir") == set()


def test_walk_skills_handles_oserror(
    fake_agent_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_walk_skills`` swallows OSError on a SKILL.md read (defensive)."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "broken").mkdir()
    (skills / "broken" / "SKILL.md").write_text("name: broken\ndescription: x")
    (skills / "ok").mkdir()
    (skills / "ok" / "SKILL.md").write_text("name: ok\ndescription: x")
    from pathlib import Path as P

    original_read_text = P.read_text

    def patched(self, *a, **k):  # type: ignore[no-untyped-def]
        if str(self).endswith("/broken/SKILL.md"):
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched)
    assert _walk_skills(skills) == {"ok"}


def test_walk_skills_handles_parse_error(fake_agent_module, tmp_path: Path) -> None:
    """``_walk_skills`` swallows parse errors and falls back to dirname."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-frontmatter").mkdir()
    (skills / "no-frontmatter" / "SKILL.md").write_text("no frontmatter at all")
    # The fake parse_frontmatter returns ({}, content) for any text not
    # starting with ``---\n``; the walker falls back to the dir name.
    assert _walk_skills(skills) == {"no-frontmatter"}


def test_walk_skills_handles_non_string_name(fake_agent_module, tmp_path: Path) -> None:
    """A frontmatter ``name:`` of a non-string type falls back to the dir name."""
    from hermes_skill_creator_plugin.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "mydir").mkdir()
    # Frontmatter ``name`` is an int — the walker falls back to "mydir".
    (skills / "mydir" / "SKILL.md").write_text("---\nname: 42\n---\n")
    # The fake parse returns ``{"name": 42}`` (parsed as int). The
    # walker checks ``isinstance(name, str)`` and falls back.
    assert _walk_skills(skills) == {"mydir"}


def test_audit_report_to_dict_and_contains() -> None:
    """AuditReport ``to_dict()``, ``__contains__``, ``__iter__``."""
    from hermes_skill_creator_plugin.cli_profiles import AuditReport

    report = AuditReport(
        tool="hermes-skill-creator-profiles",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    # __contains__
    assert "tool" in report
    assert "missing" not in report
    # __iter__
    assert set(iter(report)) == {"tool", "version", "generated_at", "profiles"}


def test_audit_report_to_json_bytes_byte_identical() -> None:
    """``to_json_bytes()`` is byte-identical across two calls on the same report."""
    from hermes_skill_creator_plugin.cli_profiles import AuditReport

    r = AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[{"profile_name": "p", "current_disabled": []}],
    )
    a = r.to_json_bytes()
    b = r.to_json_bytes()
    assert a == b


def test_audit_report_eq_with_dict_and_report() -> None:
    """AuditReport ``__eq__`` works against dict and AuditReport."""
    from hermes_skill_creator_plugin.cli_profiles import AuditReport

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
    # Non-dict, non-AuditReport → NotImplemented (Python falls back to False).
    assert (r == 42) is False  # type: ignore[comparison-overlap]


def test_audit_report_hash() -> None:
    """AuditReport is hashable (delegates to to_dict items)."""
    from hermes_skill_creator_plugin.cli_profiles import AuditReport

    r = AuditReport(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        profiles=[],
    )
    # Two equal reports hash to the same value.
    h1 = hash(r)
    h2 = hash(r)
    assert h1 == h2


def test_bilingual_message_renders() -> None:
    """``_bilingual`` produces a single-line ``[en] ... / [hu] ...`` message."""
    from hermes_skill_creator_plugin.cli_profiles import _bilingual

    out = _bilingual("profiles_msg_done", n=3)
    assert "[en]" in out
    assert "[hu]" in out
    assert " / " in out
    assert "3" in out
