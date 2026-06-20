"""Consolidated import surface for the apply pipeline module.

The :mod:`._patcher_pipeline` orchestrator pulls in 12+ symbols from
across :mod:`._patcher`, :mod:`._patcher_apply`, :mod:`._patcher_helpers`,
:mod:`._patcher_pipeline_consts`, :mod:`._patcher_pipeline_emit`,
:mod:`._patcher_sites`, and the top-level :mod:`.i18n` bilingual
catalog. Binding them all in ``_patcher_pipeline.py``'s own import
block blows past the wemake WPS201 (<=12 imports per module) cap.

This module consolidates those cross-sibling imports under stable
local names (matching the previous import binding so the orchestrator
body needs minimal change) so the orchestrator's own import block
stays under WPS201.

Note: :mod:`._patcher` is intentionally NOT imported here -- doing so
would create a cycle with :mod:`._patcher` -> :mod:`._patcher_pipeline`.
The single consumer (``_try_atomic_write``) lazy-imports it.
"""

from __future__ import annotations as annotations
