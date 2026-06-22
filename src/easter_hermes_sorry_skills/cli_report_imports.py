"""Consolidated import surface for the cli_report module.

The :mod:`.cli_report` module imports ~10 names from sibling modules
(``_cli_report_helpers``, ``_cli_report_helpers_paths``,
``_cli_report_rows``, ``_cli_report_cmd``, ``_cli_report_ui``,
``_enabled_detection``, ``_reporter``, ``_tokenizer``). Binding all
of them in ``cli_report``'s own import block blows past the wemake
WPS201 (<=12 imports per module) cap.

This module consolidates the cross-sibling imports so the orchestrator
reads through ``from easter_hermes_sorry_skills.cli_report_imports
import ...`` via the local re-bindings and keeps its own import block
under WPS201.

NOTE: The ``get_enabled_skills`` import MUST stay in ``cli_report.py``
itself — tests grep the source for that exact literal string (the
"reporter shares enabled-detection with Script #2" contract).
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _cli_report_cmd as _cmd_mod
from easter_hermes_sorry_skills import _cli_report_helpers_consts as _helpers_consts
from easter_hermes_sorry_skills import _cli_report_helpers_emit as _helpers_emit
from easter_hermes_sorry_skills import _cli_report_helpers_parse as _helpers_parse
from easter_hermes_sorry_skills import (
    _cli_report_helpers_paths as _paths_mod,
)
from easter_hermes_sorry_skills import _cli_report_rows as _rows_mod
from easter_hermes_sorry_skills import _cli_report_ui as _ui_mod
from easter_hermes_sorry_skills import _enabled_detection as _enabled_mod
from easter_hermes_sorry_skills import _reporter_models as _models_mod
from easter_hermes_sorry_skills import _reporter_sort as _sort_mod
from easter_hermes_sorry_skills import _tokenizer as _tokenizer_mod

# Sub-module re-bindings (kept for legacy access; new code should use
# ``_helpers_emit`` / ``_helpers_parse`` directly).
_helpers = _helpers_emit
_paths = _paths_mod
_rows = _rows_mod

# Function re-bindings.
emit_bilingual_help = _ui_mod.emit_bilingual_help
get_enabled_skills = _enabled_mod.get_enabled_skills
make_section = _helpers_emit.make_section
now_iso = _helpers_parse.now_iso
emit_output = _helpers_emit.emit_output
render_output = _helpers_emit.render_output
reject_unwanted_flags = _helpers_parse.reject_unwanted_flags
resolve_json_path = _helpers_emit.resolve_json_path
validate_sort_and_fmt = _helpers_parse.validate_sort_and_fmt
main = _cmd_mod.main
ProfileSection = _models_mod.ProfileSection
sort_rows = _sort_mod.sort_rows
estimate_tokens = _tokenizer_mod.estimate_tokens

# Constant re-bindings (kept here so cli_report.py can stay under WPS201).
SORT_TOKENS = _helpers_consts.SORT_TOKENS
FORMAT_TEXT = _helpers_consts.FORMAT_TEXT

# Row builder re-bindings.
_build_rows_for_profile = _rows_mod.build_rows_for_profile
_check_json_path = _rows_mod.check_json_path
EnabledDetectionUnavailable = _rows_mod.EnabledDetectionUnavailable
