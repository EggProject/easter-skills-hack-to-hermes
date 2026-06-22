"""Per-profile directory walk helpers for cli_profiles audit (AC-3.10).

Split from ``_cli_profiles_diff`` to keep that module under the
wemake WPS202 cap (<=7 module members). The two public functions
walk ``PROFILE_DIRS`` and read ``gateway.pid`` stat-only; the row
scaffolding in ``_cli_profiles_row`` calls them via the bindings.
"""

from __future__ import annotations

from pathlib import Path

# Per-profile canonical subdirs walked by the audit (AC-3.10). Mirrors
# ``hermes_cli.profiles._PROFILE_DIRS``; the audit records presence/size
# for each. ``gateway.pid`` is a FLAT file in the profile root (NOT a
# subdir) and is read stat-only — see ``read_gateway_pid_stat``.
PROFILE_DIRS: tuple[str, ...] = (
    "memories",
    "sessions",
    "skills",
    "skins",
    "logs",
    "plans",
    "workspace",
    "cron",
    "home",
)

GATEWAY_PID_FILENAME = "gateway.pid"


def walk_profile_subdirs(
    profile_path: Path,
    subdir_names: tuple[str, ...] = PROFILE_DIRS,
) -> dict[str, dict[str, object]]:
    """Walk ``profile_path/<name>`` for each ``subdir_names`` entry (AC-3.10).

    Returns a dict keyed by subdir NAME; each value is
    ``{"present": bool, "size": int, "file_count": int}``. Size is the
    sum of file sizes recursively (no symlink deref). Missing subdirs
    are recorded with ``present=False`` and ``size=0`` so the audit
    row reflects the full canonical set.
    """
    return {name: _row_for_subdir(profile_path / name) for name in subdir_names}


def read_gateway_pid_stat(profile_path: Path) -> dict[str, object]:
    """Read ``<profile_path>/gateway.pid`` stat-only (AC-3.10).

    Returns ``{"present": bool, "size": int, "mtime": float}``; the
    file CONTENT is NEVER parsed (no ``read_text`` call). ``mtime`` is
    the float epoch seconds; ``size`` is the file size in bytes.
    Missing files return ``present=False`` with zero size.
    """
    pid_path = profile_path / GATEWAY_PID_FILENAME
    if not pid_path.is_file():
        return dict(present=False, size=0, mtime=0)
    try:
        stat_result = pid_path.stat()
    except OSError:
        return dict(present=False, size=0, mtime=0)
    return dict(
        present=True,
        size=int(stat_result.st_size),
        mtime=float(stat_result.st_mtime),
    )


def _row_for_subdir(subdir: Path) -> dict[str, object]:
    """Build the audit row for one PROFILE_DIRS subdir (present or missing)."""
    if not subdir.is_dir():
        return dict(present=False, size=0, file_count=0)
    size_bytes, file_count = _walk_subdir_stats(subdir)
    return dict(present=True, size=size_bytes, file_count=file_count)


def _walk_subdir_stats(subdir: Path) -> tuple[int, int]:
    """Return ``(total_size_bytes, file_count)`` for ``subdir`` recursively."""
    total = 0
    count = 0
    try:
        children = list(subdir.rglob("*"))
    except OSError:
        return 0, 0
    for child in children:
        size = _safe_file_size(child)
        if size is None:
            continue
        total += size
        count += 1
    return total, count


def _safe_file_size(child: Path) -> int | None:
    """Return ``child`` size in bytes, or None if it is a dir or stat fails."""
    if not child.is_file():
        return None
    try:
        return int(child.stat().st_size)
    except OSError:
        return None
