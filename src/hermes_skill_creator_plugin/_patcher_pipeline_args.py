"""Parameter-object dataclasses for the patcher pipeline.

Split from ``_patcher_pipeline`` (WPS211 cap). Each public helper takes
a single bundle instead of 6+ positional/keyword arguments.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._patcher_sites import Site

WriteStateFn = Any  # Callable[[Path, dict[str, str]], None]


@dataclasses.dataclass(frozen=True)
class _OkCheckArgs:
    """Inputs for :func:`ok_check_result` (bundled to stay under WPS211)."""

    sites: list[Site]
    state: dict[str, str]
    sites_patched: list[str]
    sites_already: list[str]
    target_path: Path
    diagnostics: list[str]
    exit_ok_code: int
    write_state_fn: WriteStateFn


@dataclasses.dataclass(frozen=True)
class _ApplySitesArgs:
    """Inputs for :func:`apply_sites` (bundled to stay under WPS211)."""

    sites: list[Site]
    target_path: Path
    state: dict[str, str]
    sites_patched: list[str]
    sites_already: list[str]
    diagnostics: list[str]
    force: bool
    audit_log_path: Path | None
    exit_ok_code: int
    write_state_fn: WriteStateFn


@dataclasses.dataclass(frozen=True)
class _BuildResultArgs:
    """Inputs for :func:`_build_result` (bundled to stay under WPS211)."""

    exit_code: int
    sites_patched: tuple[str, ...]
    sites_already: tuple[str, ...]
    state: dict[str, str]
    diagnostics: tuple[str, ...]
    rejected_path: Path | None = None
