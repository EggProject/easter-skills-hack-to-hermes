"""Centralized rebindings for ``cli_profiles`` orchestrator.

The orchestrator module pulls in helpers from several sibling
``_cli_profiles_*`` modules via ``from <module> import <name>``
to keep the orchestrator itself under the wemake WPS201 cap
(<=12 imports per module) and WPS202 cap (<=7 module members).

This indirection module centralizes the rebinding logic so the
orchestrator stays slim.
"""

from __future__ import annotations

from hermes_skill_creator_plugin import (
    _cli_profiles_audit as _audit_mod,
)
from hermes_skill_creator_plugin import (
    _cli_profiles_bilingual as _bilingual_mod,
)
from hermes_skill_creator_plugin import (
    _cli_profiles_cli as _cli_mod,
)
from hermes_skill_creator_plugin import (
    _cli_profiles_cli_help as _cli_help_mod,
)
from hermes_skill_creator_plugin import (
    _cli_profiles_diff as _diff_mod,
)
from hermes_skill_creator_plugin import (
    _cli_profiles_report as _report_mod,
)
from hermes_skill_creator_plugin.i18n import messages_en as _messages_en_mod
from hermes_skill_creator_plugin.i18n import messages_hu as _messages_hu_mod

# Re-bindings matching the previous top-level names exposed by the
# orchestrator (kept for backward compat with tests + external callers).
_audit_profile = _audit_mod.audit_profile
_build_bilingual = _bilingual_mod.build_bilingual
diff_sets = _diff_mod.diff_sets
walk_skills = _diff_mod.walk_skills
_build_help_text = _cli_help_mod.build_help_text
main_cmd = _cli_mod.main_cmd
_make_cli = _cli_mod.make_cli
AuditReport = _report_mod.AuditReport
EN = _messages_en_mod.EN_MESSAGES
HU = _messages_hu_mod.HU_MESSAGES
