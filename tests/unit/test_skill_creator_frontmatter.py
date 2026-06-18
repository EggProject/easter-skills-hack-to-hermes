"""Unit tests for the migrated SKILL.md frontmatter + tool-name compliance.

Per docs/plans/07 §TDD test list (Frontmatter, Tool-name compliance).

The T3 per-binding inventory tests + active-cap detection tests
(AC-4.10) live in `test_skill_creator_t3_inventory.py` to keep each file
under the per-file 500-line cap
(plans/10-toolchain-and-conventions.md D1 + tools/check_line_count.py).
"""

from __future__ import annotations

import re
from pathlib import Path

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401
from hermes_skill_creator_plugin.skill_installer import (  # noqa: E402
    FULL_DESC_CAP,
    SHORT_DESC_CAP,
)

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"


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


def _minimal_yaml_parse(block: str) -> dict:  # noqa: C901
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
                    (
                        current_pipe_indent - 2,
                        current_pipe_key,
                        "\n".join(pipe_lines).strip(),
                        "scalar",
                    )
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
        lines.append((current_pipe_indent - 2, current_pipe_key, "\n".join(pipe_lines).strip(), "scalar"))

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
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "Task",
    "Skill",
    "AskUserQuestion",
    "WebSearch",
    "WebFetch",
    "TodoWrite",
]
HERMES_TOOL_NAMES = [
    "skill_manage",
    "skill_view",
    "skills_list",
    "read_file",
    "write_file",
    "patch",
    "search_files",
    "terminal",
    "delegate_task",
    "clarify",
    "web_search",
    "web_extract",
    "todo",
    "cronjob",
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
            f"uppercase tool name {name!r} invoked in SKILL.md body " "(matched `<Name>(`)"
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
    assert not re.search(r"\bclaude\s+-[a-zA-Z-]", body), "found 'claude -<flag>' invocation in SKILL.md body"
