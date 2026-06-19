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

from hermes_skill_creator_plugin import _patcher_sites as _sites
from hermes_skill_creator_plugin._patcher_apply import (
    REJECTED_SIDECAR,
    write_rejected,
)
from hermes_skill_creator_plugin._patcher_apply_atomic import _atomic_write_bytes
from hermes_skill_creator_plugin._patcher_apply_state import (
    STATE_SIDECAR,
    load_state,
    write_state,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_DRIFT,
    EXIT_IO,
    EXIT_OK,
    EXIT_PERMISSION,
    EXIT_USER_ABORT,
    EXIT_VALIDATION,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    file_has_circular_import,
    hermes_agent_path,
    is_hermes_agent,
    locate_anchor,
    site_already_patched,
    site_in_state,
)
from hermes_skill_creator_plugin._patcher_migration import (
    generate_migration_note,
    migration_rows_for_mode,
)
from hermes_skill_creator_plugin._patcher_migration_render import (
    _render_cap_row,
    _render_task_e_row,
)

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

__all__ = [
    "ALL_TASK_E_SITES",
    "E1_SKILLS_GUIDANCE",
    "E2_MEMORY_GUIDANCE",
    "E3_BUILD_SKILLS_PROMPT",
    "E4_SKILL_REVIEW_PROMPT",
    "E5_COMBINED_REVIEW_PROMPT",
    "E6_SKILL_MANAGE_SCHEMA_DESC",
    "E7_SKILLS_DOC_SECTION",
    "REJECTED_SIDECAR",
    "STATE_SIDECAR",
    "S1_CAP_SITE",
    "SKILL_CREATOR_CONSULT_RULE",
    "TOOLS_SKILL_UTILS_REL",
    "Anchor",
    "EXIT_DRIFT",
    "EXIT_IO",
    "EXIT_OK",
    "EXIT_PERMISSION",
    "EXIT_USER_ABORT",
    "EXIT_VALIDATION",
    "Site",
    "_atomic_write_bytes",
    "_cross_filesystem",
    "_render_cap_row",
    "_render_task_e_row",
    "file_has_circular_import",
    "generate_migration_note",
    "hermes_agent_path",
    "is_hermes_agent",
    "load_state",
    "locate_anchor",
    "migration_rows_for_mode",
    "site_already_patched",
    "site_in_state",
    "sites_for_mode",
    "write_rejected",
    "write_state",
]
