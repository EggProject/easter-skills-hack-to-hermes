"""tests/conftest.py — shared fixtures for the easter-hermes-sorry-skills-plugin test suite.

Merged conftest (Phase 7 / PR #5): combines:
  - main's hermes_home / hermes_checkout / skill_creator_home / real_hermes_agent_sentinel
  - branch's SKILL_UTILS_PATCHED / SKILL_UTILS_BODY / PROMPT_BUILDER_PATCHED /
    BACKGROUND_REVIEW_PATCHED /
    worktree / frozen_time / assert_hermes_agent_untouched (function)
  - hermes_checkout is overridden to lay down the padded branch content
    inside main's hermes_home so both main-tests AND branch-tests pass.

TDD test cases for this module:
  test_assert_hermes_agent_untouched_skips_when_path_live
  test_assert_hermes_agent_untouched_runs_when_path_inside_tmp
  test_hermes_home_fixture_resolves_under_tmp
  test_hermes_checkout_fixture_provides_a_6_file_synthetic_repo
  test_seed_minimal_creates_known_layout
  test_hermes_subprocess_env_never_pops_hermes_session
  test_decorator_preserves_test_return_value
  test_decorator_propagates_assertion_errors
"""

from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Generator
from pathlib import Path
from typing import ParamSpec, TypeVar

import pytest

from easter_hermes_sorry_skills._safety import assert_hermes_agent_untouched
from tests.fixtures.minimal_hermes.seed_minimal import (
    MINIMAL_HERMES_FILES,
    seed_minimal,
)

P = ParamSpec("P")
R = TypeVar("R")

# ensure src/ is on sys.path even when pytest is invoked from a different cwd
_SRC = Path(__file__).resolve().parent.parent / "src"
# Always ensure src/ is at the front of sys.path. Idempotent: if it's already
# there this is a no-op move; if not, it gets prepended.
sys.path = [p for p in sys.path if p != str(_SRC)]
sys.path.insert(0, str(_SRC))


# --- branch (workstream-C) padded anchor constants ------------------------

SKILL_UTILS_BODY = '''\
"""Skill utility helpers (test fixture stand-in for agent/skill_utils.py)."""

from typing import Any, Dict


def extract_skill_description(frontmatter: Dict[str, Any]) -> str:
    """Extract a truncated description from parsed frontmatter."""
    raw_desc = frontmatter.get("description", "")
    if not raw_desc:
        return ""
    desc = str(raw_desc).strip().strip('\'"')
    if len(desc) > 60:
        return desc[:57] + "..."
    return desc
'''


def _build_skill_utils_padded() -> str:
    lines: list[str] = []
    for i in range(1, 705):
        lines.append(f"# padding line {i}\n")
    lines.append(SKILL_UTILS_BODY)
    return "".join(lines)


SKILL_UTILS_PATCHED = _build_skill_utils_padded()


PROMPT_BUILDER_BODY = '''\
"""System prompt assembly -- identity, platform hints, skills index, context files."""

# --- MEMORY_GUIDANCE (E2 anchor is L158) ---
MEMORY_GUIDANCE = (
    "If you've discovered a new way to do something, "
    "solved a problem that could be "
    "necessary later, save it as a skill with the skill tool.\\n"
    ")  # end MEMORY_GUIDANCE
'''


def _build_prompt_builder_padded() -> str:
    lines: list[str] = []
    # AC-2.8: L1 docstring anchors E0 (which inserts the
    # ``SKILL_CREATOR_CONSULT_RULE`` definition immediately after).
    # Real Hermes's ``prompt_builder.py`` already has a docstring at L1
    # and the E1/E2 anchors at L179/L158 (E3 was removed 2026-06-23), so the padding
    # below preserves those line numbers (the fixture mirrors the
    # real layout: docstring + blank + padding + anchors).
    lines.append('"""System prompt assembly -- identity, platform hints, skills index, context files.\n')
    lines.append("\n")
    for i in range(1, 156):
        lines.append(f"# padding {i}\n")
    lines.append('    "necessary later, save it as a skill with the skill tool.\\n"\n')
    for i in range(159, 179):
        lines.append(f"# padding {i}\n")
    lines.append('    "Skills that aren\'t maintained become liabilities."\n')
    for i in range(180, 1421):
        lines.append(f"# padding {i}\n")
    # E3 anchor (L1421) was removed 2026-06-23 — the loop below still
    # pads every line individually to preserve the fixture's total
    # line count.
    for i in range(1422, 1440):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


PROMPT_BUILDER_PATCHED = _build_prompt_builder_padded()


BACKGROUND_REVIEW_BODY = '''\
"""Background memory/skill review — fork the agent to evaluate the turn."""
'''


def _build_background_review_padded() -> str:
    lines: list[str] = []
    # AC-2.8: L1 docstring anchors E4b. Real Hermes's
    # ``background_review.py`` already has a docstring at L1 and the
    # E4/E5 anchors at L230/L317, so the padding below preserves those
    # line numbers (mirrors the real layout: docstring + blank +
    # padding + anchors).
    lines.append('"""Background memory/skill review — fork the agent to evaluate the turn.\n')
    lines.append("\n")
    for i in range(1, 228):
        lines.append(f"# padding {i}\n")
    lines.append('    "session artifact. If the proposed name only makes sense for "\n')
    lines.append("    \"today's task, it's wrong — fall back to (1), (2), or (3).\n\n")
    lines.append('"\n')
    lines.append('    "User-preference embedding (important): when the user expressed a "\n')
    for i in range(233, 315):
        lines.append(f"# padding {i}\n")
    lines.append('    "artifact. If the name only fits today\'s task, fall back to (1), "\n')
    lines.append('    "(2), or (3).\n\n')
    lines.append('"\n')
    lines.append('    "User-preference embedding: when the user complains about how "\n')
    for i in range(320, 350):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


BACKGROUND_REVIEW_PATCHED = _build_background_review_padded()


# --- main (B-plugin) fixtures ---------------------------------------------

# Default sentinel path: the operator's live Hermes install. Tests must NEVER
# write here. The decorator resolves HERMES_HOME lazily so that monkeypatched
# env vars set inside a fixture are honored at call time.
_LIVE_HERMES_AGENT = Path("~/.hermes/hermes-agent").expanduser()


def _resolve_hermes_home() -> Path:
    """Resolve HERMES_HOME from the current os.environ (post-monkeypatch)."""
    return Path(os.environ.get("HERMES_HOME", "~/.hermes/hermes-agent")).expanduser()


# Anchor for the live Hermes install. Tests must NEVER write here.
HERMES_HOME = _resolve_hermes_home()


def assert_hermes_agent_untouched_sentinel(pre: str | None) -> None:
    """Sentinel: assert live install byte-identical.

    Function-form companion to the decorator exported by the plugin package.
    Currently unused by the test suite (the decorator form is used), but kept
    in __all__ for external consumers that need a callable form. When ``pre``
    is provided we verify the post-install hash matches; when ``pre`` is
    ``None`` the sentinel is a no-op (no live install to guard).
    """
    if pre is None:
        return
    sentinel_path = Path("~/.hermes/hermes-agent/agent/skill_utils.py").expanduser()
    if not sentinel_path.is_file():
        return
    post_hash = hashlib.sha256(sentinel_path.read_bytes()).hexdigest()
    assert post_hash == pre, f"HERMES AGENT LIVE INSTAL MUTATED! pre={pre} post={post_hash}"


@pytest.fixture
def real_hermes_agent_sentinel(request: pytest.FixtureRequest) -> str:
    """Sentinel: verify ``~/.hermes/hermes-agent/agent/skill_utils.py`` is
    NOT mutated by the test.

    Returns an opaque string token so the test can keep the linter quiet.
    """
    return _real_hermes_agent_sentinel_impl(request)


def _real_hermes_agent_sentinel_impl(request: pytest.FixtureRequest) -> str:
    """Implementation factored out for direct unit testability."""
    sentinel_path = Path("~/.hermes/hermes-agent/agent/skill_utils.py").expanduser()
    if not sentinel_path.is_file():
        # No live install — sentinel is a no-op for this run.
        return _no_live_install_sentinel()
    pre_hash = hashlib.sha256(sentinel_path.read_bytes()).hexdigest()
    _install_sentinel_finalizer(request, sentinel_path, pre_hash)
    return "sentinel-ok"


def _no_live_install_sentinel() -> str:
    """Return the no-live-install sentinel token."""
    return "sentinel-no-live-install"


def _install_sentinel_finalizer(
    request: pytest.FixtureRequest,
    sentinel_path: Path,
    pre_hash: str,
) -> None:
    """Register a finalizer that checks the live install was not mutated."""

    def _check() -> None:
        if not sentinel_path.is_file():
            return
        post_hash = hashlib.sha256(sentinel_path.read_bytes()).hexdigest()
        # fmt: off
        assert (
            post_hash == pre_hash
        ), f"{sentinel_path} was modified by the test (pre={pre_hash[:12]}, post={post_hash[:12]})"
        # fmt: on

    request.addfinalizer(_check)
    return "sentinel-ok"


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a hermes_home rooted inside tmp_path; redirect HERMES_HOME env var."""
    fake = tmp_path / "hermes-home"
    fake.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    return fake


@pytest.fixture
def hermes_checkout(hermes_home: Path) -> Generator[Path]:
    """Synthetic Hermes checkout for tests.

    Returns `hermes_home` itself (per F-meta design: hermes_checkout == hermes_home)
    after laying down the padded branch anchor files
    (SKILL_UTILS_PATCHED, etc.) AND the 6-file MINIMAL_HERMES_FILES layout.
    Both main-tests AND branch-tests can use it.
    """
    checkout = hermes_home
    (checkout / "agent").mkdir(parents=True, exist_ok=True)
    (checkout / "hermes_cli").mkdir(parents=True, exist_ok=True)
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    (checkout / "agent" / "prompt_builder.py").write_text(PROMPT_BUILDER_PATCHED, encoding="utf-8")
    (checkout / "agent" / "background_review.py").write_text(BACKGROUND_REVIEW_PATCHED, encoding="utf-8")
    # Lay down the 6-file MINIMAL_HERMES_FILES layout (idempotent — seed_minimal
    # overwrites existing files).
    seed_minimal(checkout)
    yield checkout


@pytest.fixture
def skill_creator_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HERMES_HOME rooted inside tmp_path with skills/ and profiles/ subdirs."""
    home = tmp_path / "hermes-skill-creator-home"
    (home / "skills").mkdir(parents=True)
    (home / "profiles").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


# --- branch fixtures ------------------------------------------------------


@pytest.fixture
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    return "2026-06-17T00:00:00Z"


@pytest.fixture
def worktree(tmp_path: Path) -> Generator[Path]:
    """A bare tmp worktree root used as a scratch output directory in tests."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    yield wt


def hermes_subprocess_env() -> dict[str, str]:
    """Return a child-process env that strips HERMES_SESSION without popping it
    from the parent process."""
    env = os.environ.copy()
    env.pop("HERMES_SESSION", None)
    return env


__all__ = [
    "HERMES_HOME",
    "SKILL_UTILS_PATCHED",
    "SKILL_UTILS_BODY",
    "PROMPT_BUILDER_PATCHED",
    "BACKGROUND_REVIEW_PATCHED",
    "assert_hermes_agent_untouched",
    "assert_hermes_agent_untouched_sentinel",
    "hermes_home",
    "hermes_checkout",
    "skill_creator_home",
    "frozen_time",
    "worktree",
    "seed_minimal",
    "hermes_subprocess_env",
    "MINIMAL_HERMES_FILES",
    "real_hermes_agent_sentinel",
]
