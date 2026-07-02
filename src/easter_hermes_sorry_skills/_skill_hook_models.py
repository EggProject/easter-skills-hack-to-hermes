"""Shared models for WOW skill hook modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillMetadata:
    """Minimal skill metadata used by the hook matcher."""

    name: str
    description: str
    category: str
