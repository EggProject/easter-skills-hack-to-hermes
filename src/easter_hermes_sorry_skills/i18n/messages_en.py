"""English UI messages for the easter-hermes-sorry-skills-plugin.

See also: plans/03-plugin-spec.md (owner)

Single-language contract (no bilingual in-line format):
  - every constant below is plain English text (no ``[hu]`` text, no
    Hungarian diacritics).
  - runtime language selection is driven by ``easter_hermes_sorry_skills
    ._i18n_pick.pick(lang)`` returning either this module or
    ``messages_hu``.
  - no module constant may contain ``"[en]"``, ``"[hu]"``, ``"/ [hu]"``,
    or ``"/ [en]"`` substrings.

TDD test cases:
  test_messages_en_contains_required_keys
  test_messages_en_is_plain_english
"""

# Cap-state advisory (plain English). Emitted every time the 60-char
# skill-description cap is detected as still un-raised in the operator's
# Hermes checkout (no marker-file gating, single-language via pick(lang)).
ADVISORY_CAP = (
    "The 60-character skill-description cap is un-raised in your Hermes "
    "checkout. Run `easter-hermes-sorry-skills-patch-hermes` to raise it."
)

# Script #3 (reporter) messages — plain English.
REPORT_HELP_SHORT = "Profile skill token + usage reporter"
REPORT_HELP_LONG = (
    "Lists the ENABLED skills for a profile, tokenizes the rendered "
    "name+description, and joins view/use/patch + last_used_at counts "
    "from the Curator."
)
REPORT_OPT_PROFILE = "Report a single profile; default iterates the `hermes` (default) profile AND every named profile."
REPORT_OPT_SORT = "Reorder rows: tokens | use_count | last_used_at. Default: tokens."
REPORT_OPT_FORMAT = "Output format: text (default) | json."
REPORT_OPT_JSON = "Write the report to PATH (default: ./skill-report.json when --format=json; otherwise ignored)."
REPORT_OPT_HELP = "Show help and exit."
REPORT_OPT_VERBOSE = "Print detailed per-cell diagnostics to stderr (every cell value + section summary)."

REPORT_USAGE_HEADER = "Usage: easter-hermes-sorry-skills-report [OPTIONS]"
REPORT_TOKENIZER_UNAVAILABLE = "tokenizer unavailable, falling back to chars/4"
FALLBACK_WARNING = "tokenizer unavailable, falling back to chars/4"
REPORT_ENABLED_DETECTION_UNAVAILABLE = "enabled-detection module unavailable, cannot enumerate skills"
REPORT_REJECTED_APPLY = "apply not supported on the reporter"
REPORT_REJECTED_EMIT_MIGRATION_NOTE = "emit-migration-note is not a reporter flag"
REPORT_REJECTED_WRITE_REPORT = "write-report is not a reporter flag"
REPORT_JSON_PATH_INSIDE_HERMES_HOME = "--json path resolves under HERMES_HOME, refusing"
REPORT_NO_PROFILES = "no profiles found"

# Patcher preflight diagnostics.
CIRCULAR_IMPORT_PREFLIGHT = (
    "potential circular import detected in agent/skill_utils.py (imports from tools.skills_tool)"
)

# Patcher diagnostics.
TARGET_REQUIRED = "--target is required"
TARGET_IS_HERMES_AGENT = "refusing to patch the live hermes-agent checkout: {resolved}"
TARGET_MISSING_SKILL_UTILS = "target missing agent/skill_utils.py: {path}"
LINE_DRIFT = "line drift detected at site {site_id} (line {line})"
VALIDATION_FAILED = "validation failed at site {site_id}"
OK_ALREADY_PATCHED = "OK: site {site_id} already patched"
OK_PATCHED = "OK: site {site_id} patched successfully"
PERMISSION_DENIED = "permission denied writing {path}"
IO_ERROR = "I/O error writing {path}: {error}"
CROSS_FS_WARN = "warning: target and tmp live on different filesystems"
TEXT_DRIFT = "text drift detected at site {site_id}: expected {expected!r}, actual {actual!r}"

# Dry-run plan output (plain English).
DRY_RUN_PLAN_HEADER = "plan for {target}:"
DRY_RUN_PREFLIGHT_WARNING = "WARNING: target is the live hermes-agent checkout, no patches will be applied"
DRY_RUN_PATCH_LINE = "would patch: {file_path} (site {site_id})"
DRY_RUN_DIFF_LINE_OLD = "  line {line}: - {old}"
DRY_RUN_DIFF_LINE_NEW = "  line {line}: + {new}"
DRY_RUN_PLAN_SUMMARY = "{count} patch(es) would be applied"
DRY_RUN_NOT_APPLIED = "WARNING: --dry-run mode, {count} patches were NOT applied"
DRY_RUN_APPLIED = "{count} patches applied"

# Column headers (English).
COL_PROFILE = "profile"
COL_NAME = "name"
COL_DESCRIPTION = "description"
COL_TOKENS = "tokens"
COL_USE_COUNT = "use_count"
COL_VIEW_COUNT = "view_count"
COL_PATCH_COUNT = "patch_count"
COL_LAST_USED_AT = "last_used_at"
COL_LAST_VIEWED_AT = "last_viewed_at"
COL_LAST_PATCHED_AT = "last_patched_at"
COL_PCT_OF_CAP = "% of cap"
NA_VALUE = "n/a"
TOTAL_ROW_LABEL = "total"

# Backwards-compat aliases (original lowercase / short names preserved for
# downstream callers in cli_report_* / test_* modules — simple re-bindings
# of the single-language constants above).
report_help_short = REPORT_HELP_SHORT
report_help_long = REPORT_HELP_LONG
report_opt_profile = REPORT_OPT_PROFILE
report_opt_sort = REPORT_OPT_SORT
report_opt_format = REPORT_OPT_FORMAT
report_opt_json = REPORT_OPT_JSON
report_opt_help = REPORT_OPT_HELP
report_opt_verbose = REPORT_OPT_VERBOSE
report_usage_header = REPORT_USAGE_HEADER
report_tokenizer_unavailable = REPORT_TOKENIZER_UNAVAILABLE
report_enabled_detection_unavailable = REPORT_ENABLED_DETECTION_UNAVAILABLE
report_rejected_apply = REPORT_REJECTED_APPLY
report_rejected_emit_migration_note = REPORT_REJECTED_EMIT_MIGRATION_NOTE
report_rejected_write_report = REPORT_REJECTED_WRITE_REPORT
report_json_path_inside_hermes_home = REPORT_JSON_PATH_INSIDE_HERMES_HOME
report_no_profiles = REPORT_NO_PROFILES
col_profile = COL_PROFILE
col_name = COL_NAME
col_description = COL_DESCRIPTION
col_tokens = COL_TOKENS
col_use_count = COL_USE_COUNT
col_view_count = COL_VIEW_COUNT
col_patch_count = COL_PATCH_COUNT
col_last_used_at = COL_LAST_USED_AT
col_last_viewed_at = COL_LAST_VIEWED_AT
col_last_patched_at = COL_LAST_PATCHED_AT
col_pct_of_cap = COL_PCT_OF_CAP
na_value = NA_VALUE
total_row_label = TOTAL_ROW_LABEL
