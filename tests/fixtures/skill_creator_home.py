"""tests/fixtures/skill_creator_home.py — hermes_home with skills/ + profiles/ subdirs.

Used by E-skill's installer tests so the installer can write to a tmp_path
HERMES_HOME without ever touching the live install.

TDD test cases for this module:
  test_skill_creator_home_has_skills_and_profiles_dirs
  test_skill_creator_home_redirects_hermes_home_env
  test_skill_creator_home_is_inside_tmp_path
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

__all__ = ["skill_creator_home"]


@pytest.fixture
def skill_creator_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HERMES_HOME rooted inside tmp_path with skills/ and profiles/ subdirs."""
    home = tmp_path / "hermes-skill-creator-home"
    (home / "skills").mkdir(parents=True)
    (home / "profiles").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home
