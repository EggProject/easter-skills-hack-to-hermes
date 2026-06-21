"""src/hermes_skill_creator_plugin/_enabled_detection_filter.py

Re-export hub for the enabled-detection filter primitives. The actual
implementations live in sibling modules to keep this file under
wemake WPS202 (module members <= 7):

- :mod:`._enabled_detection_disabled` — ``disabled_set``, ``drop_disabled``.
- :mod:`._enabled_detection_platform` — ``platform_blocked``,
  ``plat_value_blocks``, ``platform_disables``, ``conditional_excluded``.
- :mod:`._enabled_detection_skills` — ``find_skill_md``,
  ``apply_platform_filter``, ``apply_conditional_exclusions``.

The public names are re-bound as module-level attributes here so
existing imports (``from hermes_skill_creator_plugin._enabled_detection_filter
import ...``) keep working under mypy strict
(``implicit_reexport = false``).
"""

from __future__ import annotations

from hermes_skill_creator_plugin import (
    _enabled_detection_disabled as _disabled_mod,
)
from hermes_skill_creator_plugin import (
    _enabled_detection_platform as _platform_mod,
)
from hermes_skill_creator_plugin import (
    _enabled_detection_skills as _skills_mod,
)

apply_conditional_exclusions = _skills_mod.apply_conditional_exclusions
apply_platform_filter = _skills_mod.apply_platform_filter
conditional_excluded = _platform_mod.conditional_excluded
disabled_set = _disabled_mod.disabled_set
drop_disabled = _disabled_mod.drop_disabled
find_skill_md = _skills_mod.find_skill_md
plat_value_blocks = _platform_mod.plat_value_blocks
platform_blocked = _platform_mod.platform_blocked
platform_disables = _platform_mod.platform_disables
