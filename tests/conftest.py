"""tests/conftest.py — shared fixtures for the easter-hermes-sorry-skills-plugin test suite.

Merged conftest (Phase 7 / PR #5): combines:
  - main's hermes_home / hermes_checkout / skill_creator_home / real_hermes_agent_sentinel
  - branch's SKILL_UTILS_PATCHED / SKILL_UTILS_BODY /
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


# ---------------------------------------------------------------------------
# Pre-register ``hermes_cli.profiles`` stub so ``from hermes_cli.profiles
# import ProfileInfo`` (used by ``cli_profiles.py`` at module load time)
# succeeds during test collection, BEFORE any per-test ``installed`` fixture
# monkey-patches a richer substitute. The test fixture will overwrite this
# with a fake that also includes ``list_profiles``.
# ---------------------------------------------------------------------------


def _ensure_hermes_cli_profiles_stub() -> None:
    """Register a minimal ``hermes_cli`` package + ``hermes_cli.profiles``
    + ``hermes_cli.skills_config`` modules if absent.

    The hermes_cli package is not installed in the test environment; tests
    that need it install fakes via the ``installed`` fixture. However,
    ``cli_profiles.py`` performs ``from hermes_cli.profiles import
    ProfileInfo`` and ``from hermes_cli.skills_config import
    save_disabled_skills`` at module load (so the types are bound for
    ``TYPE_CHECKING`` and runtime annotations), which happens at test
    collection — before any fixture can run. We pre-register stubs here
    that expose ``ProfileInfo`` as a permissive ``object`` subclass with
    the three fields the source code references (name, path, is_default)
    and ``save_disabled_skills`` as a no-op.
    """
    import types

    if "hermes_cli" not in sys.modules:
        hermes_cli_mod = types.ModuleType("hermes_cli")
        hermes_cli_mod.__path__ = []  # mark as package
        sys.modules["hermes_cli"] = hermes_cli_mod

    hermes_cli_mod = sys.modules["hermes_cli"]

    if "hermes_cli.profiles" not in sys.modules:

        class _StubProfileInfo:
            """Minimal stand-in for ``hermes_cli.profiles.ProfileInfo``."""

            __slots__ = ("name", "path", "is_default")

        profiles_stub = types.ModuleType("hermes_cli.profiles")
        profiles_stub.ProfileInfo = _StubProfileInfo
        profiles_stub.list_profiles = lambda: []
        sys.modules["hermes_cli.profiles"] = profiles_stub
        hermes_cli_mod.profiles = profiles_stub

    if "hermes_cli.skills_config" not in sys.modules:
        skills_config_stub = types.ModuleType("hermes_cli.skills_config")
        skills_config_stub.save_disabled_skills = lambda *_a, **_kw: None
        sys.modules["hermes_cli.skills_config"] = skills_config_stub
        hermes_cli_mod.skills_config = skills_config_stub


_ensure_hermes_cli_profiles_stub()


def _ensure_agent_stub() -> None:
    """Register a minimal ``agent`` + ``agent.skill_utils`` module if absent.

    ``cli_profiles.py`` performs ``from agent.skill_utils import
    get_disabled_skill_names`` at module load (the unused-import silencer
    is mandated by the test contract which greps the source). Without
    this stub the import fails at test collection time, before any
    per-test fixture can run.
    """
    import types

    if "agent.skill_utils" in sys.modules:
        return
    agent_mod = sys.modules.get("agent")
    if agent_mod is None:
        agent_mod = types.ModuleType("agent")
        sys.modules["agent"] = agent_mod

    skill_utils = types.ModuleType("agent.skill_utils")

    def get_disabled_skill_names(*_args: object, **_kwargs: object) -> list[str]:
        return []

    skill_utils.get_disabled_skill_names = get_disabled_skill_names
    sys.modules["agent.skill_utils"] = skill_utils
    agent_mod.skill_utils = skill_utils


_ensure_agent_stub()


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
    for i in range(1, 677):
        lines.append(f"# padding line {i}\n")
    lines.append(SKILL_UTILS_BODY)
    return "".join(lines)


SKILL_UTILS_PATCHED = _build_skill_utils_padded()


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
    after laying down the padded SKILL_UTILS_PATCHED file AND the 6-file
    MINIMAL_HERMES_FILES layout. Both main-tests AND branch-tests can use it.
    """
    checkout = hermes_home
    (checkout / "agent").mkdir(parents=True, exist_ok=True)
    (checkout / "tools").mkdir(parents=True, exist_ok=True)
    (checkout / "hermes_cli").mkdir(parents=True, exist_ok=True)
    (checkout / "website" / "docs" / "user-guide" / "features").mkdir(parents=True, exist_ok=True)
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
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
