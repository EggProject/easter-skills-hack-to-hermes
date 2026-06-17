"""Unit tests for the migrated SKILL.md frontmatter + tool-name compliance.

Per docs/plans/07 §TDD test list (Frontmatter, Tool-name compliance).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401
from hermes_skill_creator_plugin.skill_installer import (  # noqa: E402
    FULL_DESC_CAP,
    SHORT_DESC_CAP,
    T3_INVENTORY,
    detect_active_cap,
    install,
)
from hermes_skill_creator_plugin.skill_installer import (  # noqa: E402
    PINNED_UPSTREAM_COMMIT,
)


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"
WORKTREE = Path(__file__).resolve().parents[2]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    """Strip ```...``` code-fence blocks from a markdown body."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    """YAML frontmatter parser. Uses PyYAML when available, falls back to a
    minimal hand-rolled parser (handles scalar + pipe-scalar + list + nested
    mappings) for offline runs.
    """
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    assert end != -1, "frontmatter must close with a '---' line"
    block = text[4:end]
    try:
        import yaml

        return yaml.safe_load(block) or {}
    except ImportError:
        pass
    return _minimal_yaml_parse(block)


def _minimal_yaml_parse(block: str) -> dict:
    """Tiny YAML parser: scalar + pipe-scalar + list + nested mappings.

    Good enough for the migrated skill's frontmatter; tests rely on PyYAML
    being installed (it's already a dependency) but the fallback is here for
    hermetic offline runs.
    """
    lines: list[tuple[int, str, str, str]] = []  # (indent, key, value, marker)
    current_pipe_key: str | None = None
    current_pipe_indent: int = 0
    pipe_lines: list[str] = []
    for raw in block.splitlines():
        if current_pipe_key is not None:
            if not raw.strip():
                pipe_lines.append("")
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if indent < current_pipe_indent:
                lines.append(
                    (current_pipe_indent - 2, current_pipe_key, "\n".join(pipe_lines).strip(), "scalar")
                )
                current_pipe_key = None
                current_pipe_indent = 0
                pipe_lines = []
            else:
                pipe_lines.append(raw.strip())
                continue
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        s = raw.lstrip(" ")
        if s.startswith("- "):
            lines.append((indent, "__list__", s[2:].strip(), "list-item"))
            continue
        if ":" in s:
            key, _, value = s.partition(":")
            value = value.strip()
            if value == "|":
                current_pipe_key = key.strip()
                current_pipe_indent = indent + 2
                pipe_lines = []
                continue
            if value == "":
                lines.append((indent, key.strip(), "", "map-open"))
            else:
                lines.append((indent, key.strip(), value.strip('"').strip("'"), "scalar"))
    if current_pipe_key is not None:
        lines.append(
            (current_pipe_indent - 2, current_pipe_key, "\n".join(pipe_lines).strip(), "scalar")
        )

    root: dict = {}
    stack: list[tuple[int, dict | list]] = [(0, root)]
    for indent, key, value, marker in lines:
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(0, root)]
        parent = stack[-1][1]
        if marker == "list-item":
            if isinstance(parent, list):
                parent.append(value)
        elif marker == "scalar":
            if isinstance(parent, dict):
                parent[key] = value
        elif marker == "map-open":
            if isinstance(parent, dict):
                if key in parent and isinstance(parent[key], list):
                    new: dict = {}
                    parent[key].append(new)
                else:
                    new = {}
                    parent[key] = new
                stack.append((indent, new))
    return root


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_short_skill_md_exists(skill_creator_home: Path) -> None:
    assert (SKILL_DIR / "SKILL.md.short").exists()


@assert_hermes_agent_untouched
def test_full_skill_md_exists(skill_creator_home: Path) -> None:
    assert (SKILL_DIR / "SKILL.md").exists()


@assert_hermes_agent_untouched
def test_short_description_under_short_cap(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md.short"))
    desc = fm["description"]
    assert isinstance(desc, str)
    assert len(desc) <= SHORT_DESC_CAP, f"short desc len {len(desc)} > {SHORT_DESC_CAP}"


@assert_hermes_agent_untouched
def test_full_description_under_full_cap(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md"))
    desc = fm["description"]
    if isinstance(desc, list):
        desc = " ".join(desc)
    assert isinstance(desc, str)
    assert len(desc) <= FULL_DESC_CAP, f"full desc len {len(desc)} > {FULL_DESC_CAP}"


@assert_hermes_agent_untouched
def test_full_description_starts_with_use_when(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md"))
    desc = fm["description"]
    if isinstance(desc, list):
        desc = " ".join(desc)
    assert desc.lower().startswith("use when"), f"description must start with 'Use when', got: {desc[:60]!r}"


@assert_hermes_agent_untouched
def test_short_description_starts_with_use_when(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md.short"))
    desc = fm["description"]
    assert desc.lower().startswith("use when"), f"short desc must start with 'Use when', got: {desc!r}"


@assert_hermes_agent_untouched
def test_metadata_hermes_tags_present(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md"))
    md = fm.get("metadata", {})
    if isinstance(md, str):
        md = {}
    hermes = md.get("hermes", {}) if isinstance(md, dict) else {}
    tags = hermes.get("tags", [])
    assert isinstance(tags, list)
    for required in ("authoring", "validation", "eval", "migration"):
        assert required in tags, f"metadata.hermes.tags missing {required!r}"


@assert_hermes_agent_untouched
def test_metadata_hermes_related_skills_is_list(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md"))
    md = fm.get("metadata", {})
    if isinstance(md, str):
        md = {}
    hermes = md.get("hermes", {}) if isinstance(md, dict) else {}
    related = hermes.get("related_skills", [])
    assert isinstance(related, list)
    assert len(related) >= 1


@assert_hermes_agent_untouched
def test_name_is_lowercase_alnum_dot_dash_underscore(skill_creator_home: Path) -> None:
    fm = _parse_frontmatter(_read(SKILL_DIR / "SKILL.md"))
    name = fm["name"]
    assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name), f"invalid name: {name!r}"
    assert len(name) <= 64


# ---------------------------------------------------------------------------
# Tool-name compliance
# ---------------------------------------------------------------------------


UPPERCASE_TOOL_NAMES = [
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task", "Skill",
    "AskUserQuestion", "WebSearch", "WebFetch", "TodoWrite",
]
HERMES_TOOL_NAMES = [
    "skill_manage", "skill_view", "skills_list", "read_file", "write_file",
    "patch", "search_files", "terminal", "delegate_task", "clarify",
    "web_search", "web_extract", "todo", "cronjob",
]


@assert_hermes_agent_untouched
def test_no_uppercase_tool_names_in_full_body_outside_fences(skill_creator_home: Path) -> None:
    """Anthropic tool names are uppercase; the migrated skill uses lowercase
    names. The test matches a tool invocation pattern (`Name(` or `Name=` or
    `Name)`) so that English prose uses of the same words (e.g. "Skill
    Creator") do not false-positive.
    """
    text = _read(SKILL_DIR / "SKILL.md")
    body = text.split("---\n", 2)[2] if "\n---\n" in text else text
    body = _strip_fences(body)
    for name in UPPERCASE_TOOL_NAMES:
        # Tool invocation shape: `\bName\s*\(` (e.g. `Read(`, `Skill(`).
        pattern = r"\b" + re.escape(name) + r"\s*\("
        assert not re.search(pattern, body), (
            f"uppercase tool name {name!r} invoked in SKILL.md body "
            "(matched `<Name>(`)"
        )


@assert_hermes_agent_untouched
def test_lowercase_tool_names_present_in_body(skill_creator_home: Path) -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    body = text.split("---\n", 2)[2] if "\n---\n" in text else text
    body = _strip_fences(body)
    for name in HERMES_TOOL_NAMES:
        assert name in body, f"Hermes tool name {name!r} missing from SKILL.md body"


@assert_hermes_agent_untouched
def test_no_claude_invocations_in_skill_md(skill_creator_home: Path) -> None:
    """The body must not contain `claude -p` or `claude -` invocations.

    Anthropic provenance mention is allowed (description + body may name
    the source skill); the test checks for invocations (claude followed by
    a hyphen flag), not bare mentions.
    """
    text = _read(SKILL_DIR / "SKILL.md")
    body = text.split("---\n", 2)[2] if "\n---\n" in text else text
    body = _strip_fences(body)
    # `claude -p`, `claude --model`, `claude -c`, etc.
    assert not re.search(r"\bclaude\s+-[a-zA-Z-]", body), (
        f"found 'claude -<flag>' invocation in SKILL.md body"
    )


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
        "def extract_skill_description(frontmatter):\n"
        "    if len(desc) > 60:\n"
        '        return desc[:57] + "..."\n',
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
