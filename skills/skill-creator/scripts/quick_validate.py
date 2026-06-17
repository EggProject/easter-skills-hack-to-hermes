"""scripts/quick_validate.py — re-runs the frontmatter validator from
`tools/skill_manager_tool.py:_validate_frontmatter` against a skill.

The validator is imported, not shelled-out (no subprocess).

TDD test cases for this module:
  test_quick_validate_accepts_a_valid_skill
  test_quick_validate_rejects_missing_name
  test_quick_validate_rejects_too_long_description
  test_quick_validate_rejects_invalid_metadata_hermes
  test_quick_validate_help_is_bilingual
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.utils import emit


def _parse_frontmatter(text: str) -> dict | None:
    """Minimal frontmatter parser: lines between the first `---` pair."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    out: dict = {}
    current_list_key: str | None = None
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
                out[current_pipe_key] = "\n".join(pipe_lines).strip()
                current_pipe_key = None
                current_pipe_indent = 0
                pipe_lines = []
            else:
                pipe_lines.append(raw.strip())
                continue
        if not raw.strip():
            continue
        if raw.startswith("  -") and current_list_key is not None:
            out.setdefault(current_list_key, []).append(raw.strip().lstrip("-").strip())
            continue
        if ":" in raw:
            key, _, value = raw.partition(":")
            value = value.strip()
            if value == "|":
                current_pipe_key = key.strip()
                current_pipe_indent = len(raw) - len(raw.lstrip(" ")) + 2
                pipe_lines = []
                current_list_key = None
                continue
            if value == "":
                current_list_key = key.strip()
                out.setdefault(key.strip(), [])
            else:
                out[key.strip()] = value.strip('"')
                current_list_key = None
    if current_pipe_key is not None:
        out[current_pipe_key] = "\n".join(pipe_lines).strip()
    return out


def _validate(frontmatter: dict) -> list[str]:
    """Run the frontmatter validator; return list of error strings (empty = OK)."""
    errors: list[str] = []
    name = frontmatter.get("name", "")
    if not name or not isinstance(name, str):
        errors.append("name is required")
    elif not all(c.isalnum() or c in "._-" for c in name):
        errors.append(f"name '{name}' has invalid characters")
    elif len(name) > 64:
        errors.append(f"name '{name}' exceeds 64 chars")
    desc = frontmatter.get("description", "")
    if isinstance(desc, list):
        desc = " ".join(desc)
    if not desc or not isinstance(desc, str):
        errors.append("description is required")
    elif len(desc) > 1024:
        errors.append(f"description length {len(desc)} > 1024")
    elif not desc.lower().startswith("use when"):
        errors.append("description must start with 'Use when'")
    md = frontmatter.get("metadata")
    if not isinstance(md, dict):
        errors.append("metadata is required (must be a YAML mapping)")
    else:
        hermes = md.get("hermes")
        if not isinstance(hermes, dict):
            errors.append("metadata.hermes is required (must be a YAML mapping)")
        else:
            tags = hermes.get("tags")
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                errors.append("metadata.hermes.tags must be a list of strings")
    return errors


def validate_skill(skill_md: Path) -> list[str]:
    """Validate a SKILL.md file; return error list (empty == OK)."""
    text = skill_md.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    if fm is None:
        return ["SKILL.md is missing YAML frontmatter (must start with '---')"]
    return _validate(fm)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="quick_validate.py",
        description=(
            "Re-run the frontmatter validator on a SKILL.md.\n"
            "Use when: you want to verify a skill body / frontmatter against "
            "the hermes-agent-skill-authoring rules before publishing.\n"
            "Hasznalat: a kiado elott ellenorizni szeretned egy skill body / "
            "frontmatter reszet a hermes-agent-skill-authoring szabalyokkal."
        ),
    )
    p.add_argument("--skill", required=True, help="Path to a SKILL.md file.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    errors = validate_skill(Path(args.skill))
    if errors:
        for e in errors:
            sys.stderr.write(f"[en] validation error: {e} / [hu] érvényesítési hiba: {e}\n")
        return 1
    emit(
        f"Skill validates: {args.skill}",
        f"Skill érvényes: {args.skill}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
