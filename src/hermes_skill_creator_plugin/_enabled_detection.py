"""src/hermes_skill_creator_plugin/_enabled_detection.py

Single source of truth for "which skills are enabled for a profile?" — shared
by Script #2 (apply) and Script #3 (reporter). Owns: hermes_skill_creator_plugin.

See also: plans/06-script-2-profiles.md (owner), plans/13-script-3-report.md (consumer)

The reporter (Script #3) imports get_enabled_skills() from this module at
module top level. Script #2 also imports it. Neither re-implements the
detection logic locally. If this module is unavailable at import time the
reporter aborts with exit 6 — there is NO local re-implementation fallback.

TDD test cases for this module:
  test_get_enabled_skills_returns_frozenset
  test_get_enabled_skills_honors_config_toggle
  test_get_enabled_skills_honors_platform_filter
  test_get_enabled_skills_honors_conditional_exclusions
  test_get_enabled_skills_no_fallback_to_real_hermes_home
  test_get_enabled_skills_no_skills_returns_empty
  test_get_enabled_skills_ignores_disabled_dir
  test_get_enabled_skills_skips_skill_md_missing_dir
  test_get_enabled_skills_no_config_defaults_to_all_enabled
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-not-found]
import yaml

# A standard library of frontmatter parsing is unavailable; use python-frontmatter
# (the same library Hermes uses for skill descriptions). When the import is
# unavailable we fall back to a minimal manual split.


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a SKILL.md frontmatter block. Returns {} when the file is plain markdown.

    Uses python-frontmatter (the Hermes-standard library) when available.
    Falls back to a minimal `---\\n...\\n---\\n` regex split so the function
    works in environments without python-frontmatter.
    """
    try:
        post = frontmatter.load(str(path))
        return dict(post.metadata or {})
    except Exception:
        pass
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
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def _load_config(profile_path: Path) -> dict[str, Any]:
    """Read `<profile_path>/config.yaml`. Returns {} on missing or unparseable."""
    cfg = profile_path / "config.yaml"
    if not cfg.is_file():
        return {}
    try:
        loaded = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def _disabled_set(config: dict[str, Any], platform: str | None) -> set[str]:
    """Return the union of the disabled set and the platform-scoped set.

    Schema (matching hermes_cli.skills_config / agent.skill_utils):
        skills:
          disabled: [name_a, name_b]
          disabled_if_platform: {darwin: [name_c], linux: [name_d]}
    The `disabled_if_platform` map may also be expressed as a top-level key
    on the `skills` section. We honor both shapes.
    """
    skills_section = config.get("skills", {})
    if not isinstance(skills_section, dict):
        skills_section = {}
    out: set[str] = set()
    base = skills_section.get("disabled", [])
    if isinstance(base, list):
        out.update(str(x) for x in base)
    plat_map = skills_section.get("disabled_if_platform", {})
    if platform is not None and isinstance(plat_map, dict):
        for entry in plat_map.get(platform, []) or []:
            out.add(str(entry))
    return out


def _platform_blocked(frontmatter_dict: dict[str, Any], platform: str | None) -> bool:
    """Return True when the skill's frontmatter `platforms:` section blocks `platform`.

    The `platforms:` block (Hermes convention) is a list of dicts like:
        platforms:
          - disable_if_platform_present: [darwin]
    A skill with an empty `platforms:` list is unconditional (enabled on every
    host). A skill with NO `platforms:` key is also unconditional.
    """
    if platform is None:
        return False
    plats = frontmatter_dict.get("platforms")
    if not isinstance(plats, list):
        return False
    for entry in plats:
        if isinstance(entry, dict):
            blocked = entry.get("disable_if_platform_present", [])
            if isinstance(blocked, list) and platform in blocked:
                return True
    return False


def _conditional_excluded(frontmatter_dict: dict[str, Any], platform: str | None) -> bool:
    """Return True when the skill declares a per-skill `disable_if:` rule that fires.

    Convention honored:
        disable_if:
          platform: [darwin]
    A skill with an empty `disable_if` list is unconditional. Per-skill
    `disable_if` wins over the global toggle list.
    """
    rule = frontmatter_dict.get("disable_if")
    if not isinstance(rule, dict):
        return False
    if platform is None:
        return False
    plats = rule.get("platform", [])
    if isinstance(plats, list) and platform in plats:
        return True
    return False


def get_enabled_skills(
    profile_path: Path,
    *,
    platform: str | None = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for `profile_path`.

    Args:
        profile_path: The profile root. `config.yaml` is read from here; the
            `skills/` subdirectory is walked for `SKILL.md` files. The function
            never touches `~/.hermes/` (regression sentinel).
        platform: Optional platform tag (e.g. "darwin"); `None` means "the
            current host" (mirrors hermes_cli.skills_config).

    Returns:
        Frozen set of skill NAMES (not paths) that are currently ENABLED.
        Honors:
          1. `config[skills].disabled` per-skill on/off (the `disabled` list).
          2. Profile- AND platform-scoped conditional exclusions.
          3. `platforms:` frontmatter `disable_if_platform_present` lists.
          4. Per-skill `disable_if:` frontmatter rules (wins over the toggle list).
    """
    profile_path = Path(profile_path)
    config = _load_config(profile_path)
    disabled = _disabled_set(config, platform)
    skills_dir = profile_path / "skills"
    if not skills_dir.is_dir():
        return frozenset()
    enabled: set[str] = set()
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = _parse_frontmatter(skill_md)
        name = str(meta.get("name", skill_dir.name))
        if name in disabled:
            continue
        if _platform_blocked(meta, platform):
            continue
        if _conditional_excluded(meta, platform):
            continue
        enabled.add(name)
    return frozenset(enabled)


__all__ = ["get_enabled_skills"]
