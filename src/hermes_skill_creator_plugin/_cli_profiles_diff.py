"""Set/skill diff helpers for cli_profiles audit.

Split from ``_cli_profiles_audit`` to keep module surface (WPS202) and
cognitive complexity (WPS231) within toolchain budgets.
"""

from __future__ import annotations

from pathlib import Path

DESIRED_SKILL = "skill-creator"
NEVER_DISABLE: frozenset[str] = frozenset(("openai", "skills"))


def walk_skills(skills_dir: Path) -> set[str]:
    """Return the set of installed skill NAMES under ``skills_dir``.

    NAME comes from the SKILL.md frontmatter ``name:`` field; the
    directory name is the fallback. Directories without SKILL.md are
    ignored. The walk is robust to read errors (the skill is dropped).
    """

    if not skills_dir.is_dir():
        return set()
    return _collect_skill_names(sorted(skills_dir.iterdir()))


def _collect_skill_names(children: list[Path]) -> set[str]:
    out: set[str] = set()
    for child in children:
        name = _skill_name_from(child)
        if name:
            out.add(name)
    return out


_NAME_PARSE_FAILED: str = "__NAME_PARSE_FAILED__"


def _skill_name_from(child: Path) -> str | None:
    if not child.is_dir():
        return None
    skill_md = child / "SKILL.md"
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    name = _parse_name_or_marker(text)
    return _resolve_name(name, child)


def _resolve_name(name: str, child: Path) -> str | None:
    if name == _NAME_PARSE_FAILED:
        return None
    if name == "":
        return child.name
    return name


def _parse_name_or_marker(text: str) -> str:
    """Return the name, or ``_NAME_PARSE_FAILED`` sentinel on parse error / missing."""
    try:
        return _extract_name(text)
    except Exception:
        return _NAME_PARSE_FAILED


def _extract_name(text: str) -> str:
    from agent.skill_utils import parse_frontmatter

    fm, _body = parse_frontmatter(text)
    candidate = fm.get("name")
    if isinstance(candidate, str) and candidate:
        return candidate
    return ""


def diff_sets(current: set[str], desired: set[str]) -> dict[str, list[str]]:
    """Compute the symmetric diff between current and desired as sorted lists."""
    return {
        "added": sorted(desired - current),
        "removed": sorted(current - desired),
    }
