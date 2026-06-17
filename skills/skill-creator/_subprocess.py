"""hermes_subprocess_env() — single source of truth for the nesting-guard env var.

Pin: the Hermes nesting-guard env var name. See docs/plans/12-risks-and-open-questions.md Q1.

This module is OWNED by E-skill. The migrated `scripts/run_eval.py` and
`scripts/improve_description.py` import this helper and use it as
`env=hermes_subprocess_env()`. They NEVER `os.environ.pop` the var in the
parent process; stripping is performed here for the subprocess env ONLY.

TDD test cases for this module:
  test_hermes_subprocess_env_strips_hermes_session
  test_hermes_subprocess_env_strips_claudecode
  test_hermes_subprocess_env_preserves_other_vars
  test_hermes_subprocess_env_does_not_mutate_parent
  test_nesting_guard_var_constant_is_hermes_session
  test_hermes_subprocess_env_when_guard_unset
  test_helper_is_single_source_of_truth
"""

from __future__ import annotations

import os

# Pin: the Hermes nesting-guard env var name. See 12-risks-and-open-questions Q1.
NESTING_GUARD_VAR: str = "HERMES_SESSION"

# Pin: the legacy Anthropic nesting-guard env var. Must also be stripped so
# a migrated `hermes -p` subprocess can run cleanly when the parent process
# is itself a Claude/Anthropic session (e.g. during Phase 5 eval).
_LEGACY_GUARD_VARS: frozenset[str] = frozenset({NESTING_GUARD_VAR, "CLAUDECODE"})


def hermes_subprocess_env() -> dict[str, str]:
    """Return os.environ minus the nesting-guard vars (Hermes + legacy Claude).

    Strips BOTH the current Hermes guard (`HERMES_SESSION`) and the legacy
    Anthropic guard (`CLAUDECODE`) so a migrated `hermes -p` subprocess can
    run cleanly even when the parent process is itself a Claude/Anthropic
    session (e.g. during the Phase 5 eval pipeline). Stripped ONLY for the
    subprocess; the parent process keeps the vars set so Hermes's own
    nesting guard sees the parent and refuses the inner call unless the
    child explicitly un-nests via this helper.

    Returns:
        A copy of os.environ with the nesting-guard vars removed.
    """
    return {k: v for k, v in os.environ.items() if k not in _LEGACY_GUARD_VARS}


__all__ = ["NESTING_GUARD_VAR", "hermes_subprocess_env"]
