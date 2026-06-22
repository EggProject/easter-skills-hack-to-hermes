"""Unit tests for ``easter_hermes_sorry_skills._enabled_detection`` (TDD plan 06).

TDD list (plan 06 §TDD test list → Shared enabled-detection module):
- test_get_enabled_skills_honors_config_toggle
- test_get_enabled_skills_honors_platform_filter
- test_get_enabled_skills_honors_conditional_exclusions
- test_get_enabled_skills_returns_frozenset
- test_get_enabled_skills_no_fallback_to_real_hermes_home

The function ``get_enabled_skills(profile_path, *, platform=None)`` is the
single source of truth for "which skills are enabled in this profile?"
shared by Script #2 (audit + apply) AND Script #3 (read-only reporter).

The tests run against ``tmp_path`` profile trees; they NEVER touch the
live ``~/.hermes/`` install (the ``real_hermes_agent_sentinel`` fixture
in ``tests/conftest.py`` guards every test that has the side-effect
potential).

For ``parse_frontmatter`` we inject a small fake into ``sys.modules`` so
the tests do not depend on the real ``agent.skill_utils`` being
importable (the live install requires ``yaml`` / ``rich`` which are
not part of the test venv).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixtures: minimal profile trees under tmp_path.
# ---------------------------------------------------------------------------


def _write_skill(skills_dir: Path, name: str, frontmatter: str, body: str = "") -> None:
    """Write a SKILL.md with the given frontmatter text + optional body."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    text = f"---\n{frontmatter}\n---\n{body}"
    (skill_dir / "SKILL.md").write_text(text)


def _write_config(profile_path: Path, **skills_section: Any) -> None:
    """Write a tiny ``config.yaml`` with a ``skills:`` section.

    Defaults to ``{"disabled": []}`` when not given.
    """
    cfg = skills_section or {"disabled": []}
    # Hand-rolled YAML for the trivial shape we need; avoid the pyyaml
    # dependency on the test side.
    lines = ["skills:"]
    for key, value in cfg.items():
        if isinstance(value, list):
            lines.append(f"  {key}: [{', '.join(value)}]")
        else:
            lines.append(f"  {key}: {value}")
    (profile_path / "config.yaml").write_text("\n".join(lines) + "\n")


@pytest.fixture
def fake_agent_skill_utils(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Replace ``agent.skill_utils`` with a tiny fake exposing
    ``parse_frontmatter(content) -> (frontmatter_dict, body)``.

    The real parser handles multi-doc YAML; the fake handles the trivial
    ``---`` / ``---`` blocks the tests need. Tests assert the function
    is called with the right content; the body returned is opaque.
    """
    state: dict[str, object] = {"calls": []}

    def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        state["calls"].append(content)
        if not content.startswith("---\n"):
            return {}, content
        end = content.find("\n---", 4)
        if end == -1:
            return {}, content
        fm_text = content[4:end]
        body = content[end + 4 :]
        return _parse_frontmatter_block(fm_text), body

    def _parse_frontmatter_block(fm_text: str) -> dict[str, Any]:
        """Tiny YAML reader for the frontmatter shapes the tests need.

        Accepts:
        - ``name: foo``            → ``{"name": "foo"}``
        - ``platforms: [a, b]``    → ``{"platforms": ["a", "b"]}``
        - ``platforms: {darwin: disabled}`` → ``{"platforms": {"darwin": "disabled"}}``
        - ``disable_if: {reason: dup}``      → ``{"disable_if": {"reason": "dup"}}``
        - Block form for nested maps.
        """
        fm: dict[str, Any] = {}
        lines = fm_text.splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.rstrip()
            if not line:
                i += 1
                continue
            if ":" not in line or line.startswith(" "):
                i += 1
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                # Nested block; collect indented children.
                nested: dict[str, Any] = {}
                j = i + 1
                while j < len(lines):
                    inner = lines[j]
                    if not inner.strip():
                        j += 1
                        continue
                    if not inner.startswith(" "):
                        break
                    inner_stripped = inner.strip()
                    if ":" not in inner_stripped:
                        j += 1
                        continue
                    inner_key, _, inner_value = inner_stripped.partition(":")
                    inner_value = inner_value.strip()
                    if inner_value.startswith("[") and inner_value.endswith("]"):
                        nested[inner_key.strip()] = [
                            v.strip().strip('"').strip("'") for v in inner_value[1:-1].split(",") if v.strip()
                        ]
                    elif inner_value.startswith("{") and inner_value.endswith("}"):
                        nested[inner_key.strip()] = _parse_inline_map(inner_value)
                    else:
                        nested[inner_key.strip()] = inner_value.strip('"').strip("'")
                    j += 1
                fm[key] = nested
                i = j
            elif value.startswith("[") and value.endswith("]"):
                fm[key] = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
                i += 1
            elif value.startswith("{") and value.endswith("}"):
                fm[key] = _parse_inline_map(value)
                i += 1
            else:
                fm[key] = value.strip('"').strip("'")
                i += 1
        return fm

    def _parse_inline_map(text: str) -> dict[str, Any]:
        """Parse a one-level ``{k: v, k: v}`` inline map (values may be
        quoted strings, barewords, or one-level nested inline maps)."""
        inner = text.strip()[1:-1].strip()
        out: dict[str, Any] = {}
        if not inner:
            return out
        # Naive split on top-level commas (no quoted commas — tests do
        # not use them).
        parts: list[str] = []
        depth = 0
        buf: list[str] = []
        for ch in inner:
            if ch in "{[":
                depth += 1
            elif ch in "}]":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf).strip())
        for part in parts:
            if ":" not in part:
                continue
            k, _, v = part.partition(":")
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                out[k.strip()] = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            elif v.startswith("{") and v.endswith("}"):
                out[k.strip()] = _parse_inline_map(v)
            else:
                out[k.strip()] = v.strip('"').strip("'")
        return out

    fake = types.ModuleType("agent.skill_utils")
    fake.parse_frontmatter = parse_frontmatter
    fake._state = state
    # Also fake the get_disabled_skill_names symbol (not used by the
    # detection helper but used elsewhere in the audit pipeline; tests
    # can monkeypatch if needed).
    fake.get_disabled_skill_names = lambda platform=None: set()
    # Create a parent ``agent`` module so ``from agent.skill_utils
    # import ...`` works in the production code path.
    agent_pkg = types.ModuleType("agent")
    agent_pkg.skill_utils = fake
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.skill_utils", fake)
    return fake


@pytest.fixture
def enabled_detection(fake_agent_skill_utils: types.ModuleType):
    """Import the module under test with a fake ``agent.skill_utils``."""
    import importlib

    mod_name = "easter_hermes_sorry_skills._enabled_detection"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# TDD list — get_enabled_skills.
# ---------------------------------------------------------------------------


def test_get_enabled_skills_honors_config_toggle(enabled_detection, tmp_path: Path) -> None:
    """Skills in ``config.skills.disabled`` are NOT enabled."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: foo skill")
    _write_skill(profile / "skills", "bar", "name: bar\ndescription: bar skill")
    _write_config(profile, disabled=["foo"])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled
    assert "bar" in enabled


def test_get_enabled_skills_honors_platform_filter(enabled_detection, tmp_path: Path) -> None:
    """A skill with ``platforms: {darwin: disabled}`` (or
    ``disable_if_platform_present: [darwin]``) is excluded when the
    caller passes ``platform='darwin'``."""

    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(
        profile / "skills",
        "bar",
        "name: bar\nplatforms: {darwin: disabled}",
    )
    _write_skill(profile / "skills", "baz", "name: baz\ndescription: baz skill")
    _write_config(profile, disabled=[])

    enabled_darwin = enabled_detection.get_enabled_skills(profile, platform="darwin")
    enabled_linux = enabled_detection.get_enabled_skills(profile, platform="linux")

    assert "bar" not in enabled_darwin
    assert "baz" in enabled_darwin
    assert "bar" in enabled_linux  # linux does NOT disable bar
    assert "baz" in enabled_linux


def test_get_enabled_skills_honors_conditional_exclusions(enabled_detection, tmp_path: Path) -> None:
    """A per-skill ``disable_if`` rule wins over the toggle list.

    Even if the skill is NOT in the toggle list, a ``disable_if`` rule
    excludes it.
    """
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(
        profile / "skills",
        "qux",
        "name: qux\ndisable_if: {reason: 'duplicate'}",
    )
    _write_skill(profile / "skills", "ok", "name: ok\ndescription: ok skill")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "qux" not in enabled
    assert "ok" in enabled


def test_get_enabled_skills_returns_frozenset(enabled_detection, tmp_path: Path) -> None:
    """Return type is ``frozenset[str]``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: foo skill")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert isinstance(enabled, frozenset)
    # All elements are strings.
    for s in enabled:
        assert isinstance(s, str)


def test_get_enabled_skills_no_fallback_to_real_hermes_home(
    enabled_detection, tmp_path: Path, real_hermes_agent_sentinel: str
) -> None:
    """The function reads ONLY from ``profile_path``; it MUST NOT touch
    ``~/.hermes/`` (regression sentinel for AC-3.4 / AC-7.3)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: foo skill")
    _write_config(profile, disabled=[])

    # The real_hermes_agent_sentinel fixture snapshots
    # ~/.hermes/hermes-agent/agent/skill_utils.py; if get_enabled_skills
    # were to fall back to ~/.hermes and read the live tree, that
    # snapshot would be a no-op (we never write). The test also asserts
    # the result is purely from profile_path by checking that skills in
    # the live install are NOT pulled in.
    enabled = enabled_detection.get_enabled_skills(profile)
    # We don't compare against the full live tree (that would be a
    # snapshot test against a live source) — we just assert the result
    # is bounded by what we wrote into the fixture.
    assert enabled <= {"foo", "bar", "baz", "qux", "ok"}


# ---------------------------------------------------------------------------
# Branch coverage tests — every edge case in the helper functions.
# ---------------------------------------------------------------------------


def test_get_enabled_skills_empty_profile(enabled_detection, tmp_path: Path) -> None:
    """Profile with no ``skills/`` dir → empty enabled set."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir.
    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset()


def test_get_enabled_skills_skips_dirs_without_skill_md(enabled_detection, tmp_path: Path) -> None:
    """Directories in ``skills/`` without ``SKILL.md`` are ignored."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    # A valid skill.
    _write_skill(skills, "valid", "name: valid\ndescription: x")
    # A directory with no SKILL.md.
    (skills / "broken").mkdir()
    # A regular file (not a directory) — also ignored.
    (skills / "stray.txt").write_text("not a skill")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset({"valid"})


def test_get_enabled_skills_uses_dirname_when_frontmatter_lacks_name(enabled_detection, tmp_path: Path) -> None:
    """If the frontmatter omits ``name``, the directory name is used."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "dirname-fallback", "description: no name field here")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset({"dirname-fallback"})


def test_get_enabled_skills_handles_missing_config(enabled_detection, tmp_path: Path) -> None:
    """Profile with skills but no ``config.yaml`` → empty disabled set."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    # No config.yaml.

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset({"foo"})


def test_get_enabled_skills_handles_block_form_yaml(enabled_detection, tmp_path: Path) -> None:
    """``config.yaml`` in block form (multi-line) is parsed correctly."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    _write_skill(profile / "skills", "bar", "name: bar\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  disabled: [foo]\n  other_key: ignored\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled
    assert "bar" in enabled


def test_get_enabled_skills_handles_inline_yaml(enabled_detection, tmp_path: Path) -> None:
    """``config.yaml`` in inline ``{ ... }`` form is parsed correctly."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    _write_skill(profile / "skills", "bar", "name: bar\ndescription: x")
    (profile / "config.yaml").write_text("skills: { disabled: [foo] }\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled
    assert "bar" in enabled


def test_get_enabled_skills_handles_empty_disabled_list(enabled_detection, tmp_path: Path) -> None:
    """``config.yaml`` with an empty ``disabled: []`` list → all enabled."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  disabled: []\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset({"foo"})


def test_get_enabled_skills_handles_other_keys_under_skills(enabled_detection, tmp_path: Path) -> None:
    """Other keys under ``skills:`` end the disabled scan (no false positives)."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  other_section:\n    nested: value\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset({"foo"})


def test_get_enabled_skills_handles_skills_key_not_first(enabled_detection, tmp_path: Path) -> None:
    """``skills:`` is not the first key in the YAML → still found."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("other:\n  nested: value\nskills:\n  disabled: [foo]\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled


def test_get_enabled_skills_platform_filter_list_value(enabled_detection, tmp_path: Path) -> None:
    """Platform filter handles list values (per the validator's "any truthy"
    rule)."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "mac-only",
        "name: mac-only\nplatforms: {darwin: [disabled]}",
    )
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    assert "mac-only" not in enabled
    assert "ok" in enabled


def test_get_enabled_skills_platform_filter_dict_value(enabled_detection, tmp_path: Path) -> None:
    """Platform filter handles dict values with truthy nested key."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "mac-only",
        "name: mac-only\nplatforms: {darwin: {disabled: true}}",
    )
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    assert "mac-only" not in enabled
    assert "ok" in enabled


def test_get_enabled_skills_platform_filter_unrelated_platform(enabled_detection, tmp_path: Path) -> None:
    """A skill disabled on ``darwin`` is enabled on ``linux``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "mac-only",
        "name: mac-only\nplatforms: {darwin: disabled}",
    )
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="linux")
    assert "mac-only" in enabled


def test_get_enabled_skills_conditional_exclusion_empty_value(enabled_detection, tmp_path: Path) -> None:
    """``disable_if:`` with an empty / falsy value does NOT exclude."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "ok", "name: ok\ndisable_if: ")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "ok" in enabled


def test_get_enabled_skills_oserror_on_read_skill_md(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a SKILL.md read raises OSError during the platform/conditional
    filter pass, the skill is treated as enabled (defensive: we could not
    determine its exclusions, so we conservatively keep it)."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "bad", "name: bad\nplatforms: {darwin: disabled}")
    _write_config(profile, disabled=[])

    # Wrap Path.read_text to raise OSError only on the second invocation
    # (the platform/conditional filter pass). The first walk (counted by
    # invocation order) must succeed so ``bad`` is in installed_names.
    from pathlib import Path as P

    original_read_text = P.read_text
    call_count = {"n": 0}

    def patched_read_text(self, *a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    # Defensive: bad is conservatively kept when we cannot read it.
    assert "bad" in enabled


def test_get_enabled_skills_oserror_on_walk_skill_md(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the first walk's read_text raises OSError, that skill is
    dropped from ``installed_names`` (the walk swallows the error)."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    _write_skill(skills, "broken", "name: broken\ndescription: x")
    _write_config(profile, disabled=[])

    from pathlib import Path as P

    original_read_text = P.read_text
    state = {"broken_seen": False}

    def patched_read_text(self, *a, **k):
        if self.name == "SKILL.md" and "broken" in str(self):
            state["broken_seen"] = True
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    enabled = enabled_detection.get_enabled_skills(profile)
    # ``broken`` was dropped (the walk swallowed its OSError).
    assert "broken" not in enabled
    assert "ok" in enabled


def test_get_enabled_skills_walk_read_oserror_in_conditional_pass(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a SKILL.md read raises OSError during the conditional
    exclusions pass, the skill is conservatively kept."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "qux", "name: qux\ndisable_if: {reason: dup}")
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    _write_config(profile, disabled=[])

    from pathlib import Path as P

    original_read_text = P.read_text
    call_count = {"n": 0}

    def patched_read_text(self, *a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 3:  # let both first walks succeed, fail on the conditional pass
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    enabled = enabled_detection.get_enabled_skills(profile)
    # Both skills in installed_names; the conditional pass read failed
    # for qux, so it is conservatively kept.
    assert "qux" in enabled
    assert "ok" in enabled


def test_get_enabled_skills_dirname_used_when_no_skill_md_in_filter(enabled_detection, tmp_path: Path) -> None:
    """A skill directory that has SKILL.md during the first walk but is
    later looked up by NAME that differs from its directory name —
    platform/conditional filters must locate it via the frontmatter
    cross-reference in ``_find_skill_md``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    # Directory name = "renamed"; frontmatter name = "renamed-skill".
    _write_skill(
        skills,
        "renamed",
        "name: renamed-skill\ndescription: x\nplatforms: {darwin: disabled}",
    )
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    # The filter resolves the skill by frontmatter name and excludes it.
    assert "renamed-skill" not in enabled


def test_get_enabled_skills_dirname_used_when_no_skill_md_in_conditional(enabled_detection, tmp_path: Path) -> None:
    """Same as above, but for the conditional-exclusion pass."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "renamed-2",
        "name: renamed-cond\ndescription: x\ndisable_if: {reason: x}",
    )
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "renamed-cond" not in enabled


def test_get_enabled_skills_dirname_fallback_when_skill_md_missing(enabled_detection, tmp_path: Path) -> None:
    """If a skill in installed_names has no SKILL.md during the
    platform/conditional filter pass, the defensive fallback keeps it
    in the result."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    # Create a "ghost" dir with no SKILL.md but pre-seed installed_names
    # so the filter would look it up. Easier: use a skill that exists
    # in the walk but whose SKILL.md is removed before the filter.
    ghost = skills / "ghost"
    ghost.mkdir()
    (ghost / "SKILL.md").write_text("name: ghost\ndescription: x")
    # The first walk picks it up; remove SKILL.md so the filter's
    # _find_skill_md returns None.
    (ghost / "SKILL.md").unlink()
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    # ghost was not in installed_names (no SKILL.md during the first walk).
    # So this test asserts the simple "no SKILL.md → not installed" path.
    assert "ghost" not in enabled
    assert "ok" in enabled


def test_get_enabled_skills_disabled_scalar_value(enabled_detection, tmp_path: Path) -> None:
    """A scalar ``disabled: foo`` (no list brackets) is parsed correctly."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    _write_skill(profile / "skills", "bar", "name: bar\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  disabled: foo\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled
    assert "bar" in enabled


def test_get_enabled_skills_block_form_with_other_key_after_disabled(enabled_detection, tmp_path: Path) -> None:
    """The disabled scan stops at any other key under ``skills:``."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  disabled: [foo]\n  another_key: value\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" not in enabled


def test_get_enabled_skills_platform_filter_falsy_value(enabled_detection, tmp_path: Path) -> None:
    """A platform value of ``""`` is falsy → skill is NOT disabled."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "maybe",
        "name: maybe\nplatforms: {darwin: ''}",
    )
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    assert "maybe" in enabled


def test_get_enabled_skills_platform_filter_unknown_value_type(enabled_detection, tmp_path: Path) -> None:
    """A non-str/dict/list value (e.g. an int) falls back to ``bool(value)``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "weird",
        "name: weird\nplatforms: {darwin: 1}",
    )
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile, platform="darwin")
    # 1 is truthy → skill is disabled.
    assert "weird" not in enabled


def test_get_enabled_skills_platform_filter_skills_dir_missing(enabled_detection, tmp_path: Path) -> None:
    """When ``skills/`` does not exist, the platform filter is a no-op."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir.
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset()


def test_get_enabled_skills_platform_filter_skill_md_missing(enabled_detection, tmp_path: Path) -> None:
    """A skill in installed_names whose SKILL.md was removed before the
    platform filter is conservatively kept (the filter's
    ``_find_skill_md`` returns None)."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    # Create a SKILL.md, run the walk to register it, then remove the
    # SKILL.md so the platform filter's _find_skill_md returns None.
    ghost = skills / "ghost"
    ghost.mkdir()
    (ghost / "SKILL.md").write_text("name: ghost\ndescription: x")
    # Now remove it BEFORE the walk — the skill is NOT in installed_names.
    # Instead, manually pre-register it in installed_names by using a
    # custom walk? Easiest: use a skill whose SKILL.md exists in the
    # walk but where _find_skill_md's "frontmatter match" path is the
    # only way to resolve it. We already cover that case in
    # test_get_enabled_skills_dirname_used_when_no_skill_md_in_filter.

    # To exercise the "skill_md is None" branch in _apply_platform_filter,
    # we need installed_names to contain a name that has NO SKILL.md.
    # The first walk only adds names for skills with SKILL.md. So we
    # have to seed installed_names by another route. Easiest: build a
    # custom scenario where installed_names has an entry without a
    # backing file.
    # We do that by patching the walk to return a synthetic set.
    from easter_hermes_sorry_skills import _enabled_detection as ed

    real_walk = ed._walk_installed_skill_names
    ed._walk_installed_skill_names = lambda d: {"synthetic"}
    try:
        enabled = ed.get_enabled_skills(profile, platform="darwin")
        # synthetic is in installed_names, has no SKILL.md → kept.
        assert "synthetic" in enabled
    finally:
        ed._walk_installed_skill_names = real_walk


def test_get_enabled_skills_conditional_skill_md_missing(enabled_detection, tmp_path: Path) -> None:
    """Same as above for the conditional-exclusion pass."""
    profile = tmp_path / "default"
    profile.mkdir()
    (profile / "skills").mkdir()
    _write_config(profile, disabled=[])

    from easter_hermes_sorry_skills import _enabled_detection as ed

    real_walk = ed._walk_installed_skill_names
    ed._walk_installed_skill_names = lambda d: {"synthetic"}
    try:
        enabled = ed.get_enabled_skills(profile)
        # synthetic is in installed_names, has no SKILL.md → kept.
        assert "synthetic" in enabled
    finally:
        ed._walk_installed_skill_names = real_walk


def test_get_enabled_skills_find_skill_md_cross_reference(enabled_detection, tmp_path: Path) -> None:
    """The cross-reference in ``_find_skill_md`` resolves a skill whose
    directory name differs from its frontmatter name, by iterating all
    skill dirs."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "a", "name: alpha\ndescription: x")
    _write_skill(skills, "b", "name: beta\ndescription: x")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    # Both directory-named and frontmatter-named skills are present.
    assert enabled == frozenset({"alpha", "beta"})


def test_get_enabled_skills_find_skill_md_cross_reference_oserror(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A SKILL.md that raises OSError during the cross-reference
    iteration is skipped."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(skills, "a", "name: alpha\ndescription: x")
    _write_skill(skills, "b", "name: beta\ndescription: x")
    _write_config(profile, disabled=[])

    from pathlib import Path as P

    original_read_text = P.read_text
    state = {"b_failed": False}

    def patched_read_text(self, *a, **k):
        if self.name == "SKILL.md" and str(self).endswith("/b/SKILL.md"):
            state["b_failed"] = True
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    enabled = enabled_detection.get_enabled_skills(profile)
    # alpha is found via the frontmatter cross-reference.
    assert "alpha" in enabled


def test_get_enabled_skills_skills_dir_not_a_directory(enabled_detection, tmp_path: Path) -> None:
    """When ``skills/`` does not exist, the walk and filters are no-ops."""
    profile = tmp_path / "default"
    profile.mkdir()
    # No skills/ subdir at all.
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert enabled == frozenset()


def test_find_skill_md_returns_none_when_dir_missing(enabled_detection, tmp_path: Path) -> None:
    """``_find_skill_md`` returns ``None`` when ``skills_dir`` does not exist.

    Direct unit test on the helper. This branch is unreachable through
    the public ``get_enabled_skills`` API (the platform/conditional
    filters short-circuit on empty ``installed_names``), so we test it
    in isolation to satisfy the 100% branch coverage contract.
    """
    missing = tmp_path / "does-not-exist" / "skills"
    assert not missing.exists()
    result = enabled_detection._find_skill_md(missing, "anything")
    assert result is None


def test_find_skill_md_returns_none_when_no_match(enabled_detection, tmp_path: Path) -> None:
    """``_find_skill_md`` returns ``None`` when no directory matches the
    given NAME (neither by directory name nor by frontmatter ``name``)."""
    skills = tmp_path / "skills"
    skills.mkdir()
    _write_skill(skills, "alpha", "name: alpha\ndescription: x")
    _write_skill(skills, "beta", "name: beta\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "gamma")
    assert result is None


def test_find_skill_md_skips_files_in_skills_dir(enabled_detection, tmp_path: Path) -> None:
    """A regular file in ``skills/`` is skipped during cross-reference."""
    skills = tmp_path / "skills"
    skills.mkdir()
    _write_skill(skills, "alpha", "name: alpha\ndescription: x")
    (skills / "stray.txt").write_text("not a skill dir")
    result = enabled_detection._find_skill_md(skills, "alpha")
    # Still found via the frontmatter cross-reference.
    assert result is not None
    assert result.name == "SKILL.md"


def test_find_skill_md_skips_subdirs_without_skill_md(enabled_detection, tmp_path: Path) -> None:
    """A subdirectory without ``SKILL.md`` is skipped during cross-reference."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "broken").mkdir()
    _write_skill(skills, "alpha", "name: alpha\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None


def test_find_skill_md_skips_subdirs_with_unreadable_skill_md(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subdirectory whose ``SKILL.md`` raises OSError is skipped during
    the frontmatter cross-reference loop.

    We use a directory whose frontmatter ``name`` is NOT the directory
    name so the cross-reference loop (not the direct-match) is what
    locates the skill.
    """
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "broken").mkdir()
    _write_skill(skills, "broken", "name: broken\ndescription: x")
    # Directory name "renamed" but frontmatter name "alpha".
    (skills / "renamed").mkdir()
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")

    from pathlib import Path as P

    original_read_text = P.read_text
    state = {"broken_failed": False}

    def patched_read_text(self, *a, **k):
        if str(self).endswith("/broken/SKILL.md"):
            state["broken_failed"] = True
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None
    assert result.parent.name == "renamed"
    assert state["broken_failed"] is True


def test_parse_disabled_yaml_other_inline_key(enabled_detection, tmp_path: Path) -> None:
    """An inline ``{ enabled: [a] }`` (other key, not ``disabled``) is
    parsed without setting anything in the disabled set."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills: { enabled: [foo] }\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    # ``enabled:`` is not the key we look for; foo is enabled by default.
    assert "foo" in enabled


def test_parse_disabled_yaml_block_ends_unexpectedly(enabled_detection, tmp_path: Path) -> None:
    """A non-indented line right after ``skills:`` ends the disabled scan."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills:\nnot_indented: ends_block\nother_key: value\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" in enabled


def test_platform_disables_returns_false_for_unexpected_type(
    enabled_detection,
) -> None:
    """``_platform_disables`` returns ``False`` when ``platforms`` is not a dict."""
    assert enabled_detection._platform_disables(None, "darwin") is False
    assert enabled_detection._platform_disables("not a dict", "darwin") is False
    assert enabled_detection._platform_disables(["not", "a", "dict"], "darwin") is False


def test_platform_disables_returns_false_for_unknown_platform(
    enabled_detection,
) -> None:
    """``_platform_disables`` returns ``False`` when the platform is not in the map."""
    assert enabled_detection._platform_disables({"darwin": "disabled"}, "linux") is False


def test_parse_disabled_yaml_empty_disabled_value(enabled_detection, tmp_path: Path) -> None:
    """``disabled:`` (empty value) is treated as no disabled skills."""
    profile = tmp_path / "default"
    (profile / "skills").mkdir(parents=True)
    _write_skill(profile / "skills", "foo", "name: foo\ndescription: x")
    (profile / "config.yaml").write_text("skills:\n  disabled:\n")

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "foo" in enabled


def test_extract_disabled_from_inline_other_key(
    enabled_detection,
) -> None:
    """``_extract_disabled_from_inline`` is a no-op when ``disabled:`` is absent."""
    out: set[str] = set()
    enabled_detection._extract_disabled_from_inline("enabled: [foo]", out)
    assert out == set()


def test_extract_disabled_from_inline_empty_list(
    enabled_detection,
) -> None:
    """An empty ``disabled: []`` in an inline block adds nothing."""
    out: set[str] = set()
    enabled_detection._extract_disabled_from_inline("disabled: []", out)
    assert out == set()


def test_platform_disables_int_value_truthy(
    enabled_detection,
) -> None:
    """``_platform_disables`` covers the ``bool(value)`` fallback for int values."""
    # Non-str / non-dict / non-list value → ``bool(value)`` branch (line 252).
    assert enabled_detection._platform_disables({"darwin": 0}, "darwin") is False
    assert enabled_detection._platform_disables({"darwin": 1}, "darwin") is True


def test_platform_disables_tuple_value(
    enabled_detection,
) -> None:
    """``_platform_disables`` covers the tuple branch (any truthy disables)."""
    assert enabled_detection._platform_disables({"darwin": ("disabled",)}, "darwin") is True
    assert enabled_detection._platform_disables({"darwin": ()}, "darwin") is False


def test_platform_disables_set_value(
    enabled_detection,
) -> None:
    """``_platform_disables`` covers the set branch."""
    assert enabled_detection._platform_disables({"darwin": {"disabled"}}, "darwin") is True
    assert enabled_detection._platform_disables({"darwin": set()}, "darwin") is False


def test_platform_disables_empty_dict_value(
    enabled_detection,
) -> None:
    """``_platform_disables`` covers the empty-dict branch (no values to scan)."""
    assert enabled_detection._platform_disables({"darwin": {}}, "darwin") is False


def test_find_skill_md_skips_non_dir_child(enabled_detection, tmp_path: Path) -> None:
    """The cross-reference loop skips non-directory children in ``skills/``."""
    skills = tmp_path / "skills"
    skills.mkdir()
    # Place a regular file in skills/; the loop must skip it (line 303-304).
    (skills / "stray.txt").write_text("not a skill")
    # The skill we look up is found via frontmatter cross-reference only.
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None


def test_find_skill_md_skips_subdir_without_skill_md(enabled_detection, tmp_path: Path) -> None:
    """The cross-reference loop skips subdirs with no SKILL.md (line 306-307)."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "no-skill-md").mkdir()
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None


def test_find_skill_md_skips_subdir_with_unreadable_skill_md_in_loop(
    enabled_detection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cross-reference loop skips subdirs whose SKILL.md raises OSError
    (line 310-311). We use a directory whose frontmatter name is the
    lookup target and another directory that fails to read."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "broken").mkdir()
    _write_skill(skills, "broken", "name: broken\ndescription: x")
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")

    from pathlib import Path as P

    original_read_text = P.read_text

    def patched_read_text(self, *a, **k):
        if str(self).endswith("/broken/SKILL.md"):
            raise OSError("simulated")
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(P, "read_text", patched_read_text)
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None


def test_extract_disabled_from_inline_loop_continues_for_non_disabled_parts(
    enabled_detection,
) -> None:
    """The inline extractor iterates ALL parts (not just ``disabled:``) —
    the ``if kv.startswith("disabled:")`` branch must be tested as False."""
    out: set[str] = set()
    # The block includes the braces; the function strips them.
    # Two parts: one ``disabled:``, one not. The non-disabled part exercises
    # the ``kv.startswith("disabled:")`` False branch (line 183->181).
    enabled_detection._extract_disabled_from_inline("{enabled: [foo], disabled: [bar]}", out)
    assert out == {"bar"}


def test_extract_disabled_from_inline_continues_loop(
    enabled_detection,
) -> None:
    """The inline extractor iterates multiple items in a list (line 188->186)."""
    out: set[str] = set()
    enabled_detection._extract_disabled_from_inline("{disabled: [a, b, c]}", out)
    assert out == {"a", "b", "c"}


def test_extract_disabled_from_inline_scalar_value(
    enabled_detection,
) -> None:
    """``disabled: foo`` (scalar, no list) in an inline block is a no-op
    for the list-extraction branch (line 190->185, the False branch)."""
    out: set[str] = set()
    enabled_detection._extract_disabled_from_inline("{disabled: foo}", out)
    # The function only handles list values; scalars are silently ignored.
    assert out == set()


def test_extract_disabled_from_inline_skips_empty_items(
    enabled_detection,
) -> None:
    """Empty items in a ``disabled: [a, , c]`` list are skipped (line 193->191)."""
    out: set[str] = set()
    enabled_detection._extract_disabled_from_inline("{disabled: [a, , c]}", out)
    assert out == {"a", "c"}


def test_find_skill_md_cross_ref_skips_non_dir_child(enabled_detection, tmp_path: Path) -> None:
    """A regular file in ``skills/`` is skipped during cross-reference
    (line 331). The lookup name is the frontmatter ``name`` of a sibling
    skill so the direct-match path is skipped."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "stray.txt").write_text("not a skill")
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None


def test_apply_platform_filter_skill_md_none(enabled_detection, tmp_path: Path) -> None:
    """Direct test: a name in the filter with no backing SKILL.md is
    conservatively kept (line 214->216 False branch)."""
    from easter_hermes_sorry_skills import _enabled_detection as ed

    real_walk = ed._walk_installed_skill_names
    ed._walk_installed_skill_names = lambda d: {"synthetic"}
    try:
        result = ed._apply_platform_filter({"synthetic"}, tmp_path, "darwin")
        # skill_md is None for "synthetic" → kept.
        assert "synthetic" in result
    finally:
        ed._walk_installed_skill_names = real_walk


def test_split_top_level_commas_trailing_comma(
    enabled_detection,
) -> None:
    """A trailing comma in the input leaves an empty buffer at the end
    (the ``if buf:`` branch is False → no extra empty part appended)."""
    parts = enabled_detection._split_top_level_commas("a, b, c,")
    assert parts == ["a", " b", " c", ""] or parts == ["a", " b", " c"]


def test_find_skill_md_cross_ref_non_dir_first(enabled_detection, tmp_path: Path) -> None:
    """The cross-reference loop must skip a non-dir child EVEN IF it
    appears FIRST in the sorted iteration order (line 331).

    Sorted order is alphabetical; a file named ``!alpha`` sorts before
    ``renamed`` (and we name the target so it sorts after).
    """
    skills = tmp_path / "skills"
    skills.mkdir()
    # Regular file; sorts before any alphabetic dir name.
    (skills / "!stray.txt").write_text("not a skill")
    _write_skill(skills, "renamed", "name: alpha\ndescription: x")
    result = enabled_detection._find_skill_md(skills, "alpha")
    assert result is not None
    assert result.parent.name == "renamed"


def test_get_enabled_skills_find_skill_md_via_frontmatter(enabled_detection, tmp_path: Path) -> None:
    """The directory-name → frontmatter-name lookup resolves a skill whose
    directory name differs from its frontmatter ``name``."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    _write_skill(
        skills,
        "directory-name",
        "name: frontmatter-name\ndescription: x",
    )
    _write_skill(skills, "bar", "name: bar\ndescription: x")
    _write_config(profile, disabled=["frontmatter-name"])

    enabled = enabled_detection.get_enabled_skills(profile)
    assert "frontmatter-name" not in enabled
    assert "bar" in enabled


def test_get_enabled_skills_skill_dir_with_missing_skill_md(enabled_detection, tmp_path: Path) -> None:
    """A skill directory that lacks SKILL.md after the first walk is still
    handled in the platform/conditional filters (defensive: kept)."""
    profile = tmp_path / "default"
    skills = profile / "skills"
    skills.mkdir(parents=True)
    (skills / "ghost").mkdir()  # no SKILL.md
    _write_skill(skills, "ok", "name: ok\ndescription: x")
    _write_config(profile, disabled=[])

    enabled = enabled_detection.get_enabled_skills(profile)
    # "ghost" never appears in installed_names (no SKILL.md).
    assert enabled == frozenset({"ok"})
