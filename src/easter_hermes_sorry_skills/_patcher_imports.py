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

from easter_hermes_sorry_skills import _patcher_apply_atomic as _atomic_mod
from easter_hermes_sorry_skills import _patcher_consts as _consts_mod
from easter_hermes_sorry_skills import _patcher_helpers as _helpers_mod
from easter_hermes_sorry_skills import _patcher_sites as _sites

# Constants — re-bound to keep the orchestrator readable.
_atomic_write_bytes = _atomic_mod._atomic_write_bytes
EXIT_DRIFT = _consts_mod.EXIT_DRIFT
EXIT_IO = _consts_mod.EXIT_IO
EXIT_OK = _consts_mod.EXIT_OK
EXIT_PERMISSION = _consts_mod.EXIT_PERMISSION
EXIT_USER_ABORT = _consts_mod.EXIT_USER_ABORT
EXIT_VALIDATION = _consts_mod.EXIT_VALIDATION
STATE_DRIFTED = _consts_mod.STATE_DRIFTED
STATE_PATCHED = _consts_mod.STATE_PATCHED

# Helpers — re-bound to the canonical function names used by callers.
_cross_filesystem = _helpers_mod.cross_filesystem
file_has_circular_import = _helpers_mod.file_has_circular_import
hermes_agent_path = _helpers_mod.hermes_agent_path
is_hermes_agent = _helpers_mod.is_hermes_agent
locate_anchor = _helpers_mod.locate_anchor
site_already_patched = _helpers_mod.site_already_patched
site_in_state = _helpers_mod.site_in_state

# Site-table re-exports (each bound to the local name to keep
# ``_patcher.py`` readable without exceeding WPS235 on _patcher_sites).
# AC-2.8: ``SKILL_CREATOR_CONSULT_RULE`` is no longer re-exported —
# the constant lives in the target's ``agent/prompt_builder.py`` after
# the E0 site is applied.
ALL_TASK_E_SITES = _sites.ALL_TASK_E_SITES
E0_CONSULT_RULE_DEF = _sites.E0_CONSULT_RULE_DEF
E1_SKILLS_GUIDANCE = _sites.E1_SKILLS_GUIDANCE
E2_MEMORY_GUIDANCE = _sites.E2_MEMORY_GUIDANCE
E4B_CONSULT_RULE_IMPORT = _sites.E4B_CONSULT_RULE_IMPORT
E4_SKILL_REVIEW_PROMPT = _sites.E4_SKILL_REVIEW_PROMPT
E5_COMBINED_REVIEW_PROMPT = _sites.E5_COMBINED_REVIEW_PROMPT
S1_CAP_SITE = _sites.S1_CAP_SITE
S1_CAP_SITE_FALLBACK = _sites.S1_CAP_SITE_FALLBACK
TOOLS_SKILL_UTILS_REL = _sites.TOOLS_SKILL_UTILS_REL
Anchor = _sites.Anchor
Site = _sites.Site
sites_for_mode = _sites.sites_for_mode
