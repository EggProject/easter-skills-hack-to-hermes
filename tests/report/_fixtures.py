"""Shared pytest fixtures for tests/report/."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from easter_hermes_sorry_skills._reporter import SkillRow, make_row
from easter_hermes_sorry_skills._reporter_sort import _RowFields


def _make_skill_dir(root: Path, name: str, *, description: str = "x" * 10) -> Path:
    """Create a minimal skill directory with a SKILL.md frontmatter description."""
    skill = root / name
    skill.mkdir(parents=True, exist_ok=True)
    skill_md = skill / "SKILL.md"
    body = f"---\nname: {name}\ndescription: '{description}'\n---\n\n# {name}\n"
    skill_md.write_text(body, encoding="utf-8")
    return skill


def _write_profile(
    profile_root: Path,
    *,
    name: str,
    config: dict[str, Any] | None,
    skills: dict[str, str],
) -> Path:
    """Materialize a profile under `profile_root/name` with config + skills.

    Args:
        profile_root: parent of all profiles (e.g. hermes_home).
        name: profile name (e.g. 'hermes' or 'work').
        config: the `config.yaml` body (a dict). When None, no config.yaml.
        skills: mapping of skill name -> description.
    """
    p = profile_root / name
    p.mkdir(parents=True, exist_ok=True)
    if config is not None:
        import yaml

        (p / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    skills_dir = p / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for sname, desc in skills.items():
        _make_skill_dir(skills_dir, sname, description=desc)
    return p


@pytest.fixture
def make_profile() -> Callable[..., Path]:
    """Return the helper so tests can build their own profiles."""
    return _write_profile


def make_row_factory(
    *,
    profile: str = "hermes",
    name: str = "skill-a",
    description: str = "Use when you need a thing.",
    tokens: int = 10,
    use_count: int | None = 0,
    view_count: int | None = 0,
    patch_count: int | None = 0,
    last_used_at: str | None = None,
    last_viewed_at: str | None = None,
    last_patched_at: str | None = None,
) -> SkillRow:
    """Build a SkillRow for tests."""
    return make_row(
        _RowFields(
            profile=profile,
            name=name,
            description=description,
            tokens=tokens,
            use_count=use_count,
            view_count=view_count,
            patch_count=patch_count,
            last_used_at=last_used_at,
            last_viewed_at=last_viewed_at,
            last_patched_at=last_patched_at,
        ),
    )
