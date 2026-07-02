"""pre_llm_call orchestration for adaptive Hermes skill reminders."""

from __future__ import annotations

import logging
from typing import Any

from easter_hermes_sorry_skills._skill_hook_api import load_enabled_skills
from easter_hermes_sorry_skills._skill_hook_config import load_skill_hook_config
from easter_hermes_sorry_skills._skill_hook_config_consts import MODE_ADAPTIVE, MODE_FIRST, MODE_OFF
from easter_hermes_sorry_skills._skill_hook_matcher import SkillMatch, match_skills
from easter_hermes_sorry_skills._skill_hook_render import render_skill_context

logger = logging.getLogger(__name__)


def pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    """Hermes ``pre_llm_call`` callback.

    Fail-open by design: a broken hook must not break the agent turn.
    """
    try:
        context = build_pre_llm_context(kwargs)
    except Exception as exc:
        logger.warning("WOW skill hook skipped after error: %s", exc)
        return None
    if not context:
        return None
    return {"context": context}


def build_pre_llm_context(payload: dict[str, Any]) -> str | None:
    """Build optional context for a Hermes pre_llm_call payload."""
    config = load_skill_hook_config()
    _apply_log_level(config.log_level)
    if not _should_run(config.enabled, config.mode, payload.get("is_first_turn")):
        logger.debug("skill_hook: skipped reason=mode mode=%s", config.mode)
        return None
    user_message = payload.get("user_message")
    if not isinstance(user_message, str) or not user_message.strip():
        logger.debug("skill_hook: skipped reason=empty_user_message")
        return None
    skills = load_enabled_skills()
    matches = match_skills(
        user_message,
        skills,
        is_first_turn=bool(payload.get("is_first_turn")),
        top_k=config.top_k,
        min_score=config.min_score,
    )
    context = render_skill_context(matches, config.output)
    _log_decision(config.mode, config.output, len(skills), matches, bool(context))
    return context


def _should_run(enabled: bool, mode: str, is_first_turn: object) -> bool:
    """Return whether hook logic should run for this turn."""
    if not enabled or mode == MODE_OFF:
        return False
    if mode == MODE_FIRST:
        return bool(is_first_turn)
    return mode == MODE_ADAPTIVE


def _apply_log_level(log_level: str) -> None:
    """Apply configured module log level."""
    logger.setLevel(getattr(logging, log_level, logging.INFO))


def _log_decision(
    mode: str,
    output: str,
    skill_count: int,
    matches: tuple[SkillMatch, ...],
    injected: bool,
) -> None:
    """Emit bounded debug details without logging the user prompt."""
    logger.debug(
        "skill_hook: mode=%s output=%s skills=%d matched=%d injected=%d",
        mode,
        output,
        skill_count,
        len(matches),
        int(injected),
    )
    for match in matches:
        logger.debug(
            "skill_hook: matched %s score=%d reason=%s",
            match.skill.name,
            match.score,
            "+".join(match.reasons),
        )
