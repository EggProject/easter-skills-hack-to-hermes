"""Lexical skill matcher for the WOW skill reminder hook."""

from __future__ import annotations

from dataclasses import dataclass

from easter_hermes_sorry_skills._skill_hook_matcher_rules import score_skill
from easter_hermes_sorry_skills._skill_hook_matcher_text import (
    content_tokens,
    normalized_text,
)
from easter_hermes_sorry_skills._skill_hook_models import SkillMetadata


@dataclass(frozen=True)
class SkillMatch:
    """One matched skill with score and debug reasons."""

    skill: SkillMetadata
    score: int
    reasons: tuple[str, ...]


def match_skills(
    user_message: str,
    skills: tuple[SkillMetadata, ...],
    *,
    is_first_turn: bool,
    top_k: int,
    min_score: int,
) -> tuple[SkillMatch, ...]:
    """Return top matching skills for a user message."""
    prompt_tokens = content_tokens(user_message)
    prompt_text = normalized_text(user_message)
    matches = _matched_skills(skills, prompt_tokens, prompt_text, is_first_turn, min_score)
    sorted_matches = sorted(matches, key=_sort_key)
    return tuple(sorted_matches[:top_k])


def _matched_skills(
    skills: tuple[SkillMetadata, ...],
    prompt_tokens: frozenset[str],
    prompt_text: str,
    is_first_turn: bool,
    min_score: int,
) -> tuple[SkillMatch, ...]:
    """Return matches that pass the configured minimum score."""
    matches: list[SkillMatch] = []
    for skill in skills:
        match = _score_skill(skill, prompt_tokens, prompt_text, is_first_turn)
        if match is not None and match.score >= min_score:
            matches.append(match)
    return tuple(matches)


def _sort_key(match: SkillMatch) -> tuple[int, str]:
    """Sort highest score first and then by stable skill name."""
    return -match.score, match.skill.name.lower()


def _score_skill(
    skill: SkillMetadata,
    prompt_tokens: frozenset[str],
    prompt_text: str,
    is_first_turn: bool,
) -> SkillMatch | None:
    """Score a single skill against prompt features."""
    scored = score_skill(skill, prompt_tokens, prompt_text, is_first_turn)
    if scored is None:
        return None
    score, reasons = scored
    return SkillMatch(skill=skill, score=score, reasons=reasons)
