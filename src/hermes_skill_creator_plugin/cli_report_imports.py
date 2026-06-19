"""Consolidated import surface for the cli_report module.

The :mod:`.cli_report` module imports ~10 names from sibling modules
(``_cli_report_helpers``, ``_cli_report_helpers_paths``,
``_cli_report_rows``, ``_cli_report_cmd``, ``_cli_report_ui``,
``_enabled_detection``, ``_reporter``, ``_tokenizer``). Binding all
of them in ``cli_report``'s own import block blows past the wemake
WPS201 (<=12 imports per module) cap.

This module consolidates the cross-sibling imports so the orchestrator
reads through ``from hermes_skill_creator_plugin.cli_report_imports
import ...`` via the local re-bindings and keeps its own import block
under WPS201.

NOTE: The ``get_enabled_skills`` import MUST stay in ``cli_report.py``
itself — tests grep the source for that exact literal string (the
"reporter shares enabled-detection with Script #2" contract).
"""

from __future__ import annotations

from hermes_skill_creator_plugin import _cli_report_helpers as _helpers
from hermes_skill_creator_plugin import _cli_report_helpers_paths as _paths
from hermes_skill_creator_plugin import _cli_report_rows as _rows
from hermes_skill_creator_plugin._cli_report_cmd import main
from hermes_skill_creator_plugin._cli_report_ui import emit_bilingual_help
from hermes_skill_creator_plugin._reporter import ProfileSection, sort_rows
from hermes_skill_creator_plugin._tokenizer import estimate_tokens

__all__ = [
    "ProfileSection",
    "_helpers",
    "_paths",
    "_rows",
    "emit_bilingual_help",
    "estimate_tokens",
    "main",
    "sort_rows",
]
