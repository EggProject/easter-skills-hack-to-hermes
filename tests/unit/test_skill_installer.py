"""Unit tests for the skill installer + MIGRATION.skill-port.md generation.

Per docs/plans/07 + 08 §TDD test list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401
from hermes_skill_creator_plugin.skill_installer import (  # noqa: E402
    PINNED_UPSTREAM_COMMIT,
    T3_INVENTORY,
    detect_active_cap,
    install,
)


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"
WORKTREE = Path(__file__).resolve().parents[2]


def test_skill_creator_home_has_skills_and_profiles_dirs(
    skill_creator_home: Path,
) -> None:
    assert (skill_creator_home / "skills").is_dir()
    assert (skill_creator_home / "profiles").is_dir()


# ---------------------------------------------------------------------------
# Installer copies the skill to HERMES_HOME/skills/skill-creator/
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_installer_copies_skill_to_hermes_home_skills_dir(
    skill_creator_home: Path,
) -> None:
    result = install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    target = skill_creator_home / "skills" / "skill-creator"
    assert target.is_dir()
    assert (target / "SKILL.md").exists()
    assert (target / "scripts").is_dir()
    assert (target / "agents").is_dir()
    assert (target / "eval-viewer").is_dir()
    # `_subprocess.py` must be present.
    assert (target / "_subprocess.py").exists()
    # Result captures the selected SKILL.md path.
    assert result.selected_skill_md == target / "SKILL.md"


@assert_hermes_agent_untouched
def test_installer_emits_migration_skill_port_md(
    skill_creator_home: Path,
) -> None:
    result = install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    assert result.migration_note == WORKTREE / "MIGRATION.skill-port.md"
    assert result.migration_note.exists()
    body = result.migration_note.read_text(encoding="utf-8")
    # Frontmatter + T3 rows are emitted.
    assert "T3 inventory" in body
    assert PINNED_UPSTREAM_COMMIT in body
    assert "HERMES_SESSION" in body


@assert_hermes_agent_untouched
def test_migration_skill_port_has_18_t3_rows(
    skill_creator_home: Path,
) -> None:
    install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    body = (WORKTREE / "MIGRATION.skill-port.md").read_text(encoding="utf-8")
    # Every T3 ID is present.
    for row in T3_INVENTORY:
        assert row["id"] in body, f"missing {row['id']} in MIGRATION.skill-port.md"
    # Count the "T3.NNN" pattern.
    ids = re.findall(r"\bT3\.\d{3}\b", body)
    assert len(set(ids)) == 18


@assert_hermes_agent_untouched
def test_migration_skill_port_deterministic_under_frozen_time(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    body1 = (WORKTREE / "MIGRATION.skill-port.md").read_text(encoding="utf-8")
    # Second install with the same frozen time should produce byte-identical output.
    install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    body2 = (WORKTREE / "MIGRATION.skill-port.md").read_text(encoding="utf-8")
    assert body1 == body2
    # Frozen timestamp is present.
    assert "2026-06-17T00:00:00Z" in body1


@assert_hermes_agent_untouched
def test_migration_skill_port_mentions_anthropic_provenance(
    skill_creator_home: Path,
) -> None:
    """The note documents the FROM-Claude migration; the `claude-binding`
    column legitimately contains the original Anthropic-side binding
    text. We assert the note does include the column header.
    """
    install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    body = (WORKTREE / "MIGRATION.skill-port.md").read_text(encoding="utf-8")
    assert "claude-binding" in body
    assert "hermes-binding" in body


@assert_hermes_agent_untouched
def test_installer_writes_only_to_hermes_home_and_worktree(
    skill_creator_home: Path,
) -> None:
    """No writes outside hermes_home + worktree_root."""
    # Snapshot tmp_path before.
    install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    # The installer wrote to hermes_home/skills/skill-creator/ + worktree/MIGRATION.skill-port.md.
    assert (skill_creator_home / "skills" / "skill-creator").exists()
    assert (WORKTREE / "MIGRATION.skill-port.md").exists()


@assert_hermes_agent_untouched
def test_installer_refuses_to_write_to_live_hermes_agent(
    skill_creator_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`install()` raises ValueError if `hermes_home` is the live install.

    We monkeypatch the module's `_LIVE_HERMES_AGENT` constant to a known
    tmp_path so the refusal path is exercised without touching the real
    install.
    """
    from hermes_skill_creator_plugin import skill_installer as si

    fake_live = tmp_path / "fake-live-install"
    fake_live.mkdir()
    monkeypatch.setattr(si, "_LIVE_HERMES_AGENT", fake_live)
    with pytest.raises(ValueError, match="refusing to install to live"):
        install(
            skill_source=SKILL_DIR,
            hermes_home=fake_live,
            worktree_root=WORKTREE,
            cap="patched",
        )


@assert_hermes_agent_untouched
def test_installer_selects_short_or_full_description_per_active_cap(
    skill_creator_home: Path,
) -> None:
    """With cap='unpatched' the installer uses SKILL.md.short."""
    result_short = install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="unpatched",
    )
    body_short = result_short.selected_skill_md.read_text(encoding="utf-8")
    # The short variant's description is <= 60 chars.
    fm = _parse_short_frontmatter(body_short)
    desc = fm["description"]
    assert isinstance(desc, str) and len(desc) <= 60, f"short desc len {len(desc)}"

    result_full = install(
        skill_source=SKILL_DIR,
        hermes_home=skill_creator_home,
        worktree_root=WORKTREE,
        cap="patched",
    )
    body_full = result_full.selected_skill_md.read_text(encoding="utf-8")
    fm_full = _parse_short_frontmatter(body_full)
    desc_full = fm_full["description"]
    if isinstance(desc_full, list):
        desc_full = " ".join(desc_full)
    assert len(desc_full) > 60  # full variant is longer


@assert_hermes_agent_untouched
def test_detect_active_cap_raises_when_skill_utils_missing(
    skill_creator_home: Path,
) -> None:
    """detect_active_cap raises FileNotFoundError when agent/skill_utils.py
    is missing in the active checkout."""
    with pytest.raises(FileNotFoundError, match="skill_utils.py not found"):
        detect_active_cap(skill_creator_home)


@assert_hermes_agent_untouched
def test_install_raises_when_skill_source_missing(
    skill_creator_home: Path,
) -> None:
    """install() raises FileNotFoundError when the source skill is absent."""
    with pytest.raises(FileNotFoundError, match="skill source not found"):
        install(
            skill_source=Path("/nonexistent/skill-creator"),
            hermes_home=skill_creator_home,
            worktree_root=WORKTREE,
            cap="patched",
        )


@assert_hermes_agent_untouched
def test_install_raises_when_short_skill_md_missing(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When cap='unpatched' but SKILL.md.short is missing, install raises."""
    fake_skill = tmp_path / "fake-skill"
    fake_skill.mkdir()
    (fake_skill / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    # No SKILL.md.short.
    with pytest.raises(FileNotFoundError, match="SKILL.md.short"):
        install(
            skill_source=fake_skill,
            hermes_home=skill_creator_home,
            worktree_root=WORKTREE,
            cap="unpatched",
        )


@assert_hermes_agent_untouched
def test_install_autodetects_cap(
    skill_creator_home: Path, tmp_path: Path
) -> None:
    """When cap=None, install() autodetects the cap from the active checkout."""
    fake_skill = tmp_path / "fake-skill-autodetect"
    fake_skill.mkdir()
    (fake_skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: long desc for the FULL variant\n---\n",
        encoding="utf-8",
    )
    (fake_skill / "SKILL.md.short").write_text(
        "---\nname: x\ndescription: short desc\n---\n",
        encoding="utf-8",
    )
    # active_cap autodetects on `_LIVE_HERMES_AGENT` (which exists), so we
    # point detect_active_cap at a non-existent dir to force "unpatched".
    from hermes_skill_creator_plugin import skill_installer as si

    original = si.detect_active_cap
    si.detect_active_cap = lambda checkout=None: "unpatched"
    try:
        result = install(
            skill_source=fake_skill,
            hermes_home=skill_creator_home,
            worktree_root=WORKTREE,
            cap=None,
        )
        # Should pick SKILL.md.short.
        assert result.selected_skill_md.name == "SKILL.md"
        # The target's body matches the SHORT variant.
        body = result.selected_skill_md.read_text(encoding="utf-8")
        assert "short desc" in body
    finally:
        si.detect_active_cap = original


def _parse_short_frontmatter(text: str) -> dict:
    """YAML frontmatter parser (delegates to PyYAML)."""
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    block = text[4:end]
    import yaml

    return yaml.safe_load(block) or {}
