"""tests/report/test_enabled_detection.py

TDD: tests for the shared enabled-detection module
(hermes_skill_creator_plugin._enabled_detection) and its integration with
the reporter (cli_report.py).
"""

from __future__ import annotations

import ast
from pathlib import Path

from hermes_skill_creator_plugin import _enabled_detection, cli_report
from tests.report._fixtures import _write_profile

# --- _enabled_detection.get_enabled_skills ---


def test_get_enabled_skills_returns_frozenset(tmp_path: Path) -> None:
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={"a": "x" * 5})
    out = _enabled_detection.get_enabled_skills(profile)
    assert isinstance(out, frozenset)
    assert "a" in out


def test_get_enabled_skills_no_skills_returns_empty(tmp_path: Path) -> None:
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={})
    (profile / "skills").mkdir(parents=True, exist_ok=True)
    out = _enabled_detection.get_enabled_skills(profile)
    assert out == frozenset()


def test_get_enabled_skills_honors_config_toggle(tmp_path: Path) -> None:
    profile = _write_profile(
        tmp_path,
        name="hermes",
        config={"skills": {"disabled": ["foo"]}},
        skills={"foo": "x", "bar": "y"},
    )
    out = _enabled_detection.get_enabled_skills(profile)
    assert "foo" not in out
    assert "bar" in out


def test_get_enabled_skills_honors_platform_filter(tmp_path: Path) -> None:
    profile = _write_profile(
        tmp_path,
        name="hermes",
        config={"skills": {"disabled_if_platform": {"darwin": ["bar"]}}},
        skills={"bar": "y"},
    )
    out = _enabled_detection.get_enabled_skills(profile, platform="darwin")
    assert "bar" not in out
    out_linux = _enabled_detection.get_enabled_skills(profile, platform="linux")
    assert "bar" in out_linux


def test_get_enabled_skills_honors_conditional_exclusions(tmp_path: Path) -> None:
    profile_dir = _write_profile(tmp_path, name="hermes", config=None, skills={"baz": "z"})
    # Per-skill frontmatter disable_if: platform: [darwin]
    skill_dir = profile_dir / "skills" / "baz"
    (skill_dir / "SKILL.md").write_text(
        "---\nname: baz\ndescription: 'z'\ndisable_if:\n  platform: [darwin]\n---\n\n# baz\n",
        encoding="utf-8",
    )
    out = _enabled_detection.get_enabled_skills(profile_dir, platform="darwin")
    assert "baz" not in out
    out_linux = _enabled_detection.get_enabled_skills(profile_dir, platform="linux")
    assert "baz" in out_linux


def test_get_enabled_skills_honors_platforms_frontmatter(tmp_path: Path) -> None:
    profile_dir = _write_profile(tmp_path, name="hermes", config=None, skills={"qux": "q"})
    skill_dir = profile_dir / "skills" / "qux"
    (skill_dir / "SKILL.md").write_text(
        "---\nname: qux\ndescription: 'q'\nplatforms:\n" "  - disable_if_platform_present: [darwin]\n---\n\n# qux\n",
        encoding="utf-8",
    )
    out = _enabled_detection.get_enabled_skills(profile_dir, platform="darwin")
    assert "qux" not in out


def test_get_enabled_skills_skips_skill_md_missing_dir(tmp_path: Path) -> None:
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={})
    (profile / "skills" / "no-md").mkdir(parents=True, exist_ok=True)
    out = _enabled_detection.get_enabled_skills(profile)
    assert "no-md" not in out


def test_get_enabled_skills_no_config_defaults_to_all_enabled(tmp_path: Path) -> None:
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={"a": "x"})
    out = _enabled_detection.get_enabled_skills(profile)
    assert "a" in out


# --- cli_report integration: imports shared helper ---


def test_report_shares_enabled_detection_with_script_2() -> None:
    """Assert the reporter imports get_enabled_skills from the shared module."""
    src = cli_report.__file__
    assert src is not None
    text = Path(src).read_text(encoding="utf-8")
    tree = ast.parse(text)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.endswith("_enabled_detection"):
                for alias in node.names:
                    if alias.name == "get_enabled_skills":
                        found = True
    assert found, "cli_report.py must import get_enabled_skills at module top-level"


# --- resolve_profiles / run() integration ---


def test_report_default_profile_iteration(hermes_home: Path, monkeypatch) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile=None, sort="tokens", fmt="text", json_path=None)
    assert rc == 0


def test_report_named_profile_selects_one(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    _write_profile(hermes_home, name="work", config=None, skills={"b": "y"})
    rc = cli_report.run(profile="work", sort="tokens", fmt="text", json_path=None)
    assert rc == 0


def test_report_multi_profile_default(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    _write_profile(hermes_home, name="alpha", config=None, skills={"b": "y"})
    _write_profile(hermes_home, name="zeta", config=None, skills={"c": "z"})
    rc = cli_report.run(profile=None, sort="tokens", fmt="text", json_path=None)
    assert rc == 0


def test_report_no_skills_returns_empty(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={})
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 0
