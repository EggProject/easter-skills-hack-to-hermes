"""Tests for rendering skill hook context."""

from __future__ import annotations

from easter_hermes_sorry_skills._skill_hook_api import SkillMetadata
from easter_hermes_sorry_skills._skill_hook_config_consts import OUTPUT_INDEX, OUTPUT_NAMES, OUTPUT_SHORTLIST
from easter_hermes_sorry_skills._skill_hook_matcher import SkillMatch
from easter_hermes_sorry_skills._skill_hook_render import _truncate, render_skill_context


def _match(name: str, description: str) -> SkillMatch:
    """Build a renderable match."""
    return SkillMatch(
        skill=SkillMetadata(name=name, description=description, category="coding"),
        score=5,
        reasons=("name",),
    )


def test_render_skill_context_shortlist() -> None:
    """Shortlist renders name and bounded description."""
    context = render_skill_context((_match("review", "Review code changes"),), OUTPUT_SHORTLIST)

    assert context is not None
    assert "- review: Review code changes" in context
    assert "Use skill_view(name) only if" in context


def test_render_skill_context_names() -> None:
    """Names output omits descriptions."""
    context = render_skill_context(
        (
            _match("review", "Review code changes"),
            _match("docs", "Write docs"),
        ),
        OUTPUT_NAMES,
    )

    assert context is not None
    assert "- review, docs" in context
    assert "Review code changes" not in context


def test_render_skill_context_index_uses_longer_description() -> None:
    """Index output preserves longer Hermes description."""
    description = "x" * 200
    context = render_skill_context((_match("long", description),), OUTPUT_INDEX)

    assert context is not None
    assert description in context


def test_render_skill_context_empty_matches_returns_none() -> None:
    """No matches produce no context."""
    assert render_skill_context((), OUTPUT_SHORTLIST) is None


def test_render_skill_context_truncates_shortlist_description() -> None:
    """Shortlist descriptions are bounded."""
    context = render_skill_context((_match("long", "x" * 200),), OUTPUT_SHORTLIST)

    assert context is not None
    assert "..." in context
    assert "x" * 180 not in context


def test_render_skill_context_handles_empty_description() -> None:
    """Empty descriptions render as name-only lines."""
    context = render_skill_context((_match("plain", ""),), OUTPUT_SHORTLIST)

    assert context is not None
    assert "- plain\n" in context


def test_truncate_handles_tiny_limit() -> None:
    """Tiny truncate limits clip without ellipsis."""
    assert _truncate("abcdef", 2) == "ab"
