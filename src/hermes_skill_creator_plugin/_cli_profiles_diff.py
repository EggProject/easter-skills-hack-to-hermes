"""Set/skill diff helpers for cli_profiles audit.

Split from ``_cli_profiles_audit`` to keep module surface (WPS202) and
cognitive complexity (WPS231) within toolchain budgets.
"""

from __future__ import annotations

from pathlib import Path

DESIRED_SKILL = "skill-creator"
NEVER_DISABLE = frozenset({"openai", "skills"})


def walk_skills(skills_dir: Path) -> set[str]:
    """Return the set of installed skill NAMES under ``skills_dir``.

    NAME comes from the SKILL.md frontmatter ``name:`` field; the
    directory name is the fallback. Directories without SKILL.md are
    ignored. The walk is robust to read errors (the skill is dropped).
    """
    from agent.skill_utils import parse_frontmatter

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
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from agent.skill_utils import parse_frontmatter

        fm, _body = parse_frontmatter(text)
    except Exception:
        return None
    name = fm.get("name")
    if isinstance(name, str) and name:
        return name
    return child.name


def diff_sets(current: set[str], desired: set[str]) -> dict[str, list[str]]:
    """Compute the symmetric diff between current and desired as sorted lists."""
    return {
        "added": sorted(desired - current),
        "removed": sorted(current - desired),
    }
