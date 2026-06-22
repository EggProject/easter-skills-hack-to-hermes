"""Column-dispatch table for text-format rendering.

Extracted from ``_reporter_format`` to keep that module under 7 members
(WPS202). The dispatch maps a column name to a getter that pulls the
display string from a ``SkillRow``.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType

# Import column-name constants directly from the consts module to avoid
# a circular import: the ``_reporter_format`` HUB re-exports from
# ``_reporter_format_text_value`` which in turn imports this dispatch
# table for ``VALUE_DISPATCH``.
from easter_hermes_sorry_skills._reporter_format_consts import (
    COL_DESCRIPTION,
    COL_NAME,
    COL_PCT_OF_CAP,
    COL_PROFILE,
    COL_TOKENS,
)
from easter_hermes_sorry_skills._reporter_models import SkillRow


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


VALUE_DISPATCH: MappingProxyType[str, Callable[[SkillRow], str]] = MappingProxyType(
    {
        COL_PROFILE: _get_profile,
        COL_NAME: _get_name,
        COL_DESCRIPTION: _get_description,
        COL_TOKENS: _get_tokens,
        COL_PCT_OF_CAP: _get_pct_of_cap,
    },
)
