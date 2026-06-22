"""Diff-builder helpers for the ``--force`` confirmation gate.

Extracted from :mod:`_patcher_force_confirm` to keep the gate's
module under wemake WPS202 (<=7 module members). Holds the
unified-diff builder + the per-site before/after text accumulator.
"""

from __future__ import annotations

import dataclasses
import difflib
from pathlib import Path

from hermes_skill_creator_plugin._patcher_sites import Site
from hermes_skill_creator_plugin.i18n.messages_en import FORCE_CONFIRM_DIFF_HEADER


@dataclasses.dataclass(frozen=True)
class _SiteDiffView:
    """Pre-computed before/after text for one site."""

    site: Site
    before_text: str
    after_text: str


def _build_unified_diff(site: Site, before_text: str, after_text: str) -> str:
    """Build a unified-diff string for one site (label-only header)."""
    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{site.file_path}",
        tofile=f"b/{site.file_path}",
    )
    return "".join(diff_lines)


def _build_site_diff(target_path: Path, site: Site) -> _SiteDiffView:
    """Read ``target_path/site.file_path`` and return before/after text."""
    from hermes_skill_creator_plugin._patcher_pipeline_emit import (
        mutate_lines_for_site,
    )

    path = target_path / site.file_path
    before_bytes = path.read_bytes() if path.exists() else b""
    before_text = before_bytes.decode("utf-8", errors="replace")
    after_lines = mutate_lines_for_site(site, before_text)
    return _SiteDiffView(
        site=site,
        before_text=before_text,
        after_text="".join(after_lines),
    )


def build_diff_text(sites: tuple[Site, ...], target_path: Path) -> str:
    """Build the full unified-diff text for the planned apply."""
    blocks: list[str] = [_diff_block_for(target_path, site) for site in sites]
    site_ids = ", ".join(site.site_id for site in sites) if sites else "(none)"
    header = FORCE_CONFIRM_DIFF_HEADER.format(sites=site_ids)
    body = "\n".join(blocks)
    return f"{header}\n{body}"


def _diff_block_for(target_path: Path, site: Site) -> str:
    """Build the unified-diff block for one site."""
    view = _build_site_diff(target_path, site)
    return _build_unified_diff(view.site, view.before_text, view.after_text)
