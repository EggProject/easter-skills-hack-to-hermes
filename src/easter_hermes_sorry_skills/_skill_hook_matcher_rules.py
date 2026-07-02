"""Scoring rules for the WOW skill reminder matcher."""

from __future__ import annotations

from easter_hermes_sorry_skills._skill_hook_matcher_text import content_tokens, normalized_text
from easter_hermes_sorry_skills._skill_hook_models import SkillMetadata

_TRIVIAL_TOKEN_LIMIT = 2
_NAME_SCORE = 5
_DESCRIPTION_SCORE = 3
_CATEGORY_SCORE = 2
_FIRST_TURN_SCORE = 1
_TRIVIAL_PENALTY = 3
_SKILL_HINT_WORDS = frozenset(
    (
        "agent",
        "config",
        "debug",
        "document",
        "eval",
        "generate",
        "hook",
        "implement",
        "migrate",
        "plugin",
        "prompt",
        "review",
        "skill",
        "test",
        "tool",
        "workflow",
    ),
)


def score_skill(
    skill: SkillMetadata,
    prompt_tokens: frozenset[str],
    prompt_text: str,
    is_first_turn: bool,
) -> tuple[int, tuple[str, ...]] | None:
    """Return score and reasons for one skill."""
    if not prompt_tokens:
        return None
    reasons = _match_reasons(skill, prompt_tokens, prompt_text, is_first_turn)
    score = _score_reasons(reasons)
    if score <= 0 or not reasons:
        return None
    return score, reasons


def _match_reasons(
    skill: SkillMetadata,
    prompt_tokens: frozenset[str],
    prompt_text: str,
    is_first_turn: bool,
) -> tuple[str, ...]:
    """Return the triggered score reasons for one skill."""
    reasons: tuple[str, ...] = ()
    if _matches_name(skill, prompt_text):
        reasons += ("name",)
    if _matches_description(skill, prompt_tokens):
        reasons += ("description",)
    if _matches_category(skill, prompt_tokens):
        reasons += ("category",)
    if is_first_turn and prompt_tokens & _SKILL_HINT_WORDS:
        reasons += ("first_turn",)
    if len(prompt_tokens) <= _TRIVIAL_TOKEN_LIMIT:
        reasons += ("trivial",)
    return reasons


def _matches_name(skill: SkillMetadata, prompt_text: str) -> bool:
    """Return whether the prompt explicitly contains the skill name."""
    name_text = normalized_text(skill.name)
    return bool(name_text and name_text in prompt_text)


def _matches_description(skill: SkillMetadata, prompt_tokens: frozenset[str]) -> bool:
    """Return whether the prompt overlaps enough with the description."""
    return len(prompt_tokens & content_tokens(skill.description)) >= 2


def _matches_category(skill: SkillMetadata, prompt_tokens: frozenset[str]) -> bool:
    """Return whether the prompt overlaps with category or name tokens."""
    skill_tokens = content_tokens(skill.category) | content_tokens(skill.name)
    return bool(prompt_tokens & skill_tokens)


def _score_reasons(reasons: tuple[str, ...]) -> int:
    """Convert triggered reasons into a score."""
    score = 0
    if "name" in reasons:
        score += _NAME_SCORE
    if "description" in reasons:
        score += _DESCRIPTION_SCORE
    if "category" in reasons:
        score += _CATEGORY_SCORE
    if "first_turn" in reasons:
        score += _FIRST_TURN_SCORE
    if "trivial" in reasons:
        score -= _TRIVIAL_PENALTY
    return score
