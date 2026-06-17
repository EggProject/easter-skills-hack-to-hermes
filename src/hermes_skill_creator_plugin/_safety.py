"""hermes_skill_creator_plugin/_safety.py — no-touch sentinel for the live Hermes install.

The decorator is a thin wrapper that compares the resolved HERMES_HOME to the
live `~/.hermes/hermes-agent` path and pytest.skip's the test if they match.

TDD test cases for this module:
  test_safety_module_exports
  test_current_hermes_home_reads_env
  test_decorator_passes_through_when_hermes_home_in_tmp
  test_decorator_skips_when_hermes_home_resolves_to_live
  test_decorator_preserves_test_return_value
  test_decorator_propagates_assertion_errors
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

# Anchor for the live Hermes install. Tests must NEVER write here.
_LIVE_HERMES_AGENT = Path("~/.hermes/hermes-agent").expanduser()


def _current_hermes_home() -> Path:
    """Resolve HERMES_HOME at CALL time (after monkeypatch)."""
    return Path(os.environ.get("HERMES_HOME", "~/.hermes/hermes-agent")).expanduser()


# Module-level convenience for non-test use.
HERMES_HOME = _current_hermes_home()


def assert_hermes_agent_untouched(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: skip the test if `HERMES_HOME` resolves to the live install.

    Inside a tmp_path fixture, HERMES_HOME is monkey-patched to a tmp subdir,
    so tests pass through. If a test resolves the real `~/.hermes/hermes-agent`
    (i.e. HERMES_HOME was NOT monkey-patched), pytest.skip the test.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if _current_hermes_home() == _LIVE_HERMES_AGENT and _LIVE_HERMES_AGENT.exists():
            import pytest as _pytest

            _pytest.skip(
                f"refusing to run {func.__name__!r}: "
                f"HERMES_HOME={_current_hermes_home()} resolves to the live install. "
                "Use the hermes_home / hermes_checkout fixture to redirect to tmp_path."
            )
        return func(*args, **kwargs)

    return wrapper


__all__ = ["assert_hermes_agent_untouched", "HERMES_HOME"]
