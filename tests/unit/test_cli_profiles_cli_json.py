"""Unit tests for the ``--json`` flag on the ``cli_profiles`` CLI (Phase D).

TDD list:
- ``test_json_flag_emits_parseable_json`` — ``--json`` prints valid JSON to stdout.
- ``test_json_payload_top_level_keys`` — the JSON dump has the documented keys.
- ``test_json_payload_profile_block_shape`` — each profile block has the
  documented keys (``name``, ``skill_count``, ``token_total``,
  ``token_source``, ``enabled_skills``).
- ``test_json_without_flag_prints_table`` — without ``--json`` the CLI
  prints a rich table (no JSON braces on stdout).
- ``test_json_warnings_propagated`` — the ``warnings`` list flows into
  the top-level payload.

The CLI never writes — ``save_disabled_skills``, ``do_install``,
``clear_skills_system_prompt_cache``, and ``save_config`` are NOT
invoked under either the ``--json`` or the default code path.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from click.testing import CliRunner


def _extract_json(stdout: str) -> dict:
    """Pull the JSON document from ``stdout``.

    The click runner may emit leading ``[verbose]`` / bilingual lines
    before the JSON dump; this helper finds the first ``{`` and parses
    the remainder as the JSON payload.
    """
    start = stdout.find("{")
    assert start != -1, f"no JSON braces in stdout: {stdout!r}"
    return json.loads(stdout[start:])


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


def _install_cli_json_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile_paths: list[Path],
    profile_names: list[str],
    skill_to_description: dict[str, str] | None = None,
) -> _CallLog:
    """Install fakes for the ``--json`` CLI tests."""
    log = _CallLog()

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
def cli_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Yield ``(log, runner, app)`` for the click CLI surface."""

    def _setup(
        *,
        profile_paths: list[Path] | None = None,
        profile_names: list[str] | None = None,
        skill_to_description: dict[str, str] | None = None,
    ) -> tuple[_CallLog, CliRunner, object]:
        if profile_paths is None:
            profile_paths = [tmp_path / "default"]
        if profile_names is None:
            profile_names = ["hermes"]
        for p in profile_paths:
            # Create the parent profile dir, then the skills/ subdir.
            p.mkdir(parents=True, exist_ok=True)
            (p / "skills").mkdir(parents=True, exist_ok=True)
        log = _install_cli_json_fakes(
            monkeypatch,
            profile_paths=profile_paths,
            profile_names=profile_names,
            skill_to_description=skill_to_description,
        )
        # Force a fresh import of cli_profiles + its helpers so the
        # fakes patched above are wired in.
        import importlib

        for module_name in list(sys.modules):
            if (
                module_name.startswith("easter_hermes_sorry_skills._cli_profiles")
                or module_name == "easter_hermes_sorry_skills._enabled_detection"
                or module_name == "easter_hermes_sorry_skills._cli_report_helpers_paths"
            ):
                del sys.modules[module_name]
        if "easter_hermes_sorry_skills.cli_profiles" in sys.modules:
            del sys.modules["easter_hermes_sorry_skills.cli_profiles"]
        cli = importlib.import_module("easter_hermes_sorry_skills.cli_profiles")
        return log, CliRunner(), cli.app

    return _setup


# ---------------------------------------------------------------------------
# TDD list — --json flag structure.
# ---------------------------------------------------------------------------


def test_json_flag_emits_parseable_json(cli_runner, tmp_path: Path) -> None:
    """``--json`` prints a valid JSON document on stdout."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    (profile / "skills" / "alpha").mkdir()
    (profile / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: x\n---\n")

    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, ["--json"], color=False)
    assert result.exit_code == 0, result.output
    # Stdout contains parseable JSON.
    parsed = _extract_json(result.output)
    assert isinstance(parsed, dict)


def test_json_payload_top_level_keys(cli_runner, tmp_path: Path) -> None:
    """The JSON dump has the documented top-level keys."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, ["--json"], color=False)
    assert result.exit_code == 0, result.output
    parsed = _extract_json(result.output)
    assert parsed["tool"] == "easter-hermes-sorry-skills-profiles"
    assert parsed["version"] == "0.1.0"
    assert "generated_at" in parsed
    assert parsed["profile_count"] == 1
    assert "profiles" in parsed
    assert "warnings" in parsed


def test_json_payload_profile_block_shape(cli_runner, tmp_path: Path) -> None:
    """Each profile block carries ``name``, ``skill_count``, ``token_total``,
    ``token_source``, ``enabled_skills``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    for name in ("alpha", "beta"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")

    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
        skill_to_description={"alpha": "first", "beta": "second"},
    )
    result = runner.invoke(app, ["--json"], color=False)
    assert result.exit_code == 0, result.output
    parsed = _extract_json(result.output)
    block = parsed["profiles"][0]
    assert block["name"] == "hermes"
    # The pipeline's _summarize_rows populates skill_count + token_total +
    # token_source; enabled_skills is a (possibly empty) list rendered by
    # the table renderer from summary["enabled_skills"].
    assert block["skill_count"] == 2
    assert block["token_total"] >= 0
    assert block["token_source"] in {"tokenizer", "chars_div_4"}
    enabled = block["enabled_skills"]
    assert isinstance(enabled, list)


# ---------------------------------------------------------------------------
# TDD list — default (no --json) prints a table.
# ---------------------------------------------------------------------------


def test_json_without_flag_prints_table(cli_runner, tmp_path: Path) -> None:
    """Without ``--json`` the CLI emits a rich table (NOT a JSON document)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, [], color=False)
    assert result.exit_code == 0, result.output
    # No JSON braces on stdout (the table renderer doesn't emit them).
    assert "{" not in result.output or "tool" not in result.output
    # The bilingual message key surfaces in the output (or its translation).
    assert "[en]" in result.output
    assert "[hu]" in result.output


# ---------------------------------------------------------------------------
# TDD list — JSON warnings propagation.
# ---------------------------------------------------------------------------


def test_json_warnings_propagated(cli_runner, tmp_path: Path) -> None:
    """The ``warnings`` list (currently always empty in READ-ONLY mode) is
    present at the top level of the JSON payload as a list."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, ["--json"], color=False)
    assert result.exit_code == 0, result.output
    parsed = _extract_json(result.output)
    assert isinstance(parsed["warnings"], list)


# ---------------------------------------------------------------------------
# TDD list — READ-ONLY invariant under --json.
# ---------------------------------------------------------------------------


def test_json_flag_does_not_call_write_paths(cli_runner, tmp_path: Path) -> None:
    """``--json`` never invokes ``save_disabled_skills`` / ``do_install`` /
    ``clear_skills_system_prompt_cache`` / ``save_config``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, ["--json"], color=False)
    assert result.exit_code == 0, result.output
    assert log.save_disabled_calls == []
    assert log.do_install_calls == []
    assert log.clear_cache_calls == []
    assert log.save_config_calls == []


def test_json_with_profile_filter(cli_runner, tmp_path: Path) -> None:
    """``--json --profile NAME`` restricts the JSON dump to the named profile."""
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    for p in (p1, p2):
        (p / "skills").mkdir(parents=True)

    log, runner, app = cli_runner(
        profile_paths=[p1, p2],
        profile_names=["alpha", "beta"],
    )
    result = runner.invoke(app, ["--json", "--profile", "alpha"], color=False)
    assert result.exit_code == 0, result.output
    parsed = _extract_json(result.output)
    assert parsed["profile_count"] == 1
    assert [block["name"] for block in parsed["profiles"]] == ["alpha"]


def test_json_with_verbose_keeps_diagnostics_on_stderr(cli_runner, tmp_path: Path) -> None:
    """``--json --verbose`` keeps the ``[verbose]`` lines on stderr while
    the JSON dump still goes to stdout."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    log, runner, app = cli_runner(
        profile_paths=[profile],
        profile_names=["hermes"],
    )
    result = runner.invoke(app, ["--json", "--verbose"], color=False)
    assert result.exit_code == 0, result.output
    parsed = _extract_json(result.output)
    assert isinstance(parsed, dict)
    assert "[verbose]" in (result.stderr or "")
