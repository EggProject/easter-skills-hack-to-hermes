"""tests/conftest.py — shared fixtures for the hermes-skill-creator-plugin test suite.

The headline invariant is the @assert_hermes_agent_untouched decorator: any test
that resolves `~/.hermes/hermes-agent` is automatically skipped if the path
would be live, so the plugin (and its migration scripts) can never accidentally
mutate the user's real Hermes install.

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

import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

import pytest

P = ParamSpec("P")
R = TypeVar("R")

# Default sentinel path: the operator's live Hermes install. Tests must NEVER
# write here. The decorator resolves HERMES_HOME lazily so that monkeypatched
# env vars set inside a fixture are honored at call time.
_LIVE_HERMES_AGENT = Path("~/.hermes/hermes-agent").expanduser()


def _resolve_hermes_home() -> Path:
    """Resolve HERMES_HOME from the current os.environ (post-monkeypatch)."""
    return Path(os.environ.get("HERMES_HOME", "~/.hermes/hermes-agent")).expanduser()


# Anchor for the live Hermes install. Tests must NEVER write here.
HERMES_HOME = _resolve_hermes_home()


def assert_hermes_agent_untouched(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: skip the test if `HERMES_HOME` resolves to a live, writable path.

    Inside a tmp_path fixture, HERMES_HOME is monkey-patched to a tmp subdir,
    so tests pass through. If a test resolves the real `~/.hermes/hermes-agent`
    (i.e. HERMES_HOME was NOT monkey-patched), pytest.skip the test.

    The sentinel check reads os.environ lazily so monkeypatch.setenv inside
    a fixture is observed at call time.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # The sentinel: if HERMES_HOME still points at the real ~/.hermes/hermes-agent,
        # the test is touching the live install and must be skipped.
        current = _resolve_hermes_home()
        if current == _LIVE_HERMES_AGENT and current.exists():
            pytest.skip(
                f"refusing to run {func.__name__!r}: "
                f"HERMES_HOME={current} resolves to the live install. "
                "Use the hermes_home / hermes_checkout fixture to redirect to tmp_path."
            )
        return func(*args, **kwargs)

    return wrapper


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a hermes_home rooted inside tmp_path; redirect HERMES_HOME env var."""
    fake = tmp_path / "hermes-home"
    fake.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(fake))
    return fake


@pytest.fixture
def hermes_checkout(hermes_home: Path) -> Path:
    """A 6-file synthetic Hermes checkout inside the hermes_home fixture."""
    return seed_minimal(hermes_home)


@pytest.fixture
def skill_creator_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HERMES_HOME rooted inside tmp_path with skills/ and profiles/ subdirs.

    Used by E-skill's installer tests so the installer can write to a
    tmp_path HERMES_HOME without ever touching the live install. Mirrors the
    E-skill ownership of this fixture (see 26525c4:tests/conftest.py).
    """
    home = tmp_path / "hermes-skill-creator-home"
    (home / "skills").mkdir(parents=True)
    (home / "profiles").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


# Minimal 6-file synthetic Hermes checkout, suitable for migration tests.
MINIMAL_HERMES_FILES: dict[str, str] = {
    "pyproject.toml": "[project]\nname = 'hermes-agent'\nversion = '0.0.0'\n",
    "README.md": "# hermes-agent (synthetic fixture)\n",
    "src/hermes_agent/__init__.py": "",
    "src/hermes_agent/cli.py": "def main() -> None: pass\n",
    "src/hermes_agent/skills.py": "SKILL_CAP = 12\n",
    "skills/.gitkeep": "",
}


def seed_minimal(root: Path) -> Path:
    """Materialize the 6-file synthetic Hermes checkout under `root`. Returns root."""
    for rel, content in MINIMAL_HERMES_FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def hermes_subprocess_env() -> dict[str, str]:
    """Return a child-process env that strips HERMES_SESSION without popping it
    from the parent process. Owned by E-skill (see _subprocess.py).

    Placeholder: the real implementation is owned by E-skill. The contract here
    is that the parent process's HERMES_SESSION is NEVER touched via os.environ.pop.
    """
    env = os.environ.copy()
    env.pop("HERMES_SESSION", None)
    return env


__all__ = [
    "HERMES_HOME",
    "assert_hermes_agent_untouched",
    "hermes_home",
    "hermes_checkout",
    "skill_creator_home",
    "seed_minimal",
    "hermes_subprocess_env",
    "MINIMAL_HERMES_FILES",
]
