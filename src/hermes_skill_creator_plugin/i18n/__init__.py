"""English + Hungarian i18n message constants for the patcher pipeline.

The re-export hub previously declared here was removed to satisfy
wemake WPS412 (no logic in ``__init__.py``). The patcher pipeline and
its helpers now import their strings directly from
:mod:`hermes_skill_creator_plugin.i18n.messages_en` (and
``messages_hu`` for bilingual consumers).

This module re-exports three pipeline-audit constants (FORCE_AUDIT_LOG,
LINE_DRIFT, TEXT_DRIFT) so cross-module attribute lookups (e.g. via
``hermes_skill_creator_plugin.i18n.FORCE_AUDIT_LOG``) resolve under
mypy --strict. The constants themselves are defined in
:mod:`messages_en`.
"""

from __future__ import annotations

from hermes_skill_creator_plugin.i18n import messages_en as _en

FORCE_AUDIT_LOG = _en.FORCE_AUDIT_LOG
LINE_DRIFT = _en.LINE_DRIFT
TEXT_DRIFT = _en.TEXT_DRIFT
