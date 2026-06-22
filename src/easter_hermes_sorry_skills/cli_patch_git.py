"""Best-effort git HEAD SHA lookup for the patcher CLI.

Extracted from ``cli_patch.py`` to keep that module under wemake WPS202
(≤7 module members).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

_GIT_REV_PARSE_TIMEOUT_SEC = 5


def git_head(target: Path) -> str:
    """Best-effort git HEAD SHA for the target; empty on failure."""
    import subprocess

    try:
        return run_git_rev_parse(subprocess, target)
    except Exception:
        return ""


def run_git_rev_parse(subprocess_module: ModuleType, target: Path) -> str:
    """Run ``git rev-parse HEAD`` in ``target``; return stripped stdout."""
    proc = subprocess_module.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
        timeout=_GIT_REV_PARSE_TIMEOUT_SEC,
    )
    return str(proc.stdout).strip()
