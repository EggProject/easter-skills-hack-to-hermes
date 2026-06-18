"""_migration_manifest.py — manifest parsing helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools._migration_paths import REPO_ROOT


def is_git_tracked(path: Path) -> bool:
    """True when ``path`` is in the git index."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", "--", str(path)],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return out.strip() != ""


def _stringify_entries(loaded: object) -> dict[str, str]:
    """Coerce manifest values to ``str``; keep only string entries."""
    if not isinstance(loaded, dict):
        return {}
    entries: dict[str, str] = {}
    for key, payload in loaded.items():
        if isinstance(payload, str) and isinstance(key, str):
            entries[key] = payload
    return entries


def load_manifest(manifest_path: Path) -> dict[str, str]:
    """Load manifest from ``manifest_path``; empty dict on missing/invalid."""
    if not manifest_path.exists():
        return {}
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _stringify_entries(loaded)
