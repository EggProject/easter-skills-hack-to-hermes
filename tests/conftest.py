"""Shared pytest fixtures for the hermes-skill-creator-plugin.

The workstream-C deliverable (``_patcher.py`` + ``cli_patch.py`` +
migration note) only needs a minimum Hermes-shaped checkout: a few
files at the canonical paths with the byte-exact anchor lines the
patcher matches against.

We use an INLINE minimal checkout here (per the workstream-C task
spec: "for now, inline a minimal tmp_path fixture"). A separate
``tests/fixtures/minimal_hermes/seed_minimal.py`` will be added in
workstream F (the meta workstream) and will replace this inline
fixture once F lands.

The no-touch sentinel (``real_hermes_agent_sentinel``) wraps every
patcher unit test to guarantee the live install is never written.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# ensure src/ is on sys.path even when pytest is invoked from a different cwd
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# --- anchor lines (byte-exact, copied from the pinned Hermes source) ------

SKILL_UTILS_BODY = '''\
"""Skill utility helpers (test fixture stand-in for agent/skill_utils.py)."""

from typing import Any, Dict


def extract_skill_description(frontmatter: Dict[str, Any]) -> str:
    """Extract a truncated description from parsed frontmatter."""
    raw_desc = frontmatter.get("description", "")
    if not raw_desc:
        return ""
    desc = str(raw_desc).strip().strip('\'"')
    if len(desc) > 60:
        return desc[:57] + "..."
    return desc
'''


# We need 688 / 689 to be the line numbers of the cap-raise / slice lines.
# SKILL_UTILS_BODY places them at L9/L10 of the body (12 body lines), so we
# pad with 676 leading comment lines to land them at L688/L689.
def _build_skill_utils_padded() -> str:
    lines: list[str] = []
    for i in range(1, 677):
        lines.append(f"# padding line {i}\n")
    lines.append(SKILL_UTILS_BODY)
    return "".join(lines)


SKILL_UTILS_PATCHED = _build_skill_utils_padded()


PROMPT_BUILDER_BODY = '''\
"""Prompt builder (test fixture stand-in for agent/prompt_builder.py)."""

# --- MEMORY_GUIDANCE (E2 anchor is L158) ---
MEMORY_GUIDANCE = (
    "If you've discovered a new way to do something, "
    "solved a problem that could be "
    "necessary later, save it as a skill with the skill tool.\\n"
    ")  # end MEMORY_GUIDANCE
'''


def _build_prompt_builder_padded() -> str:
    """Pad so that:

    - L158 is the E2 anchor (``necessary later, save it as a skill...``)
    - L179 is the E1 anchor (``Skills that aren't maintained...``)
    - L1421 is the E3 anchor (``After difficult/iterative tasks...``)
    """
    lines: list[str] = []
    # E2 lands at L158 -> 157 lines of padding BEFORE it
    for i in range(1, 158):
        lines.append(f"# padding {i}\n")
    # L158 — E2 anchor
    lines.append('    "necessary later, save it as a skill with the skill tool.\\n"\n')
    # 20 padding lines (L159..L178) -> E1 lands at L179
    for i in range(159, 179):
        lines.append(f"# padding {i}\n")
    # L179 — E1 anchor (within SKILLS_GUIDANCE)
    lines.append('    "Skills that aren\'t maintained become liabilities."\n')
    # 1241 padding lines (L180..L1420) -> E3 lands at L1421
    for i in range(180, 1421):
        lines.append(f"# padding {i}\n")
    # L1421 — E3 anchor (12-space indent)
    lines.append('            "After difficult/iterative tasks, offer to save as a skill. "\n')
    # trailing padding
    for i in range(1422, 1440):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


PROMPT_BUILDER_PATCHED = _build_prompt_builder_padded()


BACKGROUND_REVIEW_BODY = '''\
"""Background review (test fixture stand-in for agent/background_review.py)."""
'''


def _build_background_review_padded() -> str:
    """Pad so that:

    - L105 is the E4 anchor (the closing of the option-4 paragraph)
    - L192 is the E5 anchor
    """
    lines: list[str] = []
    # 104 padding lines (L1..L104) -> E4 lands at L105
    for i in range(1, 105):
        lines.append(f"# padding {i}\n")
    # L105 — E4 anchor
    # Use the actual em-dash (U+2014) bytes (e2 80 94), NOT the literal
    # 6-character escape sequence "\\u2014".
    lines.append("    \"today's task, it's wrong — fall back to (1), (2), or (3).\\n\\n\"\n")
    # 86 padding lines (L106..L191) -> E5 lands at L192
    for i in range(106, 192):
        lines.append(f"# padding {i}\n")
    # L192 — E5 anchor
    lines.append('    "(2), or (3).\\n\\n"\n')
    for i in range(193, 220):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


BACKGROUND_REVIEW_PATCHED = _build_background_review_padded()


SKILL_MANAGER_TOOL_BODY = '''\
"""Skill manager (test fixture stand-in for tools/skill_manager_tool.py)."""
'''


def _build_skill_manager_tool_padded() -> str:
    """Pad so that:

    - L1099/1100/1101 are the compound symbol locator
    - L1129 is the E6 single-line anchor
    - L1130 is the closing ``),``
    """
    lines: list[str] = []
    # 1098 padding lines (L1..L1098)
    for i in range(1, 1099):
        lines.append(f"# padding {i}\n")
    # L1099 / L1100 / L1101 — compound symbol locator
    lines.append("SKILL_MANAGE_SCHEMA = {\n")
    lines.append('    "name": "skill_manage",\n')
    lines.append('    "description": (\n')
    # L1102..L1128: implicit-concat description body (27 lines)
    for i in range(1102, 1129):
        lines.append(f'        "padding line {i} of description. "\n')
    # L1129 — single-line anchor (unique end-of-value)
    lines.append('        "pitfalls come up; pin only guards against irrecoverable loss."\n')
    # L1130
    lines.append("    ),\n")
    for i in range(1131, 1150):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


SKILL_MANAGER_TOOL_PATCHED = _build_skill_manager_tool_padded()


SKILLS_DOC_BODY = """\
# Skills

## Agent-Managed Skills (skill_manage tool)

The agent can create, update, and delete its own skills via the
`skill_manage` tool. This is the agent's **procedural memory** — when it
figures out a non-trivial workflow, it saves the approach as a skill for
future reuse.

### When the Agent Creates Skills
"""


def _build_skills_doc_padded() -> str:
    """Pad so L380 is the E7 anchor (the first paragraph under the
    ``## Agent-Managed Skills (skill_manage tool)`` heading).

    Layout:
      L378 = ``## Agent-Managed Skills (skill_manage tool)`` heading
      L379 = blank
      L380 = the E7 anchor (the first paragraph)
    """
    lines: list[str] = []
    for i in range(1, 378):
        lines.append(f"<!-- padding {i} -->\n")
    # L378 = heading
    lines.append("## Agent-Managed Skills (skill_manage tool)\n")
    # L379 = blank line
    lines.append("\n")
    # L380 = the E7 anchor (the first paragraph)
    lines.append(
        "The agent can create, update, and delete its own skills via the "
        "`skill_manage` tool. This is the agent's **procedural memory** — "
        "when it figures out a non-trivial workflow, it saves the approach "
        "as a skill for future reuse.\n"
    )
    return "".join(lines)


# --- the fixture ----------------------------------------------------------


@pytest.fixture
def hermes_checkout(tmp_path: Path) -> Generator[Path]:
    """A USER-OWNED fake Hermes checkout (the --target for Script #1).

    Lays down the minimum tree so Script #1's pre-validation can resolve
    all anchors. NEVER touches the real ``~/.hermes/``.
    """
    checkout = tmp_path / "hermes-checkout"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    (checkout / "hermes_cli").mkdir(parents=True)
    (checkout / "website" / "docs" / "user-guide" / "features").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    (checkout / "agent" / "prompt_builder.py").write_text(PROMPT_BUILDER_PATCHED, encoding="utf-8")
    (checkout / "agent" / "background_review.py").write_text(
        BACKGROUND_REVIEW_PATCHED, encoding="utf-8"
    )
    (checkout / "tools" / "skill_manager_tool.py").write_text(
        SKILL_MANAGER_TOOL_PATCHED, encoding="utf-8"
    )
    (checkout / "website" / "docs" / "user-guide" / "features" / "skills.md").write_text(
        _build_skills_doc_padded(), encoding="utf-8"
    )
    # also create the "tools.skills_tool" so the import-strategy pre-flight
    # can run a sanity import. (For the test path the script reads
    # `from tools.skills_tool import` -- it only needs the IMPORT LINE
    # to be absent, not the module to be importable.)
    yield checkout


@pytest.fixture
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    return "2026-06-17T00:00:00Z"


@pytest.fixture
def real_hermes_agent_sentinel() -> str | None:
    """Hash ~/.hermes/hermes-agent/agent/skill_utils.py before the test.

    Returns the pre-test hash; tests can re-hash after the run and assert
    equality. If the live install is missing, the fixture returns None and
    tests should skip the no-touch check.
    """
    target = Path.home() / ".hermes" / "hermes-agent" / "agent" / "skill_utils.py"
    if not target.exists():
        return None
    return hashlib.sha256(target.read_bytes()).hexdigest()


def assert_hermes_agent_untouched(pre: str | None) -> None:
    """Assert the live Hermes install is byte-identical to the pre-test hash."""
    if pre is None:
        return
    target = Path.home() / ".hermes" / "hermes-agent" / "agent" / "skill_utils.py"
    post = hashlib.sha256(target.read_bytes()).hexdigest()
    assert pre == post, f"HERMES-AGENT TOUCHED: {target} sha changed {pre} -> {post}"


@pytest.fixture
def worktree(tmp_path: Path) -> Generator[Path]:
    """A bare tmp worktree root for --emit-migration-note output."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    yield wt
