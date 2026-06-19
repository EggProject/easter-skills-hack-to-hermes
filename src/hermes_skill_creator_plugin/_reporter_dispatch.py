"""Column-dispatch table for text-format rendering.

Extracted from ``_reporter_format`` to keep that module under 7 members
(WPS202). The dispatch maps a column name to a getter that pulls the
display string from a ``SkillRow``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hermes_skill_creator_plugin._reporter_format import (
    COL_DESCRIPTION,
    COL_NAME,
    COL_PCT_OF_CAP,
    COL_PROFILE,
    COL_TOKENS,
)
from hermes_skill_creator_plugin._reporter_models import SkillRow


def _get_profile(row: SkillRow) -> str:
    """Return the profile name of ``row``."""
    return row.profile


def _get_name(row: SkillRow) -> str:
    """Return the skill name of ``row``."""
    return row.name


def _get_description(row: SkillRow) -> str:
    """Return the display-truncated description of ``row``."""
    return row.description_display


def _get_tokens(row: SkillRow) -> str:
    """Return the token count of ``row`` as a string."""
    return str(row.tokens)


def _get_pct_of_cap(row: SkillRow) -> str:
    """Return the ``pct_of_cap`` of ``row`` formatted to 1 decimal."""
    return f"{row.pct_of_cap:.1f}"


VALUE_DISPATCH: dict[str, Callable[[SkillRow], str]] = {
    COL_PROFILE: _get_profile,
    COL_NAME: _get_name,
    COL_DESCRIPTION: _get_description,
    COL_TOKENS: _get_tokens,
    COL_PCT_OF_CAP: _get_pct_of_cap,
}