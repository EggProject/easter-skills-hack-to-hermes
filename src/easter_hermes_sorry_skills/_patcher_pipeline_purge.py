"""Skills prompt snapshot cache purge.

At the end of a successful --apply, the patcher deletes Hermes' on-disk
skills prompt snapshot (default: ``~/.hermes/.skills_prompt_snapshot.json``).
The cache only tracks SKILL.md/DESCRIPTION.md mtimes; it does NOT detect
when prompt_builder.py is modified by the patcher. Without an explicit
purge, a stale snapshot would keep serving the pre-patch skills prompt
indefinitely.

This module isolates the path resolution + unlink logic so it is easy to
unit-test independently of the pipeline.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

from easter_hermes_sorry_skills._patcher_pipeline_types import PatcherResult

SKILLS_PROMPT_SNAPSHOT_FILENAME = ".skills_prompt_snapshot.json"


def resolve_skills_prompt_snapshot_path(
    hermes_home: Path | None = None,
) -> Path:
    """Resolve the absolute path of the skills prompt snapshot file.

    Resolution order:
    1. The explicit ``hermes_home`` argument (if provided).
    2. The ``HERMES_HOME`` environment variable.
    3. ``Path.home() / ".hermes"`` (the platform default).

    The caller is expected to pass either an explicit, trusted path or
    rely on the env var / default. Do not pass attacker-controlled paths;
    this function unlinks a file inside the provided directory without
    further checks.
    """
    if hermes_home is None:
        env = os.environ.get("HERMES_HOME", "").strip()
        if env:
            return (Path(env).expanduser().resolve()) / SKILLS_PROMPT_SNAPSHOT_FILENAME
        return Path.home() / ".hermes" / SKILLS_PROMPT_SNAPSHOT_FILENAME
    return Path(hermes_home) / SKILLS_PROMPT_SNAPSHOT_FILENAME


def purge_skills_prompt_snapshot(
    hermes_home: Path | None = None,
) -> Path:
    """Delete the skills prompt snapshot if it exists.

    Returns the absolute path unconditionally; the caller treats a
    missing snapshot as a no-op. Idempotent and non-raising
    (``missing_ok=True``).
    """
    snapshot_path = resolve_skills_prompt_snapshot_path(hermes_home)
    snapshot_path.unlink(missing_ok=True)
    return snapshot_path


def apply_skills_cache_purge_to_result(apply_result: PatcherResult) -> PatcherResult:
    """Purge the on-disk skills prompt snapshot after a successful apply.

    The given ``apply_result`` (presumably the result of
    :func:`_patcher._apply_sites_pipeline`) has its ``diagnostics`` extended
    with a one-line note about the purge. The snapshot path is always
    returned by :func:`purge_skills_prompt_snapshot`, so the diagnostic is
    always appended (``unlink(missing_ok=True)`` is a no-op if the file
    does not exist).
    """
    purged_path = purge_skills_prompt_snapshot()
    note = f"Purged skills prompt snapshot: {purged_path}"
    return dataclasses.replace(apply_result, diagnostics=apply_result.diagnostics + (note,))
