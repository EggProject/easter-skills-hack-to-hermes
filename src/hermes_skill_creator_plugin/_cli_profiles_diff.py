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


def _skill_name_from(child: Path) -> str | None:
    if not child.is_dir():
        return None
    skill_md = child / "SKILL.md"
    if not skill_md.is_file():
        return None
    fm = _parse_skill_frontmatter(skill_md)
    if fm is None:
        return None
    return _name_from_frontmatter(fm, fallback=child.name)


def _parse_skill_frontmatter(skill_md: Path) -> dict[str, object] | None:
    """Read SKILL.md + parse frontmatter; return None on any failure."""
    text = _read_skill_md(skill_md)
    if text is None:
        return None
    return _parse_frontmatter_text(text)


def _read_skill_md(skill_md: Path) -> str | None:
    """Read SKILL.md text or return None on OSError."""
    try:
        return skill_md.read_text(encoding="utf-8")
    except OSError:
        return None


def _parse_frontmatter_text(text: str) -> dict[str, object] | None:
    """Parse frontmatter text; return None on any exception."""
    try:
        from agent.skill_utils import parse_frontmatter

        fm, _body = parse_frontmatter(text)
    except Exception:
        return None
    return fm


def _name_from_frontmatter(
    fm: dict[str, object],
    *,
    fallback: str,
) -> str:
    """Return the ``name`` field if it is a non-empty string, else ``fallback``."""
    name = fm.get("name")
    if isinstance(name, str) and name:
        return name
    return fallback


def diff_sets(
    current: set[str],
    desired: set[str],
) -> dict[str, list[str]]:
    """Compute the symmetric diff between current and desired as sorted lists."""
    added = sorted(desired - current)
    removed = sorted(current - desired)
    return {"added": added, "removed": removed}
