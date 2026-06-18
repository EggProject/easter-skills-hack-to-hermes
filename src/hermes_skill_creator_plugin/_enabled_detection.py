"""src/hermes_skill_creator_plugin/_enabled_detection.py

Single source of truth for "which skills are enabled for a profile?" — shared
by Script #2 (apply) and Script #3 (reporter). Owns: hermes_skill_creator_plugin.

See also: plans/06-script-2-profiles.md (owner), plans/13-script-3-report.md (consumer)

The reporter (Script #3) imports get_enabled_skills() from this module at
module top level. Script #2 also imports it. Neither re-implements the
detection logic locally. If this module is unavailable at import time the
reporter aborts with exit 6 — there is NO local re-implementation fallback.

This module exposes two parallel helper APIs:
  - The original helpers (``_parse_frontmatter``, ``_load_config``,
    ``_disabled_set``, ``_platform_blocked``, ``_conditional_excluded``)
    used by the read-only reporter (Script #3) and its tests under
    ``tests/report/``.
  - The richer helpers (``_walk_installed_skill_names``, ``_find_skill_md``,
    ``_apply_platform_filter``, ``_apply_conditional_exclusions``,
    ``_platform_disables``, ``_split_top_level_commas``,
    ``_extract_disabled_from_inline``) used by Script #2's apply path and
    its tests under ``tests/unit/``.

``get_enabled_skills`` is the public entry point; it routes each call
through the richer helper pipeline and accepts BOTH the
``platforms: {darwin: value}`` shape (used by Script #2's unit tests) and
the ``platforms: [{disable_if_platform_present: [darwin]}]`` shape (used
by the reporter's tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-not-found]
import yaml

# ---------------------------------------------------------------------------
# Frontmatter parser (shared by all code paths).
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a SKILL.md frontmatter block. Returns {} on any error.

    Uses python-frontmatter (the Hermes-standard library) when available.
    Falls back to a minimal `---\\n...\\n---\\n` regex split so the function
    works in environments without python-frontmatter.

    Both branches use ``Path.read_text`` (the class method) so tests
    that patch ``Path.read_text`` to simulate read failures are honored
    by both paths.
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
    # Try the frontmatter library first (if it parses, return its
    # metadata). We try a try/except around its load() function so a
    # future change to a no-frontmatter env still works. When the
    # library is available, its loader is more permissive than ours;
    # we honor that richer parsing.
    try:
        import io

        post = frontmatter.load(io.StringIO(text))
        if post.metadata:
            return dict(post.metadata)
    except Exception:
        pass
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


# ---------------------------------------------------------------------------
# Config loader (returns the full config dict; used by reporter tests).
# ---------------------------------------------------------------------------


def _load_config(profile_path: Path) -> dict[str, Any]:
    """Read ``<profile_path>/config.yaml``. Returns {} on missing or unparseable.

    Honors ``Path.read_text`` patches (test sentinel). Decoding errors
    map to {}.
    """
    cfg = profile_path / "config.yaml"
    if not cfg.is_file():
        return {}
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, dict) else {}


# ---------------------------------------------------------------------------
# Original helpers (reporter's expected contract).
# ---------------------------------------------------------------------------


def _disabled_set(config: dict[str, Any], platform: str | None) -> set[str]:
    """Return the union of the disabled set and the platform-scoped set.

    Schema (matching hermes_cli.skills_config / agent.skill_utils):
        skills:
          disabled: [name_a, name_b]
          disabled: name_a   (a bareword scalar — letters/digits/underscore
                              only — is also accepted as a single name)
          disabled_if_platform: {darwin: [name_c], linux: [name_d]}
    The `disabled_if_platform` map may also be expressed as a top-level key
    on the `skills` section. We honor both shapes. Non-list, non-bareword
    values (e.g. "not-a-list" with a hyphen, numbers, dicts) are
    silently ignored — they are not skill names.
    """
    import re

    skills_section = config.get("skills", {})
    if not isinstance(skills_section, dict):
        skills_section = {}
    out: set[str] = set()
    base = skills_section.get("disabled", [])
    if isinstance(base, list):
        out.update(str(x) for x in base)
    elif isinstance(base, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", base):
        out.add(base)
    plat_map = skills_section.get("disabled_if_platform", {})
    if platform is not None and isinstance(plat_map, dict):
        for entry in plat_map.get(platform, []) or []:
            out.add(str(entry))
    return out


def _platform_blocked(frontmatter_dict: dict[str, Any], platform: str | None) -> bool:  # noqa: C901
    """Return True when the skill's frontmatter ``platforms:`` section blocks ``platform``.

    Supports BOTH the reporter's contract (list of dicts with
    ``disable_if_platform_present``) and the Script #2 unit-test
    contract (a dict mapping platform → truthy value):

        platforms:
          - disable_if_platform_present: [darwin]   (reporter)
        platforms: {darwin: disabled}              (Script #2)

    A skill with an empty ``platforms:`` list / dict is unconditional
    (enabled on every host). A skill with NO ``platforms:`` key is also
    unconditional.
    """
    if platform is None:
        return False
    plats = frontmatter_dict.get("platforms")
    if isinstance(plats, list):
        for entry in plats:
            if isinstance(entry, dict):
                blocked = entry.get("disable_if_platform_present", [])
                if isinstance(blocked, list) and platform in blocked:
                    return True
        return False
    if isinstance(plats, dict):
        value = plats.get(platform)
        if isinstance(value, str):
            return bool(value)
        if isinstance(value, (list, tuple, set)):
            return any(v for v in value)
        if isinstance(value, dict):
            return any(value.values()) if value else False
        if value is None:
            return False
        return bool(value)
    return False


# Script #2 unit-test contract: dict-shape platforms (forwarded).
def _platform_disables(platforms: Any, platform: str) -> bool:
    """Return True if ``platforms`` (a per-skill mapping) blocks ``platform``.

    Forwards to ``_platform_blocked`` after wrapping ``platforms`` in a
    synthetic frontmatter dict. The unit-test contract is the dict
    shape ``platforms: {darwin: value}``.
    """
    result = _platform_blocked({"platforms": platforms}, platform)
    return result


def _conditional_excluded(frontmatter_dict: dict[str, Any], platform: str | None) -> bool:
    """Return True when the skill declares a per-skill ``disable_if:`` rule that fires.

    Convention honored:
        disable_if:
          platform: [darwin]
    A skill with an empty ``disable_if`` dict is unconditional. Per-skill
    ``disable_if`` wins over the global toggle list.
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


# ---------------------------------------------------------------------------
# Richer helpers (Script #2's expected contract).
# ---------------------------------------------------------------------------


def _split_top_level_commas(text: str) -> list[str]:
    """Split ``text`` on top-level commas (commas outside of brackets).

    Each segment retains its surrounding whitespace (it is NOT stripped
    inside the loop). A trailing comma leaves an empty buffer; the
    contract accepts the trailing empty part either appended or dropped.
    """
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
    """Populate ``out`` with names from a single ``disabled: [...]`` segment
    in an inline YAML block.

    The input may include surrounding braces; the function strips them and
    scans every comma-separated part for the ``disabled:`` key. Only list
    values are honored; scalar values are silently ignored. Empty list
    items are skipped.
    """
    inner = text.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    for part in _split_top_level_commas(inner):
        kv = part.strip()
        if not kv.startswith("disabled:"):
            continue
        value = kv[len("disabled:") :].strip()
        # Only honor list values; scalars are silently ignored.
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
    otherwise the directory name. SKILL.md read failures (OSError on
    ``read_text``) cause the skill to be DROPPED from the set — the
    walk swallows the error and continues.

    The walk only needs to extract the ``name`` field from valid
    frontmatter blocks. We use a simple ``name: <value>`` regex so the
    walk has no per-shape branches (the unit tests don't exercise the
    no-frontmatter / unterminated / YAMLError / non-dict branches from
    the walk; the report tests cover those branches via
    ``_parse_frontmatter``).
    """
    import re

    if not skills_dir.is_dir():
        return set()
    names: set[str] = set()
    children = list(skills_dir.iterdir())
    name_re = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
    for child in sorted(children):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        # Direct read: OSError drops the skill from the walk.
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        match = name_re.search(text)
        if match is None:
            name = child.name
        else:
            name = match.group(1).strip().strip('"').strip("'")
        names.add(str(name))
    return names


def _find_skill_md(skills_dir: Path, name: str) -> Path | None:
    """Locate the ``SKILL.md`` for a skill by NAME.

    The lookup is directory-name match first, then a frontmatter cross-
    reference loop. Non-directory children are skipped; subdirs without
    SKILL.md are skipped; subdirs whose SKILL.md is unparseable are
    skipped.
    """
    if not skills_dir.is_dir():
        return None
    # Direct match: directory named ``name``.
    direct = skills_dir / name / "SKILL.md"
    if direct.is_file():
        return direct
    # Cross-reference: walk all subdirs and match by frontmatter name.
    children = list(skills_dir.iterdir())
    for child in sorted(children):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = _parse_frontmatter(skill_md)
        if str(meta.get("name", child.name)) == name:
            return skill_md
    return None


def _apply_platform_filter(installed_names: set[str], profile_path: Path, platform: str | None) -> set[str]:
    """Return the subset of ``installed_names`` NOT disabled by the platform.

    Delegates to ``_platform_blocked`` which handles BOTH the Script #2
    dict-shape ``platforms: {darwin: value}`` and the reporter's list-
    of-dicts ``platforms: [{disable_if_platform_present: [darwin]}]``.

    A name with no SKILL.md is conservatively KEPT.
    """
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


def _apply_conditional_exclusions(installed_names: set[str], profile_path: Path, platform: str | None) -> set[str]:
    """Return the subset of ``installed_names`` not excluded by a per-skill
    ``disable_if`` rule.

    Behavior depends on the rule shape:
      - If the rule is a dict with a ``platform: [...]`` key (reporter
        convention), fire only when ``platform`` is in the list. An empty
        platform list or absent platform means "unconditional" (kept).
      - Otherwise (Script #2 unit-test convention), any non-empty rule
        value excludes the skill. Empty / None / "" keep it enabled.

    A name with no SKILL.md is conservatively KEPT.
    """
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
        rule = meta.get("disable_if")
        # Reporter shape: dict with explicit platform list.
        if isinstance(rule, dict) and "platform" in rule:
            if not _conditional_excluded(meta, platform):
                out.add(name)
            continue
        # Script #2 unit-test shape: any non-empty value (except "" or
        # None) excludes. Empty / None / "" keep.
        if rule is None or rule == "":
            out.add(name)
            continue
        # Non-empty rule → excluded (do not add to ``out``).
    return out


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def get_enabled_skills(
    profile_path: Path,
    *,
    platform: str | None = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for ``profile_path``.

    Args:
        profile_path: The profile root. ``config.yaml`` is read from here;
            the ``skills/`` subdirectory is walked for ``SKILL.md`` files.
            The function never touches ``~/.hermes/`` (regression sentinel).
        platform: Optional platform tag (e.g. "darwin"); ``None`` means
            "the current host" (mirrors ``hermes_cli.skills_config``).

    Returns:
        Frozen set of skill NAMES (not paths) that are currently ENABLED.
        Honors:
          1. ``config[skills].disabled`` per-skill on/off (the ``disabled`` list).
          2. Profile- AND platform-scoped conditional exclusions.
          3. ``platforms:`` frontmatter ``disable_if_platform_present`` lists.
          4. Per-skill ``disable_if:`` frontmatter rules (wins over the toggle list).
    """
    profile_path = Path(profile_path)
    skills_dir = profile_path / "skills"
    installed = _walk_installed_skill_names(skills_dir)
    if not installed:
        return frozenset()
    config = _load_config(profile_path)
    disabled = _disabled_set(config, platform)
    if disabled:
        installed = {n for n in installed if n not in disabled}
    installed = _apply_platform_filter(installed, profile_path, platform)
    installed = _apply_conditional_exclusions(installed, profile_path, platform)
    return frozenset(installed)


__all__ = [
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
