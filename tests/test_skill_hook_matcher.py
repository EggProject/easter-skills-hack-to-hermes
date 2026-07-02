"""Tests for the WOW skill lexical matcher."""

from __future__ import annotations

from easter_hermes_sorry_skills._skill_hook_api import SkillMetadata
from easter_hermes_sorry_skills._skill_hook_matcher import match_skills


def _skill(name: str, description: str, category: str = "coding") -> SkillMetadata:
    """Build compact skill metadata for matcher tests."""
    return SkillMetadata(name=name, description=description, category=category)


def test_match_skills_prefers_explicit_name() -> None:
    """Explicit skill name is a strong match."""
    result = match_skills(
        "Please use skill-creator for this workflow",
        (_skill("skill-creator", "Create SKILL.md workflows"),),
        is_first_turn=False,
        top_k=3,
        min_score=2,
    )

    assert result[0].skill.name == "skill-creator"
    assert result[0].score >= 5
    assert "name" in result[0].reasons


def test_match_skills_uses_description_and_category() -> None:
    """Description and category tokens can match without explicit name."""
    result = match_skills(
        "Review this code change for regressions",
        (
            _skill("reviewer", "Review code changes for regressions", "quality"),
            _skill("docs", "Write markdown guides", "documentation"),
        ),
        is_first_turn=True,
        top_k=3,
        min_score=2,
    )

    assert [match.skill.name for match in result] == ["reviewer"]
    assert {"description", "first_turn"} <= set(result[0].reasons)


def test_match_skills_filters_trivial_prompt() -> None:
    """Very short prompts do not trigger weak matches."""
    result = match_skills(
        "review",
        (_skill("reviewer", "Review code changes"),),
        is_first_turn=False,
        top_k=3,
        min_score=2,
    )

    assert result == ()


def test_match_skills_filters_stopword_only_prompt() -> None:
    """Stopword-only prompt has no content tokens."""
    result = match_skills(
        "and the with",
        (_skill("anything", "and the with"),),
        is_first_turn=True,
        top_k=3,
        min_score=0,
    )

    assert result == ()


def test_match_skills_sorts_and_limits_deterministically() -> None:
    """Top-K and tie ordering are stable."""
    result = match_skills(
        "Generate docs workflow",
        (
            _skill("zeta", "Generate docs workflow", "docs"),
            _skill("alpha", "Generate docs workflow", "docs"),
            _skill("beta", "Generate docs workflow", "docs"),
        ),
        is_first_turn=False,
        top_k=2,
        min_score=2,
    )

    assert [match.skill.name for match in result] == ["alpha", "beta"]


def test_match_skills_handles_unicode_text() -> None:
    """Unicode input is tokenized safely."""
    result = match_skills(
        "Keszits fordítást dokumentáció alapján",
        (_skill("translator", "fordítást dokumentáció alapján", "docs"),),
        is_first_turn=False,
        top_k=1,
        min_score=2,
    )

    assert result[0].skill.name == "translator"


def test_match_skills_empty_prompt_returns_no_matches() -> None:
    """Empty prompts do not match."""
    assert match_skills("", (_skill("demo", "demo skill"),), is_first_turn=False, top_k=3, min_score=0) == ()
