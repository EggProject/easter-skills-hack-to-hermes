"""Target-resolution pre-flight flow for the patcher CLI.

Extracted from ``cli_patch.py`` to keep that module under wemake WPS202
(≤7 module members). Holds the small pre-patch helpers that decide
whether to refuse the run (``is_hermes_agent``) and resolve the
``--target`` path.
"""

from __future__ import annotations

from pathlib import Path


def resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None
