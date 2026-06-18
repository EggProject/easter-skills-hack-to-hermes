"""hermes_skill_creator_plugin — Hermes port of Anthropic's skill-creator.

The plugin package is purely advisory. The migrated skill-creator
lives at skills/skill-creator/ at the worktree root and is installed
flat by Script #2. This package NEVER bundles, contains, or owns the
skill files.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._safety import assert_hermes_agent_untouched

__all__ = ["assert_hermes_agent_untouched"]
