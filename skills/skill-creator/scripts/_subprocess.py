"""Helpers for invoking Hermes CLI from skill scripts.

The hermes_subprocess_env() helper returns an environment dict suitable for
spawning a `hermes` subprocess. By default it preserves every existing
environment variable (PATH, HOME, API keys, etc.) and does NOT strip
CLAUDECODE.

Rationale for the default behavior:
- Hermes does not auto-strip CLAUDECODE; it is an Anthropic-specific signal.
- HERMES_SESSION_ID is read-only (auto-set by the agent). Never override it.
- For nested Hermes-in-Hermes isolation, prefer the profile mechanism
  (`hermes -p <name>`) which gives each profile its own ~/.hermes, sessions,
  and gateway PID. Alternatively, override HERMES_HOME to point at an
  isolated config dir.

If you need to strip additional vars for a specific call site, pass them via
extra_vars_to_strip.
"""

import os
from collections.abc import Iterable


def hermes_subprocess_env(extra_vars_to_strip: Iterable[str] | None = None) -> dict[str, str]:
    """Return an env dict for spawning a Hermes subprocess.

    Args:
        extra_vars_to_strip: Optional iterable of additional variable names to
            exclude from the returned env. Defaults to None (nothing stripped).

    Returns:
        A copy of os.environ with the requested vars removed.
    """
    env = dict(os.environ)
    if extra_vars_to_strip:
        for name in extra_vars_to_strip:
            env.pop(name, None)
    return env
