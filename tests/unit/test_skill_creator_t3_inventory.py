"""Unit tests for the T3 per-binding inventory + active-cap detection.

Per docs/plans/07 §TDD test list (T3 inventory: 18 rows, one test per row;
AC-4.10: detect_active_cap for patched vs unpatched Hermes checkout).

The helpers (_read, _strip_fences, _parse_frontmatter) are duplicated here
(rather than imported from test_skill_creator_frontmatter) so each file
remains self-contained and the per-file 500-line cap (see
plans/10-toolchain-and-conventions.md D1 + tools/check_line_count.py) is
respected.
"""

from __future__ import annotations

from pathlib import Path

from hermes_skill_creator_plugin import assert_hermes_agent_untouched
from hermes_skill_creator_plugin.skill_installer import (
    PINNED_UPSTREAM_COMMIT,
    T3_INVENTORY,
    detect_active_cap,
)

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T3 inventory: 18 rows, one test per row
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_t3_inventory_has_exactly_18_rows(skill_creator_home: Path) -> None:
    assert len(T3_INVENTORY) == 18


@assert_hermes_agent_untouched
def test_t3_inventory_ids_are_unique(skill_creator_home: Path) -> None:
    ids = [r["id"] for r in T3_INVENTORY]
    assert len(set(ids)) == 18


@assert_hermes_agent_untouched
def test_pinned_upstream_commit_is_set(skill_creator_home: Path) -> None:
    assert PINNED_UPSTREAM_COMMIT == "2a40fd2e7c52207aa903bd33fc4c65716126966e"


# Per-binding tests (T3.001..T3.018)
# T3.001: improve_description main entry: claude -p -> hermes -p
@assert_hermes_agent_untouched
def test_T3_001_run_eval_invokes_hermes_not_claude(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "improve_description.py")
    assert "claude -p" not in text
    assert "hermes -p" in text


# T3.002: env-strip pop('CLAUDECODE') -> hermes_subprocess_env()
@assert_hermes_agent_untouched
def test_T3_002_uses_hermes_subprocess_env(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "improve_description.py")
    assert "os.environ.pop" not in text
    assert "hermes_subprocess_env" in text


# T3.003: claude -p --output-format stream-json -> hermes -p ...
@assert_hermes_agent_untouched
def test_T3_003_run_eval_uses_hermes_stream_json(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_eval.py")
    assert "claude -p" not in text
    assert "hermes -p" in text
    assert "stream-json" in text


# T3.004: run_eval env-strip uses helper
@assert_hermes_agent_untouched
def test_T3_004_run_eval_uses_helper(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_eval.py")
    assert "os.environ.pop" not in text
    assert "hermes_subprocess_env" in text


# T3.005: writes to ~/.hermes/skills/<cat>/<target>/SKILL.md (not .claude/commands)
@assert_hermes_agent_untouched
def test_T3_005_run_eval_writes_to_hermes_skills(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_eval.py")
    assert ".claude/commands" not in text
    assert "skills" in text
    assert "SKILL.md" in text


# T3.006: --model claude-... -> --model hermes-...
@assert_hermes_agent_untouched
def test_T3_006_run_eval_uses_hermes_model(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_eval.py")
    assert "claude-" not in text
    # model may be omitted (session config); if present, hermes prefix is OK
    assert "hermes" in text or "model" in text


# T3.007: SKILL.md has no claude.ai URL
@assert_hermes_agent_untouched
def test_T3_007_skill_md_no_claude_ai_url(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    assert "claude.ai" not in text


# T3.008: SKILL.md has no Cowork-specific section
@assert_hermes_agent_untouched
def test_T3_008_skill_md_no_cowork_section(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    assert "Cowork-Specific Instructions" not in text
    assert "Cowork" not in text


# T3.009: SKILL.md has no Cowork fallback phrase
@assert_hermes_agent_untouched
def test_T3_009_skill_md_no_cowork_fallback(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    assert "Cowork" not in text


# T3.010: SKILL.md has no webbrowser.open(...)
@assert_hermes_agent_untouched
def test_T3_010_skill_md_no_webbrowser_open(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    assert "webbrowser.open" not in text


# T3.011: run_eval has the Hermes event-shape adapter
@assert_hermes_agent_untouched
def test_T3_011_run_eval_has_event_adapter(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_eval.py")
    # Adapter translates Hermes {event, role, content} into Anthropic shape.
    assert "event" in text
    assert "role" in text
    assert "content" in text


# T3.012: grader.md has agent_name + Hermes-style subagent header
@assert_hermes_agent_untouched
def test_T3_012_grader_subagent_registration(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "agents" / "grader.md")
    assert "agent_name: grader" in text
    assert "Subagent" in text


# T3.013: analyzer.md
@assert_hermes_agent_untouched
def test_T3_013_analyzer_subagent_registration(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "agents" / "analyzer.md")
    assert "agent_name: analyzer" in text
    assert "Subagent" in text


# T3.014: comparator.md
@assert_hermes_agent_untouched
def test_T3_014_comparator_subagent_registration(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "agents" / "comparator.md")
    assert "agent_name: comparator" in text
    assert "Subagent" in text


# T3.015: eval-viewer/generate_review.py is host-agnostic (no Claude binding)
@assert_hermes_agent_untouched
def test_T3_015_generate_review_no_claude(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "eval-viewer" / "generate_review.py")
    assert "claude" not in text.lower()
    assert "http.server" in text  # stdlib HTTP server


# T3.016: run_loop.py docstring + argparse use hermes, not claude
@assert_hermes_agent_untouched
def test_T3_016_run_loop_uses_hermes(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_loop.py")
    assert "claude" not in text
    assert "hermes" in text


# T3.017: no other claude/CLAUDECODE in run_loop body
@assert_hermes_agent_untouched
def test_T3_017_run_loop_no_claudecode(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "scripts" / "run_loop.py")
    assert "CLAUDECODE" not in text
    assert "claude" not in text


# T3.018: improve_description RuntimeError mentions hermes
@assert_hermes_agent_untouched
def test_T3_018_improve_description_runtime_error_mentions_hermes(
    skill_creator_home: Path,
) -> None:
    text = _read(SKILL_DIR / "scripts" / "improve_description.py")
    assert "hermes -p exited" in text
    assert "claude -p exited" not in text


# ---------------------------------------------------------------------------
# Active-cap detection (AC-4.10)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_detect_active_cap_unpatched_hermes_checkout(hermes_checkout: Path) -> None:
    """A fixture checkout with the literal `60` cap is detected as unpatched."""
    # Inject the cap-raise site into the fixture's skill_utils.py so detect
    # can read it. (hermes_checkout is a 6-file synthetic checkout, so we
    # write the missing file first.)
    utils = hermes_checkout / "agent" / "skill_utils.py"
    utils.parent.mkdir(parents=True, exist_ok=True)
    utils.write_text(
        'def extract_skill_description(frontmatter):\n    if len(desc) > 60:\n        return desc[:57] + "..."\n',
        encoding="utf-8",
    )
    assert detect_active_cap(hermes_checkout) == "unpatched"


@assert_hermes_agent_untouched
def test_detect_active_cap_patched_hermes_checkout(hermes_checkout: Path) -> None:
    utils = hermes_checkout / "agent" / "skill_utils.py"
    utils.parent.mkdir(parents=True, exist_ok=True)
    utils.write_text(
        "def extract_skill_description(frontmatter):\n"
        "    if len(desc) > MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n',
        encoding="utf-8",
    )
    assert detect_active_cap(hermes_checkout) == "patched"
