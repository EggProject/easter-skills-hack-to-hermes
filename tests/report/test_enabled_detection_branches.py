"""Branch-coverage tests for _enabled_detection internal helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from easter_hermes_sorry_skills import _enabled_detection
from easter_hermes_sorry_skills import _enabled_detection_parse as _ed_parse
from tests.report._fixtures import _write_profile


def test_parse_frontmatter_fallback_when_module_missing(tmp_path: Path) -> None:
    """When frontmatter.load raises, fall back to the manual split."""
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: foo\ndescription: x\n---\n# body\n", encoding="utf-8")

    def _boom(*a, **kw):
        raise ImportError("simulated")

    with patch.object(_ed_parse.frontmatter, "load", _boom):
        meta = _ed_parse.parse_frontmatter(p)
    assert meta.get("name") == "foo"


def test_parse_frontmatter_no_frontmatter_block(tmp_path: Path) -> None:
    p = tmp_path / "SKILL.md"
    p.write_text("# body\n", encoding="utf-8")
    assert _ed_parse.parse_frontmatter(p) == {}


def test_parse_frontmatter_unterminated_block(tmp_path: Path) -> None:
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: foo\nno terminator", encoding="utf-8")
    assert _ed_parse.parse_frontmatter(p) == {}


def test_parse_frontmatter_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "SKILL.md"
    p.write_text("---\n: : : bad\n---\n", encoding="utf-8")
    assert _ed_parse.parse_frontmatter(p) == {}


def test_parse_frontmatter_yaml_returns_non_dict(tmp_path: Path) -> None:
    p = tmp_path / "SKILL.md"
    p.write_text("---\n[1, 2, 3]\n---\n", encoding="utf-8")
    assert _ed_parse.parse_frontmatter(p) == {}


def test_load_config_no_file(tmp_path: Path) -> None:
    assert _enabled_detection._load_config(tmp_path) == {}


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(": : : bad", encoding="utf-8")
    assert _enabled_detection._load_config(tmp_path) == {}


def test_disabled_set_non_list_disabled(tmp_path: Path) -> None:
    s = _enabled_detection._disabled_set({"skills": {"disabled": "not-a-list"}}, platform=None)
    assert s == set()


def test_disabled_set_non_dict_skills_section(tmp_path: Path) -> None:
    s = _enabled_detection._disabled_set({"skills": "not-a-dict"}, platform=None)
    assert s == set()


def test_disabled_set_platform_filter_when_platform_is_none(tmp_path: Path) -> None:
    s = _enabled_detection._disabled_set({"skills": {"disabled_if_platform": {"darwin": ["x"]}}}, platform=None)
    assert "x" not in s


def test_disabled_set_platform_filter_dict_not_dict(tmp_path: Path) -> None:
    s = _enabled_detection._disabled_set({"skills": {"disabled_if_platform": "not-dict"}}, platform="darwin")
    assert s == set()


def test_disabled_set_platform_filter_empty_platform_list(tmp_path: Path) -> None:
    s = _enabled_detection._disabled_set({"skills": {"disabled_if_platform": {"darwin": []}}}, platform="darwin")
    assert s == set()


def test_platform_blocked_platform_none_returns_false() -> None:
    assert _enabled_detection._platform_blocked({"platforms": []}, platform=None) is False


def test_platform_blocked_no_platforms_key() -> None:
    assert _enabled_detection._platform_blocked({}, platform="darwin") is False


def test_platform_blocked_platforms_not_list() -> None:
    assert _enabled_detection._platform_blocked({"platforms": "x"}, platform="darwin") is False


def test_platform_blocked_entry_not_dict() -> None:
    assert _enabled_detection._platform_blocked({"platforms": ["string-entry"]}, platform="darwin") is False


def test_platform_blocked_blocked_field_not_list() -> None:
    assert (
        _enabled_detection._platform_blocked(
            {"platforms": [{"disable_if_platform_present": "not-a-list"}]},
            platform="darwin",
        )
        is False
    )


def test_conditional_excluded_rule_not_dict() -> None:
    assert _enabled_detection._conditional_excluded({"disable_if": "string"}, platform="darwin") is False


def test_conditional_excluded_platform_none() -> None:
    assert _enabled_detection._conditional_excluded({"disable_if": {"platform": ["darwin"]}}, platform=None) is False


def test_conditional_excluded_platforms_not_list() -> None:
    assert _enabled_detection._conditional_excluded({"disable_if": {"platform": "darwin"}}, platform="darwin") is False


def test_conditional_excluded_no_match() -> None:
    assert _enabled_detection._conditional_excluded({"disable_if": {"platform": ["linux"]}}, platform="darwin") is False


def test_conditional_excluded_match() -> None:
    assert _enabled_detection._conditional_excluded({"disable_if": {"platform": ["darwin"]}}, platform="darwin") is True


def test_get_enabled_skills_skills_dir_missing(tmp_path: Path) -> None:
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={})
    # Remove skills/ dir entirely.
    import shutil

    shutil.rmtree(profile / "skills")
    assert _enabled_detection.get_enabled_skills(profile) == frozenset()


def test_get_enabled_skills_skill_name_from_frontmatter(tmp_path: Path) -> None:
    """Skill whose frontmatter name differs from the directory name."""
    profile = _write_profile(tmp_path, name="hermes", config=None, skills={})
    (profile / "skills" / "alt-name").mkdir(parents=True)
    (profile / "skills" / "alt-name" / "SKILL.md").write_text(
        "---\nname: real-name\ndescription: x\n---\n", encoding="utf-8"
    )
    out = _enabled_detection.get_enabled_skills(profile)
    assert "real-name" in out
    assert "alt-name" not in out
