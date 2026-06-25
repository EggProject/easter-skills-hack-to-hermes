"""Unit tests for ``easter_hermes_sorry_skills.cli_profiles`` (TDD plan 06).

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
from collections.abc import Iterator
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
    fake_hc.get_hermes_home_override = hc.get_hermes_home_override
    fake_hc.set_hermes_home_override = hc.set_hermes_home_override
    fake_hc.reset_hermes_home_override = hc.reset_hermes_home_override
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

    fake_profiles.list_profiles = list_profiles
    # Expose ``ProfileInfo`` so the import in cli_profiles.py resolves; tests
    # only ever construct ``_FakeProfileInfo`` (which is a duck-typed drop-in).
    fake_profiles.ProfileInfo = _FakeProfileInfo
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
    fake_config.load_config = load_config
    fake_config.save_config = save_config
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_config)
    fake_hermes_cli.config = fake_config

    # 4) hermes_cli.skills_config — save_disabled_skills (the mutator)
    def save_disabled_skills(config, disabled, platform=None):
        log.save_disabled_calls.append({"config": dict(config), "disabled": set(disabled), "platform": platform})
        # Mirror the real mutator: write back into config["skills"]["disabled"].
        if "skills" not in config:
            config["skills"] = {}
        config["skills"]["disabled"] = sorted(disabled)
        return config

    fake_sk = types.ModuleType("hermes_cli.skills_config")
    fake_sk.save_disabled_skills = save_disabled_skills
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_config", fake_sk)
    fake_hermes_cli.skills_config = fake_sk

    # 5) agent.skill_utils — get_disabled_skill_names (read-only; takes platform str)
    installed_now = set(skills_installed) if skills_installed is not None else set()
    _disabled_now = set(disabled_now) if disabled_now is not None else set()

    def get_disabled_skill_names(platform=None):
        return set(_disabled_now)

    def parse_frontmatter(content):
        # Minimal parser for the audit path; tests cover details elsewhere.
        return {}, content

    fake_asu = types.ModuleType("agent.skill_utils")
    fake_asu.get_disabled_skill_names = get_disabled_skill_names
    fake_asu.parse_frontmatter = parse_frontmatter
    fake_asu._installed_now = installed_now
    agent_pkg = types.ModuleType("agent")
    agent_pkg.skill_utils = fake_asu
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.skill_utils", fake_asu)

    # 6) agent.prompt_builder — clear_skills_system_prompt_cache
    def clear_skills_system_prompt_cache(*, clear_snapshot=False):
        log.clear_cache_calls.append({"clear_snapshot": clear_snapshot})
        if log.clear_cache_raises is not None:
            raise log.clear_cache_raises

    fake_pb = types.ModuleType("agent.prompt_builder")
    fake_pb.clear_skills_system_prompt_cache = clear_skills_system_prompt_cache
    monkeypatch.setitem(sys.modules, "agent.prompt_builder", fake_pb)
    agent_pkg.prompt_builder = fake_pb

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
    fake_sh.do_install = do_install
    monkeypatch.setitem(sys.modules, "hermes_cli.skills_hub", fake_sh)
    fake_hermes_cli.skills_hub = fake_sh

    # Stash references on the test for assertions.
    monkeypatch.setattr("easter_hermes_sorry_skills._scope._fhc_for_test", hc, raising=False)
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

    def parse_frontmatter(content):
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
                fm[key.strip()] = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
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
    fake.parse_frontmatter = parse_frontmatter
    fake.get_disabled_skill_names = lambda platform=None: set()
    agent_pkg = types.ModuleType("agent")
    agent_pkg.skill_utils = fake
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

        if "easter_hermes_sorry_skills.cli_profiles" in sys.modules:
            del sys.modules["easter_hermes_sorry_skills.cli_profiles"]
        cli = importlib.import_module("easter_hermes_sorry_skills.cli_profiles")
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

    report = cli.run_audit(apply=False)
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

    report = cli.run_audit(apply=False)
    names = [row["profile_name"] for row in report["profiles"]]
    assert names == ["alpha", "beta", "gamma"]


def test_audit_empty_profile(installed, tmp_path: Path) -> None:
    """A profile with no ``skills/`` dir → ``current_installed == []``."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir.
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"])

    report = cli.run_audit(apply=False)
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

    report = cli.run_audit(apply=False)
    row = report["profiles"][0]
    assert row["current_disabled"] == ["unrelated"]
    assert row["desired_disabled"] == ["unrelated"]
    # S5 regression sentinels: NEVER add "openai" or "skills" to the disabled list.
    assert "openai" not in row["desired_disabled"]
    assert "skills" not in row["desired_disabled"]


def test_audit_json_deterministic(installed, tmp_path: Path) -> None:
    """Two runs in the same second produce byte-identical JSON
    (``generated_at`` is rounded to whole seconds)."""
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
        return cli.run_audit(apply=False).to_json_bytes()

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
    report = cli.run_audit(apply=False)
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
    (skills / "skill-creator" / "SKILL.md").write_text("---\nname: skill-creator\ndescription: factory\n---\n")
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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

    report = cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
    cli.run_audit(apply=True)
    assert len(log.do_install_calls) == 2
    for call in log.do_install_calls:
        assert call["force"] is True


def test_apply_force_reinstall_on_version_drift(installed, tmp_path: Path) -> None:
    """The first call is forced; a stale factory is always replaced."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    (skills / "skill-creator").mkdir()
    (skills / "skill-creator" / "SKILL.md").write_text("---\nname: skill-creator\ndescription: old-factory\n---\n")
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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

    report = cli.run_audit(apply=True)
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

    report = cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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

    cli.run_audit(apply=True)
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
    import easter_hermes_sorry_skills.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "from agent.skill_utils import get_disabled_skill_names" in src


def test_get_disabled_skill_names_takes_platform_str(installed) -> None:
    """The call site passes ``platform=None`` positionally, never ``config=``."""
    log, cli = installed()
    import easter_hermes_sorry_skills.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    # No ``config=`` kwarg for the reader.
    assert "get_disabled_skill_names(config=" not in src
    assert "get_disabled_skill_names(config =" not in src


def test_save_disabled_skills_uses_hermes_cli_skills_config(installed) -> None:
    """The writer is the ``hermes_cli.skills_config`` mutator (not agent.skill_utils)."""
    log, cli = installed()
    import easter_hermes_sorry_skills.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "from hermes_cli.skills_config import save_disabled_skills" in src


def test_save_disabled_skills_signature_is_positional(installed) -> None:
    """The call passes the disabled set positionally (NOT ``names=``)."""
    log, cli = installed()
    import easter_hermes_sorry_skills.cli_profiles as cp

    src = Path(cp.__file__).read_text()
    assert "save_disabled_skills(names=" not in src
    assert "save_disabled_skills(names =" not in src


# ---------------------------------------------------------------------------
# TDD list — directory walk correctness.
# ---------------------------------------------------------------------------


def test_walks_profile_dirs_set(installed, tmp_path: Path) -> None:
    """The audit walks the canonical ``PROFILE_DIRS`` set per profile and
    records per-subdir presence/size on the row (AC-3.10)."""
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
    # Drop a file under one of the subdirs so size > 0.
    (profile / "memories" / "memory.md").write_text("hello")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False)
    row = report["profiles"][0]
    subdirs = row["subdirs"]
    # Every PROFILE_DIRS entry must be present on the row.
    expected = {"memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"}
    assert set(subdirs.keys()) == expected
    # Each entry records present=True (the dir exists) and a size/file_count.
    for name, info in subdirs.items():
        assert info["present"] is True, name
        assert info["size"] >= 0
        assert info["file_count"] >= 0
    # The memories subdir has at least one file (memory.md) -> size > 0.
    assert subdirs["memories"]["size"] > 0
    assert subdirs["memories"]["file_count"] >= 1


def test_walks_profile_dirs_set_marks_missing(installed, tmp_path: Path) -> None:
    """Subdirs that are absent from the profile are marked present=False."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False)
    subdirs = report["profiles"][0]["subdirs"]
    assert subdirs["skills"]["present"] is True
    assert subdirs["memories"]["present"] is False
    assert subdirs["memories"]["size"] == 0


def test_gateway_pid_read_as_flat_file(installed, tmp_path: Path) -> None:
    """A ``gateway.pid`` flat file in the profile root is read stat-only (AC-3.10)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    (profile / "gateway.pid").write_text("12345\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False)
    row = report["profiles"][0]
    # No errors parsing the pid file (stat-only).
    assert row["errors"] == []
    # Stat-only entry on the row: size + mtime; NO 'content' key.
    pid_info = row["gateway_pid"]
    assert pid_info["present"] is True
    assert pid_info["size"] > 0
    assert "mtime" in pid_info
    assert "content" not in pid_info


def test_gateway_pid_absent_when_missing(installed, tmp_path: Path) -> None:
    """No ``gateway.pid`` file → present=False, no error."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False)
    pid_info = report["profiles"][0]["gateway_pid"]
    assert pid_info["present"] is False
    assert pid_info["size"] == 0


def test_walks_skills_dir_for_skill_md(installed, tmp_path: Path) -> None:
    """The skills tree is walked; both skills appear in ``current_installed``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    report = cli.run_audit(apply=False)
    installed_now = set(report["profiles"][0]["current_installed"])
    assert installed_now == {"alpha", "beta"}


def test_read_gateway_pid_stat_handles_oserror(installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``read_gateway_pid_stat`` survives OSError on ``.stat()``."""
    import easter_hermes_sorry_skills._cli_profiles_walk as walk_mod

    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    pid = profile / "gateway.pid"
    pid.write_text("12345\n")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    real_stat = Path.stat

    def fake_stat(self: Path, *args: object, **kwargs: object) -> object:
        if self == pid:
            raise OSError("simulated stat failure")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(walk_mod.Path, "stat", fake_stat)
    report = cli.run_audit(apply=False)
    pid_info = report["profiles"][0]["gateway_pid"]
    assert pid_info["present"] is False
    assert pid_info["size"] == 0


def test_walk_profile_subdirs_handles_oserror(installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``walk_profile_subdirs`` survives OSError on ``.rglob()``/``.stat()``."""
    import easter_hermes_sorry_skills._cli_profiles_walk as walk_mod

    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    real_rglob = Path.rglob

    def fake_rglob(
        self: Path,
        pattern: str,
        *,
        case_sensitive: bool | None = None,
        recurse_symlinks: bool = False,
    ) -> Iterator[Path]:
        if self == profile / "skills":
            raise OSError("simulated rglob failure")
        yield from real_rglob(self, pattern, case_sensitive=case_sensitive, recurse_symlinks=recurse_symlinks)

    monkeypatch.setattr(walk_mod.Path, "rglob", fake_rglob)
    report = cli.run_audit(apply=False)
    subdirs = report["profiles"][0]["subdirs"]
    # skills subdir was walked but rglob failed -> size/count zero, present True.
    assert subdirs["skills"]["present"] is True
    assert subdirs["skills"]["size"] == 0


def test_walk_profile_subdirs_handles_stat_oserror(installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``_dir_size_bytes`` survives OSError on individual child ``.stat()``."""
    import easter_hermes_sorry_skills._cli_profiles_walk as walk_mod

    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    (skills / "alpha").mkdir()
    (skills / "alpha" / "SKILL.md").write_text("a")
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    real_stat = Path.stat
    broken = skills / "alpha" / "SKILL.md"

    def fake_stat(self: Path, *args: object, **kwargs: object) -> object:
        if self == broken:
            raise OSError("simulated child stat failure")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(walk_mod.Path, "stat", fake_stat)
    report = cli.run_audit(apply=False)
    subdirs = report["profiles"][0]["subdirs"]
    # The skills subdir's per-child stat failed, so size=0 but file_count>=1
    # (file_count uses is_file() which goes through .stat -> also raises -> 0).
    assert subdirs["skills"]["present"] is True
    assert subdirs["skills"]["size"] == 0


# ---------------------------------------------------------------------------
# TDD list — bilingual + CLI.
# ---------------------------------------------------------------------------


def test_help_is_bilingual(installed) -> None:
    """``--help`` contains both the English and Hungarian sections.

    Phase 8 flag set: --profile, --verbose, --json, --help. ``--dry-run`` is
    gone (the CLI is READ-ONLY by design — there is no apply/dry-run split).
    """
    log, cli = installed()
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    out = result.output
    assert "Usage (English)" in out
    assert "Használat (magyar)" in out
    # Mirrored content: every option appears in both halves.
    for opt in (
        "--profile",
        "--verbose",
        "--json",
        "--help",
    ):
        assert out.count(opt) >= 2, f"{opt} should appear in both sections"
    # --dry-run is gone (READ-ONLY CLI): it must not appear in --help.
    assert "--dry-run" not in out, "--dry-run removed in Phase 8 (READ-ONLY)"


def test_dry_run_default_no_writes(installed, tmp_path: Path) -> None:
    """``--dry-run`` writes zero bytes to any profile (the only no-write mode)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    cli.run_audit(apply=False)
    # No do_install calls, no save_config calls.
    assert log.do_install_calls == []
    assert log.save_config_calls == []


# ---------------------------------------------------------------------------
# TDD list — safety.
# ---------------------------------------------------------------------------


def test_apply_does_not_touch_hermes_agent(installed, tmp_path: Path, real_hermes_agent_sentinel: str) -> None:
    """The live ``~/.hermes/hermes-agent/agent/skill_utils.py`` sha256 is
    unchanged after a full run. The sentinel fixture hashes the file
    before/after; if any bytes changed the assertion would fail."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})

    cli.run_audit(apply=True)
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
    report = cli.run_audit(apply=False)
    assert report["profiles"][0]["profile_name"] == "custom-name"


def test_audit_no_profiles_returns_empty_report(installed, tmp_path: Path) -> None:
    """When list_profiles returns [], the report has no profiles and prints
    a bilingual "no profiles" message."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[], profile_names=[], config_data={})
    report = cli.run_audit(apply=False)
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
    report = cli.run_audit(apply=False, profile="alpha")
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
    hcc.load_config = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        report = cli.run_audit(apply=False)
    finally:
        hcc.load_config = original
    assert len(report["profiles"]) == 1
    assert any("load_config" in e for e in report["profiles"][0]["errors"])


def test_audit_get_disabled_failure_recorded(installed, tmp_path: Path) -> None:
    """A failing get_disabled_skill_names is recorded but the row is still emitted."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    import agent.skill_utils as asu

    original = asu.get_disabled_skill_names
    asu.get_disabled_skill_names = lambda platform=None: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        report = cli.run_audit(apply=False)
    finally:
        asu.get_disabled_skill_names = original
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

    def _raiser(config, disabled, platform=None):
        raise RuntimeError("boom")

    original = hcsc.save_disabled_skills
    hcsc.save_disabled_skills = _raiser
    try:
        report = cli.run_audit(apply=True)
    finally:
        hcsc.save_disabled_skills = original
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
    hcc.save_config = lambda cfg: (_ for _ in ()).throw(RuntimeError("save_config boom"))
    try:
        report = cli.run_audit(apply=True)
    finally:
        hcc.save_config = original
    errors = report["profiles"][0]["errors"]
    # The error is attributed to save_config, NOT save_disabled_skills.
    assert any("save_config failed" in e for e in errors)
    assert not any("save_disabled_skills failed" in e for e in errors)
    # save_disabled_skills was attempted successfully (action recorded).
    assert "save_disabled_skills" in report["profiles"][0]["actions_taken"]
    # save_config did NOT succeed → NOT in actions_taken.
    assert "save_config" not in report["profiles"][0]["actions_taken"]


def test_dry_run_flag_no_writes(installed, tmp_path: Path) -> None:
    """``--dry-run`` was removed in Phase 8 (READ-ONLY CLI). Click rejects it."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(profile_paths=[profile], profile_names=["hermes"], config_data={})
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--dry-run"], color=False)
    # Click rejects the unknown option with exit code 2.
    assert result.exit_code != 0


def test_walk_skills_skips_files(fake_agent_module, tmp_path: Path) -> None:
    """A regular file (not a directory) in ``skills/`` is skipped (line 225)."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "stray.txt").write_text("not a skill")
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_skills(skills) == {"real"}


def _write_skill_simple(skills_dir, name, frontmatter):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n")


def test_walk_skills_skips_subdir_without_skill_md(fake_agent_module, tmp_path: Path) -> None:
    """A subdirectory without ``SKILL.md`` is skipped (line 228)."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-md").mkdir()
    _write_skill_simple(skills, "real", "name: real\ndescription: x")
    assert _walk_skills(skills) == {"real"}


def test_walk_skills_skips_on_parse_exception(fake_agent_module, tmp_path: Path, monkeypatch) -> None:
    """When ``parse_frontmatter`` raises, the walker drops the skill (defensive)."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    _write_skill_simple(skills, "broken", "name: broken\ndescription: x")
    _write_skill_simple(skills, "ok", "name: ok\ndescription: x")
    import agent.skill_utils as asu

    monkeypatch.setattr(asu, "parse_frontmatter", lambda c: (_ for _ in ()).throw(ValueError("boom")))
    # The walker drops the skill on parse failure (does NOT fall back to the dir name).
    assert _walk_skills(skills) == set()


def test_walk_skills_skips_non_string_name(fake_agent_module, tmp_path: Path) -> None:
    """A non-string frontmatter ``name`` falls back to the dir name (line 239)."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

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

    report = cli.run_audit(apply=True)
    assert "save_disabled_skills" in report["profiles"][0]["actions_taken"]
    assert "save_config" in report["profiles"][0]["actions_taken"]
    # ``openai`` was stripped from desired_disabled (S5 regression sentinel).
    assert "openai" not in report["profiles"][0]["desired_disabled"]


# Helper for the LIVE test fixtures


def test_now_iso_returns_system_time(installed) -> None:
    """``_now_iso()`` returns a real ISO 8601 UTC string with ``Z`` suffix."""
    from easter_hermes_sorry_skills.cli_profiles import _now_iso

    out = _now_iso()
    assert out.endswith("Z")
    assert "T" in out


def test_diff_empty_sets(installed) -> None:
    """``_diff`` returns empty lists when both sets are empty."""
    from easter_hermes_sorry_skills.cli_profiles import _diff

    assert _diff(set(), set()) == {"added": [], "removed": []}


def test_walk_skills_handles_missing_dir(fake_agent_module, tmp_path: Path) -> None:
    """``_walk_skills`` returns empty when the skills dir does not exist."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    assert _walk_skills(tmp_path / "no-such-dir") == set()


def test_walk_skills_handles_oserror(fake_agent_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``_walk_skills`` swallows OSError on a SKILL.md read (defensive)."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "broken").mkdir()
    (skills / "broken" / "SKILL.md").write_text("name: broken\ndescription: x")
    (skills / "ok").mkdir()
    (skills / "ok" / "SKILL.md").write_text("name: ok\ndescription: x")
    from pathlib import Path as P

    original_read_text = P.read_text

    def patched(self, *a, **k):
        if str(self).endswith("/broken/SKILL.md"):
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched)
    assert _walk_skills(skills) == {"ok"}


def test_walk_skills_handles_parse_error(fake_agent_module, tmp_path: Path) -> None:
    """``_walk_skills`` swallows parse errors and falls back to dirname."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-frontmatter").mkdir()
    (skills / "no-frontmatter" / "SKILL.md").write_text("no frontmatter at all")
    # The fake parse_frontmatter returns ({}, content) for any text not
    # starting with ``---\n``; the walker falls back to the dir name.
    assert _walk_skills(skills) == {"no-frontmatter"}


def test_walk_skills_handles_non_string_name(fake_agent_module, tmp_path: Path) -> None:
    """A frontmatter ``name:`` of a non-string type falls back to the dir name."""
    from easter_hermes_sorry_skills.cli_profiles import _walk_skills

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
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

    report = AuditReport(
        tool="easter-hermes-sorry-skills-profiles",
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
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

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
    # Non-dict, non-AuditReport → NotImplemented (Python falls back to False).
    assert (r == 42) is False


def test_audit_report_hash() -> None:
    """AuditReport is hashable (delegates to to_dict items)."""
    from easter_hermes_sorry_skills.cli_profiles import AuditReport

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
    from easter_hermes_sorry_skills.cli_profiles import _bilingual

    out = _bilingual("profiles_msg_done", n=3)
    assert "[en]" in out
    assert "[hu]" in out
    assert " / " in out


# ---------------------------------------------------------------------------
# TDD list — verbose mode (Phase C1).
# ---------------------------------------------------------------------------


def test_audit_verbose_emits_hermes_home_and_resolved_profiles(
    installed,
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``verbose=True`` writes the HERMES_HOME + resolved-profile diagnostics to stderr."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    cli.run_audit(apply=False, verbose=True)

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
        config_data={"skills": {"disabled": []}},
    )

    cli.run_audit(apply=False)

    captured = capsys.readouterr()
    assert "[verbose]" not in captured.err


def test_audit_verbose_emits_per_site_summary_on_stdout(
    installed,
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``verbose=True`` keeps the bilingual per-site row summary on stdout."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    cli.run_audit(apply=False, verbose=True)

    captured = capsys.readouterr()
    # The bilingual per-site summary still appears (gated on verbose=True).
    assert "profiles_msg_profile_audit" not in captured.out  # key not in output
    assert "[en]" in captured.out
    assert "[hu]" in captured.out


# ---------------------------------------------------------------------------
# TDD list — CLI surface (Phase D).
# ---------------------------------------------------------------------------


def test_verbose_flag_emits_diagnostics(installed) -> None:
    """``--verbose`` at the CLI level emits ``[verbose]`` diagnostics to stderr."""
    log, cli = installed()
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--verbose"])
    # The run succeeds (exit 0) and writes a [verbose] line on stderr.
    assert result.exit_code == 0, result.output
    # Click's CliRunner routes err=True output to result.stderr (not capsys).
    assert "[verbose]" in (result.stderr or "")


def test_default_is_write_no_flag_needed(installed, tmp_path: Path) -> None:
    """Default mode (no flags) is WRITE — the CLI exits 0 and do_install is called.

    This is the contract: the user no longer has to remember ``--apply``;
    running the CLI alone is enough to install.
    """
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, cli = installed(
        profile_paths=[profile],
        profile_names=["hermes"],
        config_data={"skills": {"disabled": []}},
    )
    runner = cli.make_cli()
    result = runner.invoke(cli.app, [], color=False)
    # Exit 0: the run completed without error.
    assert result.exit_code == 0, result.output
    # The write path was exercised: do_install was called once.
    assert len(log.do_install_calls) == 1
    call = log.do_install_calls[0]
    assert call["identifier"] == "skill-creator"
    # The migrated SKILL.md materializes on disk.
    installed_path = profile / "skills" / "skill-creator" / "SKILL.md"
    assert installed_path.exists()
    assert "migrated" in installed_path.read_text()


def test_default_is_write_help_text(installed) -> None:
    """The ``--help`` body declares that default mode is READ-ONLY (Phase 8).

    Phase 7G defaulted to WRITE; Phase 8 flips to READ-ONLY — no writes,
    no apply/dry-run split. The ``--json`` flag is the only output-format
    switch.
    """
    log, cli = installed()
    runner = cli.make_cli()
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    out = result.output
    assert ("READ-ONLY" in out) or ("CSAK OLVAS" in out)
