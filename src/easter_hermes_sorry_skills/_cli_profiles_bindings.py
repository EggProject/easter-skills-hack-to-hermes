"""Centralized rebindings for ``cli_profiles`` orchestrator.

The orchestrator module pulls in helpers from several sibling
``_cli_profiles_*`` modules via ``from <module> import <name>``
to keep the orchestrator itself under the wemake WPS201 cap
(<=12 imports per module) and WPS202 cap (<=7 module members).

This indirection module centralizes the rebinding logic so the
orchestrator stays slim.
"""

from __future__ import annotations

from easter_hermes_sorry_skills import (
    _cli_profiles_bilingual as _bilingual_mod,
)
from easter_hermes_sorry_skills import (
    _cli_profiles_cli as _cli_mod,
)
from easter_hermes_sorry_skills import (
    _cli_profiles_cli_help as _cli_help_mod,
)
from easter_hermes_sorry_skills import (
    _cli_profiles_report as _report_mod,
)
from easter_hermes_sorry_skills import (
    _cli_profiles_skill as _skill_mod,
)
from easter_hermes_sorry_skills import (
    _cli_profiles_table as _table_mod,
)
from easter_hermes_sorry_skills.i18n import messages_en as _messages_en_mod
from easter_hermes_sorry_skills.i18n import messages_hu as _messages_hu_mod

# Re-bindings matching the previous top-level names exposed by the
# orchestrator (kept for backward compat with tests + external callers).
_build_bilingual = _bilingual_mod.build_bilingual
_build_help_text = _cli_help_mod.build_help_text
main_cmd = _cli_mod.main_cmd
_make_cli = _cli_mod.make_cli
AuditReport = _report_mod.AuditReport
EnabledSkillRow = _skill_mod.EnabledSkillRow
build_profile_table = _table_mod.build_profile_table
render_all_profiles = _table_mod.render_all_profiles
EN = _messages_en_mod.EN_MESSAGES
HU = _messages_hu_mod.HU_MESSAGES
