"""tools/skill_usage.pyi — type stub for the host runtime ``tools.skill_usage`` module.

This module exists at the host (Hermes / Anthropic Claude Code) runtime
but is not installed in this plugin's environment. Importing it inside
the reporter is wrapped in ``try / except Exception`` so the runtime
never crashes if it's missing, but mypy still wants to resolve the name
at type-check time.
"""

from typing import Any

usage_report: Any
