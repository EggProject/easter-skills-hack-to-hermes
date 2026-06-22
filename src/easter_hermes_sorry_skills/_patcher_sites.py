"""Script #1 patch sites: dispatcher + re-exports.

The dataclass + canonical site table lives in ``_patcher_sites_table``
to keep this module slim (WPS202); tests import the public symbols from
``easter_hermes_sorry_skills._patcher_sites`` so we re-export them
below.

See also: plans/04 §Multi-signal targeting + plans/05 §Site table.
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _patcher_sites_table as _sites_table

# Re-export public symbols from the sites table without exceeding the
# WPS235 "imported names from a module" cap. Tests and external callers
# import these by name from ``easter_hermes_sorry_skills._patcher_sites``,
# so each name is bound below; the actual values live in the table.
S1_CAP_SITE = _sites_table.S1_CAP_SITE
S1_CAP_SITE_FALLBACK = _sites_table.S1_CAP_SITE_FALLBACK
TOOLS_SKILL_UTILS_REL = _sites_table.TOOLS_SKILL_UTILS_REL
Anchor = _sites_table.Anchor
Site = _sites_table.Site
