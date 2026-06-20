"""Site payload helpers for the patcher pipeline.

Split from ``_patcher_pipeline`` (WPS202 module surface budget). The
``_SitePayload`` dataclass + the :func:`_build_site_payload` reader
live here so the apply loop stays under the module surface cap.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hermes_skill_creator_plugin._patcher_pipeline_emit import (
    mutate_lines_for_site,
)
from hermes_skill_creator_plugin._patcher_sites import Site


@dataclasses.dataclass(frozen=True)
class _SitePayload:
    """Before/after byte pair for one site's atomic write."""

    before: bytes
    after_bytes: bytes


def _build_site_payload(path: Path, site: Site) -> _SitePayload:
    """Read ``path`` and return the (before, after) byte pair for ``site``."""
    before = path.read_bytes()
    text = before.decode("utf-8", errors="replace")
    new_lines = mutate_lines_for_site(site, text)
    return _SitePayload(before=before, after_bytes="".join(new_lines).encode("utf-8"))
