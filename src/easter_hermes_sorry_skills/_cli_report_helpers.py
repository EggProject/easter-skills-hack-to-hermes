"""Backward-compat stub for ``_cli_report_helpers``.

The constants and helpers that used to live here have been split into
``_cli_report_helpers_consts``, ``_cli_report_helpers_parse``, and
``_cli_report_helpers_emit`` to keep each leaf under wemake WPS202
(≤7 module members). New code should import from the leaf sub-modules
directly:

- constants → ``easter_hermes_sorry_skills._cli_report_helpers_consts``
- parse / validate helpers → ``easter_hermes_sorry_skills._cli_report_helpers_parse``
- emit / render helpers → ``easter_hermes_sorry_skills._cli_report_helpers_emit``

This stub remains so ``from easter_hermes_sorry_skills import
_cli_report_helpers as _mod`` continues to resolve, but it intentionally
exposes nothing at module level.
"""

from __future__ import annotations
