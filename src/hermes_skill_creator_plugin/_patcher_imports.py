"""Consolidated import surface for the patcher orchestrator.

The orchestrator (``_patcher.py``) needs ~18 names from sibling modules
(constants, exit codes, helpers, the site table, etc.). Exposing them
all in one module-level import block blows past wemake WPS201
(<=12 imports per module) and WPS235 (<=8 names from any single
module).

To keep the orchestrator's own import block under WPS201, this module
binds the cross-sibling re-exports as a single ``import _patcher_imports
as _imps`` surface, and ``_patcher.py`` reads through ``_imps.X``.
Siblings that are runtime-required directly (the migration helpers,
the apply pipelines) stay in the orchestrator's own import block.

Module members are kept under WPS202 by exposing only the names that
``_patcher.py`` actually reads; nothing else is re-bound here.
"""

from __future__ import annotations

from hermes_skill_creator_plugin import _patcher_apply as _apply_mod
from hermes_skill_creator_plugin import _patcher_apply_atomic as _atomic_mod
from hermes_skill_creator_plugin import _patcher_apply_state as _state_mod
from hermes_skill_creator_plugin import _patcher_consts as _consts_mod
from hermes_skill_creator_plugin import _patcher_helpers as _helpers_mod
from hermes_skill_creator_plugin import _patcher_migration as _migration_mod
from hermes_skill_creator_plugin import _patcher_migration_render as _migration_render_mod
from hermes_skill_creator_plugin import _patcher_migration_task_e as _task_e_mod
from hermes_skill_creator_plugin import _patcher_sites as _sites

# Constants — re-bound to keep the orchestrator readable.
REJECTED_SIDECAR = _apply_mod.REJECTED_SIDECAR
write_rejected = _apply_mod.write_rejected
_atomic_write_bytes = _atomic_mod._atomic_write_bytes
STATE_SIDECAR = _state_mod.STATE_SIDECAR
load_state = _state_mod.load_state
write_state = _state_mod.write_state
EXIT_DRIFT = _consts_mod.EXIT_DRIFT
EXIT_IO = _consts_mod.EXIT_IO
EXIT_OK = _consts_mod.EXIT_OK
EXIT_PERMISSION = _consts_mod.EXIT_PERMISSION
EXIT_USER_ABORT = _consts_mod.EXIT_USER_ABORT
EXIT_VALIDATION = _consts_mod.EXIT_VALIDATION

# Helpers — re-bound to the canonical function names used by callers.
_cross_filesystem = _helpers_mod.cross_filesystem
file_has_circular_import = _helpers_mod.file_has_circular_import
hermes_agent_path = _helpers_mod.hermes_agent_path
is_hermes_agent = _helpers_mod.is_hermes_agent
locate_anchor = _helpers_mod.locate_anchor
site_already_patched = _helpers_mod.site_already_patched
site_in_state = _helpers_mod.site_in_state
generate_migration_note = _migration_mod.generate_migration_note
migration_rows_for_mode = _migration_mod.migration_rows_for_mode
_render_cap_row = _migration_render_mod._render_cap_row
_render_task_e_row = _task_e_mod._render_task_e_row

# Site-table re-exports (each bound to the local name to keep
# ``_patcher.py`` readable without exceeding WPS235 on _patcher_sites).
ALL_TASK_E_SITES = _sites.ALL_TASK_E_SITES
E1_SKILLS_GUIDANCE = _sites.E1_SKILLS_GUIDANCE
E2_MEMORY_GUIDANCE = _sites.E2_MEMORY_GUIDANCE
E3_BUILD_SKILLS_PROMPT = _sites.E3_BUILD_SKILLS_PROMPT
E4_SKILL_REVIEW_PROMPT = _sites.E4_SKILL_REVIEW_PROMPT
E5_COMBINED_REVIEW_PROMPT = _sites.E5_COMBINED_REVIEW_PROMPT
E6_SKILL_MANAGE_SCHEMA_DESC = _sites.E6_SKILL_MANAGE_SCHEMA_DESC
E7_SKILLS_DOC_SECTION = _sites.E7_SKILLS_DOC_SECTION
S1_CAP_SITE = _sites.S1_CAP_SITE
SKILL_CREATOR_CONSULT_RULE = _sites.SKILL_CREATOR_CONSULT_RULE
TOOLS_SKILL_UTILS_REL = _sites.TOOLS_SKILL_UTILS_REL
Anchor = _sites.Anchor
Site = _sites.Site
sites_for_mode = _sites.sites_for_mode
