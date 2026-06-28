"""Hungarian UI messages for the easter-hermes-sorry-skills-plugin.

See also: plans/03-plugin-spec.md (owner)

Single-language contract (no bilingual in-line format):
  - every constant below is plain Hungarian text (no ``[en]`` text).
  - runtime language selection is driven by ``easter_hermes_sorry_skills
    ._i18n_pick.pick(lang)`` returning either this module or
    ``messages_en``.
  - no module constant may contain ``"[en]"``, ``"[hu]"``, ``"/ [hu]"``,
    or ``"/ [en]"`` substrings.

TDD test cases:
  test_messages_hu_contains_required_keys
  test_messages_hu_is_plain_hungarian
"""

# Cap-state advisory (plain Hungarian). Emitted every time the 60-char
# skill-description cap is detected as still un-raised in the operator's
# Hermes checkout (no marker-file gating, single-language via pick(lang)).
ADVISORY_CAP = (
    "A 60 karakteres skill-leírás-korlát még nincs felemelve a Hermes "
    "checkoutban. Futtasd a `easter-hermes-sorry-skills-patch-hermes` parancsot "
    "a felemeléshez."
)

# Reporter messages (plain Hungarian, mirrored with messages_en.py).
REPORT_HELP_SHORT = "Profil skill token + használati riport"
REPORT_HELP_LONG = (
    "Kilistázza egy profil ENGEDÉLYEZETT skilljeit, tokenizálja a "
    "renderelt name+description szöveget, és a Curator-ból kéri a "
    "view/use/patch + last_used_at számokat."
)
REPORT_OPT_PROFILE = "Egyetlen profil riportja; alapértelmezetten a `hermes` (alap) profil ÉS minden elnevezett profil."
REPORT_OPT_SORT = "Sorok rendezése: tokens | use_count | last_used_at. Alapértelmezett: tokens."
REPORT_OPT_FORMAT = "Kimeneti formátum: text (alapértelmezett) | json."
REPORT_OPT_JSON = (
    "A riport kiírása PATH-ba (alapértelmezett: ./skill-report.json, "
    "ha --format=json; egyébként figyelmen kívül hagyva)."
)
REPORT_OPT_HELP = "Súgó megjelenítése és kilépés."
REPORT_OPT_VERBOSE = (
    "Részletes, cellánkénti diagnosztika a stderr-re "
    "(minden cella értéke + szekció összegzés). "
    "Működik --json-nel is (csak stderr)."
)

REPORT_USAGE_HEADER = "Használat: easter-hermes-sorry-skills-report [OPTIONS]"
REPORT_TOKENIZER_UNAVAILABLE = "a tokenizer nem elérhető, chars/4 becslés"
FALLBACK_WARNING = "a tokenizer nem elérhető, chars/4 becslés"
REPORT_ENABLED_DETECTION_UNAVAILABLE = "az enabled-detection modul nem elérhető, a skillek nem listázhatók"
REPORT_REJECTED_APPLY = "az apply nem támogatott a riporton"
REPORT_REJECTED_EMIT_MIGRATION_NOTE = "az emit-migration-note nem riport-flag"
REPORT_REJECTED_WRITE_REPORT = "a write-report nem riport-flag"
REPORT_JSON_PATH_INSIDE_HERMES_HOME = "a --json útvonala a HERMES_HOME alá esik, megtagadva"
REPORT_NO_PROFILES = "nem találhatók profilok"

# Patcher preflight diagnostics.
CIRCULAR_IMPORT_PREFLIGHT = (
    "potenciális körkörös import észlelve az agent/skill_utils.py-ban (importál a tools.skills_tool-ból)"
)

# Patcher diagnostics.
TARGET_REQUIRED = "a --target megadása kötelező"
TARGET_IS_HERMES_AGENT = "az élő hermes-agent checkout patchelése megtagadva: {resolved}"
TARGET_MISSING_SKILL_UTILS = "a célpontból hiányzik az agent/skill_utils.py: {path}"
LINE_DRIFT = "sor-eltérés a {site_id} helyen (sor {line})"
VALIDATION_FAILED = "az érvényesítés sikertelen a {site_id} helyen"
OK_ALREADY_PATCHED = "OK: a {site_id} hely már javítva"
OK_PATCHED = "OK: a {site_id} hely sikeresen javítva"
PERMISSION_DENIED = "írási engedély megtagadva: {path}"
IO_ERROR = "I/O hiba a {path} írásakor: {error}"
CROSS_FS_WARN = "figyelmeztetés: a cél és az ideiglenes könyvtár különböző fájlrendszeren van"
TEXT_DRIFT = "szöveg-eltérés a {site_id} helyen: elvárt {expected!r}, tényleges {actual!r}"

# Dry-run plan output (plain Hungarian).
DRY_RUN_PLAN_HEADER = "terv a {target} útvonalra:"
DRY_RUN_PREFLIGHT_WARNING = "FIGYELEM: a target az élő hermes-agent checkout, nem történik patch"
DRY_RUN_PATCH_LINE = "patchelné: {file_path} ({site_id} site)"
DRY_RUN_DIFF_LINE_OLD = "  line {line}: - {old}"
DRY_RUN_DIFF_LINE_NEW = "  line {line}: + {new}"
DRY_RUN_PLAN_SUMMARY = "{count} patch kerülne alkalmazásra"
DRY_RUN_NOT_APPLIED = "FIGYELEM: --dry-run módban vagyunk, {count} patch NEM történt meg"
DRY_RUN_APPLIED = "{count} patch alkalmazva"

# Column headers (Hungarian).
COL_PROFILE = "profil"
COL_NAME = "név"
COL_DESCRIPTION = "leírás"
COL_TOKENS = "tokenek"
COL_USE_COUNT = "használat_száma"
COL_VIEW_COUNT = "megtekintés_száma"
COL_PATCH_COUNT = "patch_száma"
COL_LAST_USED_AT = "utolsó_használat"
COL_LAST_VIEWED_AT = "utolsó_megtekintés"
COL_LAST_PATCHED_AT = "utolsó_patch"
COL_PCT_OF_CAP = "% a plafonból"
NA_VALUE = "n/a"
TOTAL_ROW_LABEL = "összesen"

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
