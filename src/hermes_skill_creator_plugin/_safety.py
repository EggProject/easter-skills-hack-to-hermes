"""hermes_skill_creator_plugin/_safety.py — no-touch sentinel for Hermes.

The decorator compares the resolved HERMES_HOME to the live
`~/.hermes/hermes-agent` path and pytest.skip's the test if they match.

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

Params = ParamSpec("Params")
Return = TypeVar("Return")

# Anchor for the live Hermes install. Tests must NEVER write here.
# Tests monkey-patch this attribute to a tmp_path.
_LIVE_HERMES_AGENT: Path = Path("~/.hermes/hermes-agent").expanduser()
DEFAULT_HERMES_AGENT = "~/.hermes/hermes-agent"

_SKIP_TEMPLATE = (
    "refusing to run {name!r}: HERMES_HOME={home} resolves to the live "
    "install. Use the hermes_home / hermes_checkout fixture to redirect "
    "to tmp_path."
)


def _current_hermes_home() -> Path:
    """Resolve HERMES_HOME at CALL time (after monkeypatch)."""
    return Path(os.environ.get("HERMES_HOME", DEFAULT_HERMES_AGENT)).expanduser()


# Module-level convenience for non-test use.
HERMES_HOME = _current_hermes_home()


def assert_hermes_agent_untouched(
    func: Callable[Params, Return],
) -> Callable[Params, Return]:
    """Decorator: skip the test if HERMES_HOME resolves to the live install.

    Inside a tmp_path fixture, HERMES_HOME is monkey-patched to a tmp
    subdir, so tests pass through. If a test resolves the real
    `~/.hermes/hermes-agent` (i.e. HERMES_HOME was NOT monkey-patched),
    pytest.skip the test.
    """

    @wraps(func)
    def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> Return:
        if (
            _current_hermes_home() == _LIVE_HERMES_AGENT
            and _LIVE_HERMES_AGENT.exists()
        ):
            import pytest as _pytest

            _pytest.skip(
                _SKIP_TEMPLATE.format(
                    name=func.__name__,
                    home=_current_hermes_home(),
                )
            )
        return func(*args, **kwargs)

    return wrapper


__all__ = ["assert_hermes_agent_untouched", "HERMES_HOME"]
