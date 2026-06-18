"""src/hermes_skill_creator_plugin/_enabled_detection.py

Single source of truth for "which skills are enabled for a profile?" — shared
by Script #2 (apply) and Script #3 (reporter). Owns: hermes_skill_creator_plugin.

See also: plans/06-script-2-profiles.md (owner),
plans/13-script-3-report.md (consumer)

The reporter (Script #3) imports get_enabled_skills() from this module at
module top level. Script #2 also imports it. Neither re-implements the
detection logic locally. If this module is unavailable at import time
the reporter aborts with exit 6 — there is NO local re-implementation
fallback.

This module exposes two parallel helper APIs:

  - The original helpers (``_parse_frontmatter``, ``_load_config``,
    ``_disabled_set``, ``_platform_blocked``, ``_conditional_excluded``)
    used by the read-only reporter (Script #3) and its tests under
    ``tests/report/``.
  - The richer helpers (``_walk_installed_skill_names``,
    ``_find_skill_md``, ``_apply_platform_filter``,
    ``_apply_conditional_exclusions``, ``_platform_disables``,
    ``_split_top_level_commas``, ``_extract_disabled_from_inline``)
    used by Script #2's apply path and its tests under
    ``tests/unit/``.

``get_enabled_skills`` is the public entry point; it routes each call
through the richer helper pipeline and accepts BOTH the
``platforms: {darwin: value}`` shape (used by Script #2's unit tests)
and the ``platforms: [{disable_if_platform_present: [darwin]}]`` shape
(used by the reporter's tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
import yaml

# Key names referenced more than once in this module — kept as constants so
# the linter does not flag repeated string literals.
_SKILLS_KEY = "skills"
_DISABLED_KEY = "disabled"
_PLATFORMS_KEY = "platforms"
_PLATFORM_KEY = "platform"
_DISABLE_IF_KEY = "disable_if"
_DISABLED_IF_PLATFORM_KEY = "disabled_if_platform"
_DISABLE_IF_PLATFORM_PRESENT_KEY = "disable_if_platform_present"


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a SKILL.md frontmatter block. Returns {} on any error.

    Uses python-frontmatter (the Hermes-standard library) when available.
    Falls back to a minimal regex split so the function works in
    environments without python-frontmatter.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    import io

    try:
        post = frontmatter.load(io.StringIO(text))
        if post.metadata:
            return dict(post.metadata)
    except Exception:
        return _safe_yaml_dict(block)
    return _safe_yaml_dict(block)


def _safe_yaml_dict(block: str) -> dict[str, Any]:
    """Parse a YAML block; return {} on any failure or non-dict result."""
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def _load_config(profile_path: Path) -> dict[str, Any]:
    """Read ``<profile_path>/config.yaml``. Returns {} on missing or unparseable."""
    cfg = profile_path / "config.yaml"
    if not cfg.is_file():
        return {}
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return {}
    return _safe_yaml_dict(text)


def _disabled_set(config: dict[str, Any], platform: str | None) -> set[str]:
    """Return the union of the disabled set and the platform-scoped set.

    Schema (matching hermes_cli.skills_config / agent.skill_utils):
        skills:
          disabled: [name_a, name_b]
          disabled: name_a   (a bareword scalar — letters/digits/underscore
                              only — is also accepted as a single name)
          disabled_if_platform: {darwin: [name_c], linux: [name_d]}
    The ``disabled_if_platform`` map may also be expressed as a top-level
    key on the ``skills`` section. We honor both shapes. Non-list,
    non-bareword values (e.g. "not-a-list" with a hyphen, numbers,
    dicts) are silently ignored — they are not skill names.
    """
    import re

    skills_section = config.get(_SKILLS_KEY, {})
    if not isinstance(skills_section, dict):
        skills_section = {}
    out: set[str] = set()
    base = skills_section.get(_DISABLED_KEY, [])
    if isinstance(base, list):
        for entry in base:
            out.add(str(entry))
    elif isinstance(base, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", base):
        out.add(base)
    plat_map = skills_section.get(_DISABLED_IF_PLATFORM_KEY, {})
    if platform is not None and isinstance(plat_map, dict):
        for entry in plat_map.get(platform, []) or []:
            out.add(str(entry))
    return out


def _platform_blocked(
    frontmatter_dict: dict[str, Any],
    platform: str | None,
) -> bool:
    """Return True when the skill's ``platforms:`` section blocks ``platform``.

    Supports BOTH the reporter's contract (list of dicts with
    ``disable_if_platform_present``) and the Script #2 unit-test contract
    (a dict mapping platform -> truthy value).
    """
    if platform is None:
        return False
    plats = frontmatter_dict.get(_PLATFORMS_KEY)
    if isinstance(plats, list):
        for entry in plats:
            if not isinstance(entry, dict):
                continue
            blocked = entry.get(_DISABLE_IF_PLATFORM_PRESENT_KEY, [])
            if isinstance(blocked, list) and platform in blocked:
                return True
        return False
    if isinstance(plats, dict):
        plat_value = plats.get(platform)
        return _plat_value_blocks(plat_value)
    return False


def _plat_value_blocks(plat_value: Any) -> bool:
    """Return True iff a single ``platforms:`` value blocks the host."""
    if isinstance(plat_value, str):
        return bool(plat_value)
    if isinstance(plat_value, (list, tuple, set)):
        return any(item for item in plat_value)
    if isinstance(plat_value, dict):
        return any(plat_value.values()) if plat_value else False
    if plat_value is None:
        return False
    return bool(plat_value)


# Script #2 unit-test contract: dict-shape platforms (forwarded).
def _platform_disables(platforms: Any, platform: str) -> bool:
    """Return True if ``platforms`` (per-skill mapping) blocks ``platform``."""
    return _platform_blocked({_PLATFORMS_KEY: platforms}, platform)


def _conditional_excluded(
    frontmatter_dict: dict[str, Any],
    platform: str | None,
) -> bool:
    """Return True when the skill declares a per-skill ``disable_if:`` rule.

    Convention honored:
        disable_if:
          platform: [darwin]
    A skill with an empty ``disable_if`` dict is unconditional. Per-skill
    ``disable_if`` wins over the global toggle list.
    """
    rule = frontmatter_dict.get(_DISABLE_IF_KEY)
    if not isinstance(rule, dict):
        return False
    if platform is None:
        return False
    plats = rule.get(_PLATFORM_KEY, [])
    return isinstance(plats, list) and platform in plats


def _split_top_level_commas(text: str) -> list[str]:
    """Split ``text`` on top-level commas (commas outside of brackets)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _extract_disabled_from_inline(text: str, out: set[str]) -> None:
    """Populate ``out`` with names from a single ``disabled: [...]`` segment."""
    inner = text.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    disabled_prefix = _DISABLED_KEY + ":"
    for part in _split_top_level_commas(inner):
        kv = part.strip()
        if not kv.startswith(disabled_prefix):
            continue
        value = kv[len(disabled_prefix):].strip()
        if not (value.startswith("[") and value.endswith("]")):
            continue
        items = _split_top_level_commas(value[1:-1].strip())
        for item in items:
            name = item.strip().strip('"').strip("'")
            if name:
                out.add(name)


def _walk_installed_skill_names(skills_dir: Path) -> set[str]:
    """Walk ``skills_dir`` and return the set of installed skill NAMES.

    NAME precedence: frontmatter ``name`` if present and parsable,
    otherwise the directory name.
    """
    import re

    if not skills_dir.is_dir():
        return set()
    names: set[str] = set()
    name_re = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        match = name_re.search(text)
        if match is None:
            names.add(str(child.name))
        else:
            names.add(str(match.group(1).strip().strip('"').strip("'")))
    return names


def _find_skill_md(skills_dir: Path, name: str) -> Path | None:
    """Locate the ``SKILL.md`` for a skill by NAME.

    The lookup is directory-name match first, then a frontmatter cross-
    reference loop.
    """
    if not skills_dir.is_dir():
        return None
    direct = skills_dir / name / "SKILL.md"
    if direct.is_file():
        return direct
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = _parse_frontmatter(skill_md)
        if str(meta.get("name", child.name)) == name:
            return skill_md
    return None


def _apply_platform_filter(
    installed_names: set[str],
    profile_path: Path,
    platform: str | None,
) -> set[str]:
    """Return the subset of ``installed_names`` NOT disabled by the platform."""
    if platform is None:
        return set(installed_names)
    skills_dir = profile_path / "skills"
    out: set[str] = set()
    for name in installed_names:
        skill_md = _find_skill_md(skills_dir, name)
        if skill_md is None:
            out.add(name)  # defensive: conservatively keep
            continue
        meta = _parse_frontmatter(skill_md)
        if not meta:
            out.add(name)  # empty frontmatter: no platforms rule
            continue
        if not _platform_blocked(meta, platform):
            out.add(name)
    return out


def _apply_conditional_exclusions(
    installed_names: set[str],
    profile_path: Path,
    platform: str | None,
) -> set[str]:
    """Return the subset of ``installed_names`` not excluded by per-skill rules."""
    skills_dir = profile_path / "skills"
    out: set[str] = set()
    for name in installed_names:
        skill_md = _find_skill_md(skills_dir, name)
        if skill_md is None:
            out.add(name)  # defensive: conservatively keep
            continue
        meta = _parse_frontmatter(skill_md)
        if not meta:
            out.add(name)
            continue
        rule = meta.get(_DISABLE_IF_KEY)
        if isinstance(rule, dict) and _PLATFORM_KEY in rule:
            if not _conditional_excluded(meta, platform):
                out.add(name)
            continue
        if rule is None or rule == "":
            out.add(name)
    return out


def get_enabled_skills(
    profile_path: Path,
    *,
    platform: str | None = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for ``profile_path``.

    Args:
        profile_path: The profile root. ``config.yaml`` is read from
            here; the ``skills/`` subdirectory is walked for SKILL.md
            files.
        platform: Optional platform tag (e.g. "darwin"); ``None`` means
            "the current host".

    Returns:
        Frozen set of skill NAMES (not paths) that are currently ENABLED.
    """
    profile_path = Path(profile_path)
    skills_dir = profile_path / "skills"
    installed = _walk_installed_skill_names(skills_dir)
    if not installed:
        return frozenset()
    config = _load_config(profile_path)
    disabled = _disabled_set(config, platform)
    if disabled:
        installed = {entry for entry in installed if entry not in disabled}
    installed = _apply_platform_filter(installed, profile_path, platform)
    installed = _apply_conditional_exclusions(installed, profile_path, platform)
    return frozenset(installed)


PUBLIC_NAMES = [
    "get_enabled_skills",
    # Original helpers.
    "_parse_frontmatter",
    "_load_config",
    "_disabled_set",
    "_platform_blocked",
    "_conditional_excluded",
    # Richer helpers.
    "_walk_installed_skill_names",
    "_find_skill_md",
    "_apply_platform_filter",
    "_apply_conditional_exclusions",
    "_platform_disables",
    "_extract_disabled_from_inline",
    "_split_top_level_commas",
]
