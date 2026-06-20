"""Hermes-HOME scoping context manager (TDD plan 06).

Public surface:
    hermes_home_scope(path: Path) -> ContextManager[None]

The scope mirrors ``HERMES_HOME`` in BOTH the ``hermes_constants`` override
token AND ``os.environ['HERMES_HOME']`` for the duration of the ``with``
block. Both are restored on exit, even when an exception propagates.

Why the dual mirror:
    - ``hermes_cli.config.load_config()`` and ``save_config()`` resolve the
      config path via the ``hermes_constants`` override token (via
      ``get_config_path()``). NOT ``os.environ['HERMES_HOME']``.
    - ``hermes_cli.skills_hub.do_install`` (and its ``ensure_hub_dirs``
      helper at ``tools/skills_hub.py:3287``) reads ``os.environ['HERMES_HOME']``
      in some sub-paths.
    - Mirroring both is the only way to ensure config writes and hub
      installs resolve to the scoped ``HERMES_HOME`` (plan 06 D4).

Safety:
    The scope MUST NOT touch the live ``~/.hermes`` install when the
    caller passes a ``tmp_path`` directory. The tests under
    ``tests/unit/test_scope.py`` enforce the dual-mirror contract and
    assert the no-touch sentinel ``~/.hermes/hermes-agent/agent/skill_utils.py``
    sha256 is unchanged.

See also: plans/06-script-2-profiles.md, plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

HERMES_HOME_ENV_KEY = "HERMES_HOME"


def _restore_env(prev_value: str | None) -> None:
    """Restore the HERMES_HOME env var to its previous state."""
    if prev_value is None:
        os.environ.pop(HERMES_HOME_ENV_KEY, None)
        return
    os.environ[HERMES_HOME_ENV_KEY] = prev_value


@contextmanager
def hermes_home_scope(path: Path) -> Iterator[None]:
    """Mirror ``HERMES_HOME`` in both the override token AND ``os.environ``.

    Restores BOTH on exit, even on exception. The override token is
    obtained from :func:`set_hermes_home_override` (which returns it
    so the caller can pass it to :func:`reset_hermes_home_override`
    later); the previous ``os.environ['HERMES_HOME']`` is captured via
    ``os.environ.get``. On exit the env var is restored first (cheap),
    then the override token is reset.

    Args:
        path: The scoped ``HERMES_HOME`` for the duration of the block.

    Yields:
        ``None``. Callers can run config + hub-install operations inside
        the block; both will see ``HERMES_HOME == str(path)``.

    Raises:
        Any exception raised inside the block propagates after both
        values are restored.
    """
    # Imports are local so that tests can monkeypatch ``hermes_constants``
    # in ``sys.modules`` before the call site runs.
    from hermes_constants import set_hermes_home_override

    prev_env = os.environ.get(HERMES_HOME_ENV_KEY)
    token = set_hermes_home_override(str(path))
    os.environ[HERMES_HOME_ENV_KEY] = str(path)
    try:
        yield
    finally:
        _restore_scope(prev_env, token)


def _restore_scope(prev_env: str | None, token: object) -> None:
    """Restore both env var and override token (extracted from finally).

    ``reset_hermes_home_override`` is imported locally here (not in
    ``hermes_home_scope``) so that callers who monkeypatch the symbol
    between the call site and the ``finally`` block see the patch.

    ``prev_override`` is intentionally NOT a parameter here: the live
    state is already restored by ``reset_hermes_home_override`` (the
    token was captured against that earlier state), so the captured
    value is never read. Keeping it as a positional arg would only
    trigger wemake WPS122 ("all unused variables definition").
    """
    from hermes_constants import reset_hermes_home_override

    _restore_env(prev_env)
    reset_hermes_home_override(token)
