"""Consolidated import surface for the cli_profiles orchestrator.

The :mod:`.cli_profiles` module re-exports + cross-imports ~16 names
from sibling modules (``_cli_profiles_audit``, ``_cli_profiles_cli``,
``_cli_profiles_report``) plus click, dataclass-style stdlib, the
``hermes_cli.profiles.ProfileInfo`` type, and the i18n message dicts.
Binding all of them in ``cli_profiles``'s own import block blows past
the wemake WPS201 (<=12 imports per module) cap.

This module consolidates the cross-sibling imports so the orchestrator
can read through ``from hermes_skill_creator_plugin.cli_profiles_imports
import ...`` via the local re-bindings and keep its own import block
under WPS201.

NOTE: The two canonical read-side / write-side import lines
(``from agent.skill_utils import get_disabled_skill_names`` and
``from hermes_cli.skills_config import save_disabled_skills``) MUST
stay in ``cli_profiles.py`` itself — tests grep the source for those
exact literal strings.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._cli_profiles_audit import (
    audit_profile as _audit_profile,
)
from hermes_skill_creator_plugin._cli_profiles_audit import (
    build_bilingual as _build_bilingual,
)
from hermes_skill_creator_plugin._cli_profiles_audit import (
    diff_sets,
    walk_skills,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    build_help_text as _build_help_text,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    main_cmd,
)
from hermes_skill_creator_plugin._cli_profiles_cli import (
    make_cli as _make_cli,
)
from hermes_skill_creator_plugin._cli_profiles_report import AuditReport
from hermes_skill_creator_plugin.i18n.messages_en import EN_MESSAGES as EN
from hermes_skill_creator_plugin.i18n.messages_hu import HU_MESSAGES as HU

__all__ = [
    "AuditReport",
    "EN",
    "HU",
    "_audit_profile",
    "_build_bilingual",
    "_build_help_text",
    "_make_cli",
    "diff_sets",
    "main_cmd",
    "walk_skills",
]
