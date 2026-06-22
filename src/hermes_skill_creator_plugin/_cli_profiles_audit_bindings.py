"""Centralized rebindings for ``_cli_profiles_audit`` orchestrator.

The orchestrator module pulls in helpers from several sibling
``_cli_profiles_*`` modules via ``from <module> import <name>``
to keep the orchestrator itself under the wemake WPS201 cap
(<=12 imports per module) and WPS202 cap (<=7 module members).

This indirection module centralizes the rebinding logic so the
orchestrator stays slim.
"""

from __future__ import annotations

from hermes_skill_creator_plugin import _cli_profiles_apply as _apply_mod
from hermes_skill_creator_plugin import _cli_profiles_bilingual as _bilingual_mod
from hermes_skill_creator_plugin import _cli_profiles_diff as _diff_mod
from hermes_skill_creator_plugin import _cli_profiles_report as _report_mod
from hermes_skill_creator_plugin import _cli_profiles_row as _row_mod
from hermes_skill_creator_plugin import _cli_profiles_walk as _walk_mod
from hermes_skill_creator_plugin import _scope as _scope_mod

# Re-bindings matching the previous top-level names exposed by the
# orchestrator (kept for backward compat with tests + external callers).
_SaveDisabledArgs = _apply_mod._SaveDisabledArgs
apply_clear_cache = _apply_mod.apply_clear_cache
apply_do_install = _apply_mod.apply_do_install
apply_save_disabled = _apply_mod.apply_save_disabled
desired_disabled_after_save = _apply_mod.desired_disabled_after_save
load_config_or_error = _apply_mod.load_config_or_error
read_disabled_or_empty = _apply_mod.read_disabled_or_empty
build_bilingual = _bilingual_mod.build_bilingual
diff_sets = _diff_mod.diff_sets
walk_skills = _diff_mod.walk_skills
walk_profile_subdirs = _walk_mod.walk_profile_subdirs
read_gateway_pid_stat = _walk_mod.read_gateway_pid_stat
PROFILE_DIRS = _walk_mod.PROFILE_DIRS
AuditReport = _report_mod.AuditReport
new_row = _row_mod.new_row
populate_diff_row = _row_mod.populate_diff_row
populate_walk_row = _row_mod.populate_walk_row
hermes_home_scope = _scope_mod.hermes_home_scope
