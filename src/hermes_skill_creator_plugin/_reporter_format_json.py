"""JSON-format helpers for the hermes-skill-creator reporter.

Extracted from :mod:`._reporter_format` to keep the parent under wemake
WPS202 (module members <= 7). The ``format_json`` entry point plus its
small ``_skill_to_dict`` row converter live here.
"""

from __future__ import annotations

import json
from typing import Any

from hermes_skill_creator_plugin._reporter_models import ProfileSection, SkillRow


def _skill_to_dict(row_obj: SkillRow) -> dict[str, Any]:
    return {
        "name": row_obj.name,
        "description": row_obj.description_full,
        "tokens": row_obj.tokens,
        "use_count": row_obj.use_count,
        "view_count": row_obj.view_count,
        "patch_count": row_obj.patch_count,
        "last_used_at": row_obj.last_used_at,
        "last_viewed_at": row_obj.last_viewed_at,
        "last_patched_at": row_obj.last_patched_at,
        "pct_of_cap": row_obj.pct_of_cap,
    }


def format_json(
    *,
    tool: str,
    version: str,
    generated_at: str,
    sections: list[ProfileSection],
) -> str:
    """Render a deterministic JSON document for one OR MANY profiles.

    Args:
        tool: tool name (top-level).
        version: tool version (top-level).
        generated_at: ISO 8601 timestamp (top-level).
        sections: list of ProfileSection, one per profile. The
            single-profile case is ``sections=[ProfileSection(...)]``;
            the output is always a single valid JSON object with a
            ``profiles: [...]`` array.

    Returns:
        String with the rendered JSON document (sort_keys=True for
        stability).
    """
    payload: dict[str, Any] = {
        "tool": tool,
        "version": version,
        "generated_at": generated_at,
        "profiles": [
            {
                "profile_name": section.profile_name,
                "enabled_skills": [_skill_to_dict(row_obj) for row_obj in section.rows],
                "total_tokens": section.total_tokens,
            }
            for section in sections
        ],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)


__all__ = [
    "format_json",
]
