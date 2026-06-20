"""Consolidated import surface for the cli_profiles_audit orchestrator.

The :mod:`._cli_profiles_audit` module re-exports ~13 helpers from
``_cli_profiles_apply``, ``_cli_profiles_bilingual``,
``_cli_profiles_diff``, ``_cli_profiles_report``,
``_cli_profiles_row``, and ``_scope``. Binding all of them in
``_cli_profiles_audit``'s own import block blows past the wemake WPS201
(<=12 imports per module) cap.

This module consolidates the cross-sibling imports and re-binds each
helper under its canonical local name. The orchestrator reads through
``from hermes_skill_creator_plugin._cli_profiles_audit_imports import ...``
via ``_imps`` so its own import block stays under WPS201.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._cli_profiles_bilingual import (
    build_bilingual as build_bilingual,
)
from hermes_skill_creator_plugin._cli_profiles_diff import (
    diff_sets as diff_sets,
)
from hermes_skill_creator_plugin._cli_profiles_report import (
    AuditReport as AuditReport,
)
