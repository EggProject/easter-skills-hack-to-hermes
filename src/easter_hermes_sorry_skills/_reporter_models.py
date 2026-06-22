"""Dataclasses for the hermes-skill-creator reporter.

TDD tests reference ``easter_hermes_sorry_skills._reporter.SkillRow`` and
``ProfileSection``; ``_reporter.py`` re-exports them so existing imports
continue to work.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillRow:
    """A single skill row in the report. All values are already resolved.

    `use_count`, `view_count`, `patch_count` are Optional[int] — None means
    "n/a" (rendered as the string "n/a" in text, as `null` in JSON).
    `last_used_at`, `last_viewed_at`, `last_patched_at` are Optional[str] —
    None means "n/a".
    `description_full` is the full description (preserved in JSON).
    `description_display` is the truncated 60-char form for text rendering.
    `pct_of_cap` is rounded to one decimal place.
    """

    profile: str
    name: str
    description_full: str
    description_display: str
    tokens: int
    use_count: int | None
    view_count: int | None
    patch_count: int | None
    last_used_at: str | None
    last_viewed_at: str | None
    last_patched_at: str | None
    pct_of_cap: float
    # Sort key cached (used internally to break ties by name).
    _sort_name: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        # Stable secondary sort key: name asc.
        object.__setattr__(self, "_sort_name", self.name)


@dataclass(frozen=True)
class ProfileSection:
    """One profile's section inside a multi-profile JSON report."""

    profile_name: str
    rows: list[SkillRow]
    total_tokens: int
