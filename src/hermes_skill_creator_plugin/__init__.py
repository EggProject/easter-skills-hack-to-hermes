"""hermes_skill_creator_plugin — Hermes port of Anthropic's skill-creator.

The plugin package is purely advisory. The migrated skill-creator
lives at skills/skill-creator/ at the worktree root and is installed
flat by Script #2. This package NEVER bundles, contains, or owns the
skill files.

The :data:`__all__` re-export of ``assert_hermes_agent_untouched`` was
removed to satisfy wemake WPS412 (no logic in ``__init__.py``). Callers
should import it from :mod:`hermes_skill_creator_plugin._safety`
directly.
"""
