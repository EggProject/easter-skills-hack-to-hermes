"""Input dataclass for the patcher orchestrator.

Split from ``_patcher`` (WPS202 module surface budget). The :class:`PatchRunInputs`
struct carries the 11 keyword inputs for :func:`run_patch`.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class PatchRunInputs:
    """All keyword inputs for :func:`run_patch`.

    Bundles the 11 CLI kwargs into a single struct so the public
    function signature stays keyword-only and wemake WPS211 / WPS210
    stay below threshold.
    """

    target: Path | None = None
    check: bool = False
    apply: bool = False
    force: bool = False
    i_accept_line_drift: bool = False
    task_e_redirect: bool = False
    no_schema_redirect: bool = False
    yes: bool = False
    verbose: bool = False
    audit_log_path: Path | None = None
    git_head: str = ""
