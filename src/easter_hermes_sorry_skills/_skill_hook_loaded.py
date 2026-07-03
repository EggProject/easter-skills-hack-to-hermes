"""Loaded-skill handling for WOW skill hook matches."""

from __future__ import annotations

from easter_hermes_sorry_skills._skill_hook_history import loaded_skill_names_from_history
from easter_hermes_sorry_skills._skill_hook_matcher import SkillMatch
from easter_hermes_sorry_skills._skill_hook_render import render_skill_context


def render_matches_with_loaded_state(
    matches: tuple[SkillMatch, ...],
    output: str,
    conversation_history: object,
) -> tuple[str | None, int]:
    """Render matches after separating already loaded skills."""
    loaded_skill_names = loaded_skill_names_from_history(conversation_history)
    new_matches, loaded_matches = split_loaded_matches(matches, loaded_skill_names)
    context = render_skill_context(new_matches, output, loaded_matches=loaded_matches)
    return context, len(loaded_matches)


def split_loaded_matches(
    matches: tuple[SkillMatch, ...],
    loaded_skill_names: frozenset[str],
) -> tuple[tuple[SkillMatch, ...], tuple[SkillMatch, ...]]:
    """Split matches into not-yet-loaded and already-loaded skills."""
    loaded_lookup = frozenset(name.casefold() for name in loaded_skill_names)
    new_matches: list[SkillMatch] = []
    loaded_matches: list[SkillMatch] = []
    for match in matches:
        target = loaded_matches if match.skill.name.casefold() in loaded_lookup else new_matches
        target.append(match)
    return tuple(new_matches), tuple(loaded_matches)
