"""Render matched skills into a compact hook context."""

from __future__ import annotations

from easter_hermes_sorry_skills._skill_hook_config_consts import OUTPUT_INDEX, OUTPUT_NAMES
from easter_hermes_sorry_skills._skill_hook_matcher import SkillMatch

_SHORT_DESCRIPTION_LIMIT = 140
_INDEX_DESCRIPTION_LIMIT = 1024
_FOOTER = "Use skill_view(name) only if the current task actually matches."
_LOADED_FOOTER = "Follow already loaded skill instructions; call skill_view(name) again only for linked files."


def render_skill_context(
    matches: tuple[SkillMatch, ...],
    output: str,
    *,
    loaded_matches: tuple[SkillMatch, ...] = (),
) -> str | None:
    """Render matched skills for pre_llm_call context injection."""
    if not matches and not loaded_matches:
        return None
    sections: list[str] = []
    body = ""
    if matches:
        if output == OUTPUT_NAMES:
            body = _render_names(matches)
        elif output == OUTPUT_INDEX:
            body = _render_with_descriptions(matches, _INDEX_DESCRIPTION_LIMIT)
        else:
            body = _render_with_descriptions(matches, _SHORT_DESCRIPTION_LIMIT)
    if body:
        sections.append("\n".join(("Relevant Hermes skills to consider:", body, "", _FOOTER)))
    if loaded_matches:
        loaded_body = _render_names(loaded_matches)
        sections.append(
            "\n".join(
                (
                    "Already loaded relevant Hermes skills:",
                    loaded_body,
                    "",
                    _LOADED_FOOTER,
                ),
            ),
        )
    return "\n\n".join(sections)


def _render_names(matches: tuple[SkillMatch, ...]) -> str:
    """Render names-only output."""
    return "".join(("- ", _joined_names(matches)))


def _joined_names(matches: tuple[SkillMatch, ...]) -> str:
    """Return comma-separated skill names."""
    return ", ".join(match.skill.name for match in matches)


def _render_with_descriptions(matches: tuple[SkillMatch, ...], limit: int) -> str:
    """Render one skill per line with bounded descriptions."""
    return "\n".join(_render_skill_line(match, limit) for match in matches)


def _render_skill_line(match: SkillMatch, limit: int) -> str:
    """Render one matched skill line."""
    description = _truncate(_one_line(match.skill.description), limit)
    if not description:
        return "".join(("- ", match.skill.name))
    return "".join(("- ", match.skill.name, ": ", description))


def _one_line(text: str) -> str:
    """Collapse text to one line."""
    return " ".join(text.split())


def _truncate(text: str, limit: int) -> str:
    """Return text clipped to *limit* chars with ellipsis."""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return "".join((text[: limit - 3].rstrip(), "..."))
