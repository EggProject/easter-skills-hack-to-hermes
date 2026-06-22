"""Consolidated import surface for the cli_profiles orchestrator.

The :mod:`.cli_profiles` module re-exports + cross-imports ~16 names
from sibling modules (``_cli_profiles_audit``, ``_cli_profiles_cli``,
``_cli_profiles_report``) plus click, dataclass-style stdlib, the
``hermes_cli.profiles.ProfileInfo`` type, and the i18n message dicts.
Binding all of them in ``cli_profiles``'s own import block blows past
the wemake WPS201 (<=12 imports per module) cap.

This module consolidates the cross-sibling imports so the orchestrator
can read through ``from easter_hermes_sorry_skills.cli_profiles_imports
import ...`` via the local re-bindings and keep its own import block
under WPS201.

NOTE: The two canonical read-side / write-side import lines
(``from agent.skill_utils import get_disabled_skill_names`` and
``from hermes_cli.skills_config import save_disabled_skills``) MUST
stay in ``cli_profiles.py`` itself — tests grep the source for those
exact literal strings.
"""

from __future__ import annotations
