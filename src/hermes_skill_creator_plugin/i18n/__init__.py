"""English + Hungarian i18n message constants for the patcher pipeline.

The re-export hub previously declared here was removed to satisfy
wemake WPS412 (no logic in ``__init__.py``). The patcher pipeline and
its helpers now import their strings directly from
:mod:`hermes_skill_creator_plugin.i18n.messages_en` (and
``messages_hu`` for bilingual consumers).
"""
