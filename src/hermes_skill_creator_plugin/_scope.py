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


@contextmanager
def hermes_home_scope(path: Path) -> Iterator[None]:
    """Mirror ``HERMES_HOME`` in both the override token AND ``os.environ``.

    Restores BOTH on exit, even on exception. The previous override
    token is captured via ``get_hermes_home_override()`` (which returns
    ``None`` when no override is set); the previous ``os.environ['HERMES_HOME']``
    is captured via ``os.environ.get``. On exit the env var is restored
    first (cheap), then the override token is reset.

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
    from hermes_constants import (
        get_hermes_home_override,
        reset_hermes_home_override,
        set_hermes_home_override,
    )

    prev_override = get_hermes_home_override()
    prev_env = os.environ.get("HERMES_HOME")
    token = set_hermes_home_override(str(path))
    os.environ["HERMES_HOME"] = str(path)
    try:
        yield
    finally:
        # Restore env first (cheap), then the override token.
        if prev_env is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = prev_env
        reset_hermes_home_override(token)
        # ``prev_override`` is captured for symmetry; the live state is
        # already restored by ``reset_hermes_home_override`` (the token
        # was captured against that earlier state). Reference the name
        # to keep the binding obvious to readers.
        _ = prev_override
