"""tests/conftest.py — shared fixtures for the hermes-skill-creator-plugin test suite.

Merged conftest (Phase 7 / PR #5): combines:
  - main's hermes_home / hermes_checkout / skill_creator_home / real_hermes_agent_sentinel
  - branch's SKILL_UTILS_PATCHED / SKILL_UTILS_BODY / PROMPT_BUILDER_PATCHED /
    BACKGROUND_REVIEW_PATCHED / SKILL_MANAGER_TOOL_PATCHED / SKILLS_DOC_BODY /
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

from hermes_skill_creator_plugin._safety import assert_hermes_agent_untouched
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
    """Register a minimal ``hermes_cli.profiles`` module if absent.

    The hermes_cli package is not installed in the test environment; tests
    that need it install fakes via the ``installed`` fixture. However,
    ``cli_profiles.py`` performs ``from hermes_cli.profiles import
    ProfileInfo`` at module load (so the type is bound for ``TYPE_CHECKING``
    and runtime annotations), which happens at test collection — before any
    fixture can run. We pre-register a stub here that exposes ``ProfileInfo``
    as a permissive ``object`` subclass with the three fields the source
    code references (name, path, is_default).
    """
    import types

    if "hermes_cli.profiles" in sys.modules:
        return
    hermes_cli_mod = sys.modules.get("hermes_cli")
    if hermes_cli_mod is None:
        hermes_cli_mod = types.ModuleType("hermes_cli")
        sys.modules["hermes_cli"] = hermes_cli_mod

    class _StubProfileInfo:
        """Minimal stand-in for ``hermes_cli.profiles.ProfileInfo``.

        Real ``ProfileInfo`` is a NamedTuple; tests may substitute either a
        NamedTuple or a dataclass instance. We accept any kwargs and expose
        the three attributes ``cli_profiles.py`` reads (``name``, ``path``,
        ``is_default``).
        """

        __slots__ = ("name", "path", "is_default")

    stub = types.ModuleType("hermes_cli.profiles")
    stub.ProfileInfo = _StubProfileInfo
    stub.list_profiles = lambda: []
    sys.modules["hermes_cli.profiles"] = stub
    hermes_cli_mod.profiles = stub


_ensure_hermes_cli_profiles_stub()


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


PROMPT_BUILDER_BODY = '''\
"""Prompt builder (test fixture stand-in for agent/prompt_builder.py)."""

# --- MEMORY_GUIDANCE (E2 anchor is L158) ---
MEMORY_GUIDANCE = (
    "If you've discovered a new way to do something, "
    "solved a problem that could be "
    "necessary later, save it as a skill with the skill tool.\\n"
    ")  # end MEMORY_GUIDANCE
'''


def _build_prompt_builder_padded() -> str:
    lines: list[str] = []
    for i in range(1, 158):
        lines.append(f"# padding {i}\n")
    lines.append('    "necessary later, save it as a skill with the skill tool.\\n"\n')
    for i in range(159, 179):
        lines.append(f"# padding {i}\n")
    lines.append('    "Skills that aren\'t maintained become liabilities."\n')
    for i in range(180, 1421):
        lines.append(f"# padding {i}\n")
    lines.append('            "After difficult/iterative tasks, offer to save as a skill. "\n')
    for i in range(1422, 1440):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


PROMPT_BUILDER_PATCHED = _build_prompt_builder_padded()


BACKGROUND_REVIEW_BODY = '''\
"""Background review (test fixture stand-in for agent/background_review.py)."""
'''


def _build_background_review_padded() -> str:
    lines: list[str] = []
    for i in range(1, 105):
        lines.append(f"# padding {i}\n")
    lines.append("    \"today's task, it's wrong — fall back to (1), (2), or (3).\\n\\n\"\n")
    for i in range(106, 192):
        lines.append(f"# padding {i}\n")
    lines.append('    "(2), or (3).\\n\\n"\n')
    for i in range(193, 220):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


BACKGROUND_REVIEW_PATCHED = _build_background_review_padded()


SKILL_MANAGER_TOOL_BODY = '''\
"""Skill manager (test fixture stand-in for tools/skill_manager_tool.py)."""
'''


def _build_skill_manager_tool_padded() -> str:
    lines: list[str] = []
    for i in range(1, 1099):
        lines.append(f"# padding {i}\n")
    lines.append("SKILL_MANAGE_SCHEMA = {\n")
    lines.append('    "name": "skill_manage",\n')
    lines.append('    "description": (\n')
    for i in range(1102, 1129):
        lines.append(f'        "padding line {i} of description. "\n')
    lines.append('        "pitfalls come up; pin only guards against irrecoverable loss."\n')
    lines.append("    ),\n")
    for i in range(1131, 1150):
        lines.append(f"# padding {i}\n")
    return "".join(lines)


SKILL_MANAGER_TOOL_PATCHED = _build_skill_manager_tool_padded()


SKILLS_DOC_BODY = """\
# Skills

## Agent-Managed Skills (skill_manage tool)

The agent can create, update, and delete its own skills via the
`skill_manage` tool. This is the agent's **procedural memory** — when it
figures out a non-trivial workflow, it saves the approach as a skill for
future reuse.

### When the Agent Creates Skills
"""


def _build_skills_doc_padded() -> str:
    lines: list[str] = []
    for i in range(1, 378):
        lines.append(f"<!-- padding {i} -->\n")
    lines.append("## Agent-Managed Skills (skill_manage tool)\n")
    lines.append("\n")
    lines.append(
        "The agent can create, update, and delete its own skills via the "
        "`skill_manage` tool. This is the agent's **procedural memory** — "
        "when it figures out a non-trivial workflow, it saves the approach "
        "as a skill for future reuse.\n"
    )
    return "".join(lines)


SKILLS_DOC_PATCHED = _build_skills_doc_padded()


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
        assert (
            post_hash == pre_hash
        ), f"{sentinel_path} was modified by the test (pre={pre_hash[:12]}, post={post_hash[:12]})"

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
    (checkout / "tools").mkdir(parents=True, exist_ok=True)
    (checkout / "hermes_cli").mkdir(parents=True, exist_ok=True)
    (checkout / "website" / "docs" / "user-guide" / "features").mkdir(parents=True, exist_ok=True)
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    (checkout / "agent" / "prompt_builder.py").write_text(PROMPT_BUILDER_PATCHED, encoding="utf-8")
    (checkout / "agent" / "background_review.py").write_text(BACKGROUND_REVIEW_PATCHED, encoding="utf-8")
    (checkout / "tools" / "skill_manager_tool.py").write_text(SKILL_MANAGER_TOOL_PATCHED, encoding="utf-8")
    (checkout / "website" / "docs" / "user-guide" / "features" / "skills.md").write_text(
        SKILLS_DOC_PATCHED, encoding="utf-8"
    )
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
    """A bare tmp worktree root for --emit-migration-note output."""
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
    "SKILL_MANAGER_TOOL_PATCHED",
    "SKILLS_DOC_BODY",
    "SKILLS_DOC_PATCHED",
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
