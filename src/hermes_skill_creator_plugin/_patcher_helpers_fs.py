"""Filesystem helpers used by the Script #1 patcher orchestrator.

Extracted from :mod:`._patcher_helpers` to keep the parent module under
wemake WPS202 (module members <= 7).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def cross_filesystem(target: Path) -> bool:
    """Best-effort cross-filesystem detector.

    Returns False on platforms that do not support ``os.statvfs``.
    """
    if not hasattr(os, "statvfs"):
        return False
    try:
        target_stat = os.statvfs(target)
    except OSError:
        return False
    try:
        tmp_stat = os.statvfs(tempfile.gettempdir())
    except OSError:
        return False
    return target_stat.f_fsid != tmp_stat.f_fsid
