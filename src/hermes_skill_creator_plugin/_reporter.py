"""src/hermes_skill_creator_plugin/_reporter.py

Format text/JSON output and sort rows for the reporter. Owns: hermes_skill_creator_plugin.

See also: plans/13-script-3-report.md

n/a-vs-0 (binding, V8/W4 fix): render `n/a` iff the Curator row's
`_persisted` flag is `False` (or the Curator module is absent). Render the
recorded integer when `_persisted` is `True`, even if the count is `0`.
We NEVER call `get_record()` (the backfill accessor) in the n/a decision
path — it always backfills `_empty_record()` and would collapse
"never tracked" into a zeroed record.

TDD test cases for this module:
  test_format_text_columns_present
  test_format_text_truncates_description_to_60
  test_format_text_total_row
  test_format_text_alignment
  test_format_json_shape
  test_format_json_deterministic_with_frozen_time
  test_format_json_includes_pct_of_cap
  test_sort_rows_by_tokens_desc
  test_sort_rows_by_use_count_desc_with_na_last
  test_sort_rows_by_last_used_at_desc_with_na_last
  test_sort_rows_stable_secondary_key_by_name
  test_na_renders_when_persisted_false
  test_zero_renders_when_persisted_true
  test_na_when_curator_absent
  test_no_call_to_get_record
"""

from __future__ import annotations

# Curator's 6 documented field names (verified against tools/skill_usage.py:463-468).
DOCUMENTED_USAGE_FIELDS = frozenset(
    {
        "use_count",
        "view_count",
        "patch_count",
        "last_used_at",
        "last_viewed_at",
        "last_patched_at",
    }
)

# Columns rendered in the plain-text table (in this fixed order).
TEXT_COLUMNS = (
    "profile",
    "name",
    "description",
    "tokens",
    "use_count",
    "view_count",
    "patch_count",
    "last_used_at",
    "last_viewed_at",
    "last_patched_at",
    "pct_of_cap",
)

# ---------------------------------------------------------------------------
# Re-exports — keep the public surface stable for tests / external callers.
# ---------------------------------------------------------------------------

from hermes_skill_creator_plugin._reporter_format import (
    _format_value_for_text,
    _skill_to_dict,
    format_json,
    format_text,
)
from hermes_skill_creator_plugin._reporter_models import ProfileSection, SkillRow
from hermes_skill_creator_plugin._reporter_sort import (
    _sort_key,
    _truncate_for_display,
    make_row,
    sort_rows,
)

__all__ = [
    "DOCUMENTED_USAGE_FIELDS",
    "TEXT_COLUMNS",
    "SkillRow",
    "ProfileSection",
    "make_row",
    "sort_rows",
    "format_text",
    "format_json",
    "_truncate_for_display",
    "_format_value_for_text",
    "_skill_to_dict",
    "_sort_key",
]
