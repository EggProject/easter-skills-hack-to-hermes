"""Runtime language picker: pick(lang) -> messages_en | messages_hu module.

Single-source of truth for which language module to use at emission time.
The CLI --lang option flows through this picker; the rest of the
codebase should never import messages_en / messages_hu directly when
emitting user-facing messages.
"""

from __future__ import annotations

from typing import Any

from easter_hermes_sorry_skills.i18n import messages_en, messages_hu

# Public type alias: ``Messages`` is the structural type of the i18n
# modules returned by :func:`pick`. Declared as ``Any`` so callers can
# pass through to attribute access (DRY_RUN_PLAN_HEADER, etc.) without
# mypy/wemake object-attribute complaints.
Messages = Any


def pick(lang: str = "en") -> Messages:
    """Return the messages module for the given language code.

    Default is "en" (English) when lang is unknown or empty.
    Returns messages_hu for lang == "hu", otherwise messages_en.
    """
    if lang == "hu":
        return messages_hu
    return messages_en
