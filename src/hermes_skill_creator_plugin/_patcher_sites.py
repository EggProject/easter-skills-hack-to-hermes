"""Script #1 patch sites: dispatcher + re-exports.

The dataclass + canonical site table lives in ``_patcher_sites_table``
to keep this module slim (WPS202); tests import the public symbols from
``hermes_skill_creator_plugin._patcher_sites`` so we re-export them
below.

See also: plans/04 §Multi-signal targeting + plans/05 §Site table.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._patcher_sites_table import (
    ALL_TASK_E_SITES,
    BACKGROUND_REVIEW_REL,
    E1_SKILLS_GUIDANCE,
    E2_MEMORY_GUIDANCE,
    E3_BUILD_SKILLS_PROMPT,
    E4_SKILL_REVIEW_PROMPT,
    E5_COMBINED_REVIEW_PROMPT,
    E6_SKILL_MANAGE_SCHEMA_DESC,
    E7_SKILLS_DOC_SECTION,
    PROMPT_BUILDER_REL,
    S1_CAP_SITE,
    SKILL_CREATOR_CONSULT_RULE,
    SKILL_MANAGER_TOOL_REL,
    SKILLS_DOC_REL,
    TOOLS_SKILL_UTILS_REL,
    Anchor,
    Site,
)

__all__ = [
    "ALL_TASK_E_SITES",
    "Anchor",
    "BACKGROUND_REVIEW_REL",
    "E1_SKILLS_GUIDANCE",
    "E2_MEMORY_GUIDANCE",
    "E3_BUILD_SKILLS_PROMPT",
    "E4_SKILL_REVIEW_PROMPT",
    "E5_COMBINED_REVIEW_PROMPT",
    "E6_SKILL_MANAGE_SCHEMA_DESC",
    "E7_SKILLS_DOC_SECTION",
    "PROMPT_BUILDER_REL",
    "S1_CAP_SITE",
    "SKILL_CREATOR_CONSULT_RULE",
    "SKILL_MANAGER_TOOL_REL",
    "SKILLS_DOC_REL",
    "Site",
    "TOOLS_SKILL_UTILS_REL",
]


def sites_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> tuple[Site, ...]:
    """Return the (S1.cap, [Task E...]) tuple for the given flag combination."""
    sites: list[Site] = [S1_CAP_SITE]
    if not task_e_redirect:
        return tuple(sites)
    for site in ALL_TASK_E_SITES:
        if no_schema_redirect and site.site_id == E6_SKILL_MANAGE_SCHEMA_DESC.site_id:
            continue
        sites.append(site)
    return tuple(sites)
