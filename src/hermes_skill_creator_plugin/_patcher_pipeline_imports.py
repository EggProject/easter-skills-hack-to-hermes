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

from hermes_skill_creator_plugin import _patcher_apply as _apply_mod
from hermes_skill_creator_plugin import _patcher_helpers as _helpers_mod
from hermes_skill_creator_plugin import _patcher_migration as _migration_mod
from hermes_skill_creator_plugin import _patcher_pipeline_consts as _consts_mod
from hermes_skill_creator_plugin import _patcher_pipeline_emit as _emit_mod

# Constants and helpers re-bound under the names ``_patcher_pipeline``
# already uses locally.
AUDIT_LOG = _apply_mod.AUDIT_LOG
_cross_filesystem = _helpers_mod.cross_filesystem
_now_iso = _migration_mod._now_iso
EXIT_IO = _consts_mod.EXIT_IO
EXIT_PERMISSION = _consts_mod.EXIT_PERMISSION
STATE_DRIFTED = _consts_mod.STATE_DRIFTED
STATE_PATCHED = _consts_mod.STATE_PATCHED
emit_audit_log = _emit_mod.emit_audit_log
mutate_lines_for_site = _emit_mod.mutate_lines_for_site
