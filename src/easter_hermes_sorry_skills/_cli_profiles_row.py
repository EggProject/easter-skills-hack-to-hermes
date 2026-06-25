"""Row scaffolding for the per-profile audit report (READ-ONLY).

Phase 8 collapsed the apply row into a read-only payload shape: the
report's per-profile row is now a flat dict carrying the
``enabled_skills`` list, the per-profile ``token_total`` /
``token_source`` rollups, and any ``warnings`` collected during the
scan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def new_row(profile_path: Path) -> dict[str, Any]:
    """Build the initial empty row dict for one profile."""
    return empty_row(profile_path.name or "hermes")


def empty_row(profile_name: str) -> dict[str, Any]:
    """Return the baseline empty row dict for the read-only report."""
    return {
        "profile_name": profile_name,
        "enabled_skills": [],
        "token_total": 0,
        "token_source": "tokenizer",
        "warnings": [],
    }
