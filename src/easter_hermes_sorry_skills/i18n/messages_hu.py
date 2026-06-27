"""Hungarian UI messages for the easter-hermes-sorry-skills-plugin.

See also: plans/03-plugin-spec.md (owner)

TDD test cases:
  test_messages_hu_contains_required_keys
"""

from types import MappingProxyType

# Cap-state advisory (HU half). Emitted when the 60-character skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_HU = (
    "[hu] A 60 karakteres skill-leírás-korlát még nincs felemelve a Hermes "
    "checkoutban. Futtasd a `easter-hermes-sorry-skills-patch-hermes` parancsot a "
    "felemeléshez."
)

# Reporter messages (mirrored with messages_en.py).
REPORT_HELP_SHORT = "[hu] Profil skill token + használati riport / [en] Profile skill token + usage reporter"
REPORT_HELP_LONG = (
    "[hu] Kilistázza egy profil ENGEDÉLYEZETT skilljeit, tokenizálja a "
    "renderelt name+description szöveget, és a Curator-ból kéri a "
    "view/use/patch + last_used_at számokat. / "
    "[en] Lists the ENABLED skills for a profile, tokenizes the rendered "
    "name+description, and joins view/use/patch + last_used_at counts "
    "from the Curator."
)
REPORT_OPT_PROFILE = (
    "[hu] Egyetlen profil riportja; alapértelmezetten a `hermes` (alap) "
    "profil ÉS minden elnevezett profil. / "
    "[en] Report a single profile; default iterates the `hermes` (default) "
    "profile AND every named profile."
)
REPORT_OPT_SORT = (
    "[hu] Sorok rendezése: tokens | use_count | last_used_at. "
    "Alapértelmezett: tokens. / "
    "[en] Reorder rows: tokens | use_count | last_used_at. Default: tokens."
)
REPORT_OPT_FORMAT = (
    "[hu] Kimeneti formátum: text (alapértelmezett) | json. / [en] Output format: text (default) | json."
)
REPORT_OPT_JSON = (
    "[hu] A riport kiírása PATH-ba (alapértelmezett: "
    "./skill-report.json, ha --format=json; egyébként figyelmen kívül "
    "hagyva). / [en] Write the report to PATH "
    "(default: ./skill-report.json when --format=json; otherwise ignored)."
)
REPORT_OPT_HELP = "[hu] Kétnyelvű EN+HU help megjelenítése. / [en] Show bilingual EN+HU help."
REPORT_OPT_VERBOSE = (
    "[hu] Részletes, cellánkénti diagnosztika a stderr-re "
    "(minden cella értéke + szekció összegzés). "
    "Működik --json-nel is (csak stderr). / "
    "[en] Print detailed per-cell diagnostics to stderr "
    "(every cell value + section summary). "
    "Works with --json (stderr only)."
)

REPORT_USAGE_HEADER = (
    "[hu] Használat: easter-hermes-sorry-skills-report [OPTIONS] / "
    "[en] Usage: easter-hermes-sorry-skills-report [OPTIONS]"
)
REPORT_TOKENIZER_UNAVAILABLE = (
    "[hu] a tokenizer nem elérhető, chars/4 becslés / [en] tokenizer unavailable, falling back to chars/4"
)
REPORT_ENABLED_DETECTION_UNAVAILABLE = (
    "[hu] az enabled-detection modul nem elérhető, a skillek nem "
    "listázhatók / [en] enabled-detection module unavailable, "
    "cannot enumerate skills"
)
REPORT_REJECTED_APPLY = "[hu] az apply nem támogatott a riporton / [en] apply not supported on the reporter"
REPORT_REJECTED_EMIT_MIGRATION_NOTE = (
    "[hu] az emit-migration-note nem riport-flag / [en] emit-migration-note is not a reporter flag"
)
REPORT_REJECTED_WRITE_REPORT = "[hu] a write-report nem riport-flag / [en] write-report is not a reporter flag"
REPORT_JSON_PATH_INSIDE_HERMES_HOME = (
    "[hu] a --json útvonala a HERMES_HOME alá esik, megtagadva / [en] --json path resolves under HERMES_HOME, refusing"
)
REPORT_NO_PROFILES = "[hu] nem találhatók profilok / [en] no profiles found"

# Patcher preflight diagnostics (HU half — EN half lives in messages_en.py).
CIRCULAR_IMPORT_PREFLIGHT = (
    "[hu] potenciális körkörös import észlelve az agent/skill_utils.py-ban "
    "(importál a tools.skills_tool-ból) / [en] potential circular import "
    "detected in agent/skill_utils.py (imports from tools.skills_tool)"
)

# Patcher diagnostics (HU half — mirrored with messages_en.py).
TARGET_REQUIRED = "[hu] a --target megadása kötelező / [en] --target is required"
TARGET_IS_HERMES_AGENT = (
    "[hu] az élő hermes-agent checkout patchelése megtagadva: {resolved} / "
    "[en] refusing to patch the live hermes-agent checkout: {resolved}"
)
TARGET_MISSING_SKILL_UTILS = (
    "[hu] a célpontból hiányzik az agent/skill_utils.py: {path} / [en] target missing agent/skill_utils.py: {path}"
)
LINE_DRIFT = (
    "[hu] sor-eltérés a {site_id} helyen (sor {line}) / [en] line drift detected at site {site_id} (line {line})"
)
VALIDATION_FAILED = "[hu] az érvényesítés sikertelen a {site_id} helyen / [en] validation failed at site {site_id}"
OK_ALREADY_PATCHED = "[hu] OK: a {site_id} hely már javítva / [en] OK: site {site_id} already patched"
OK_PATCHED = "[hu] OK: a {site_id} hely sikeresen javítva / [en] OK: site {site_id} patched successfully"
PERMISSION_DENIED = "[hu] írási engedély megtagadva: {path} / [en] permission denied writing {path}"
IO_ERROR = "[hu] I/O hiba a {path} írásakor: {error} / [en] I/O error writing {path}: {error}"
CROSS_FS_WARN = (
    "[hu] figyelmeztetés: a cél és az ideiglenes könyvtár különböző "
    "fájlrendszeren van / [en] warning: target and tmp live on different "
    "filesystems"
)
TEXT_DRIFT = (
    "[hu] szöveg-eltérés a {site_id} helyen: elvárt {expected!r}, "
    "tényleges {actual!r} / [en] text drift detected at site {site_id}: "
    "expected {expected!r}, actual {actual!r}"
)

# Dry-run plan output (HU half — bilingual single-string format).
# Single-string bilingual format: "[hu] ... / [en] ...".
DRY_RUN_PLAN_HEADER = "[hu] terv a {target} útvonalra: / [en] plan for {target}:"
DRY_RUN_PREFLIGHT_WARNING = (
    "[hu] FIGYELEM: a target az élő hermes-agent checkout, "
    "nem történik patch / "
    "[en] WARNING: target is the live hermes-agent checkout, "
    "no patches will be applied"
)
DRY_RUN_PATCH_LINE = "[hu] patchelné: {file_path} ({site_id} site) / [en] would patch: {file_path} (site {site_id})"
DRY_RUN_DIFF_LINE_OLD = "[hu]   line {line}: - {old} / [en]   line {line}: - {old}"
DRY_RUN_DIFF_LINE_NEW = "[hu]   line {line}: + {new} / [en]   line {line}: + {new}"
DRY_RUN_PLAN_SUMMARY = "[hu] {count} patch kerülne alkalmazásra / [en] {count} patch(es) would be applied"
DRY_RUN_NOT_APPLIED = (
    "[hu] FIGYELEM: --dry-run módban vagyunk, {count} patch NEM történt meg / "
    "[en] WARNING: --dry-run mode, {count} patches were NOT applied"
)
DRY_RUN_APPLIED = "[hu] {count} patch alkalmazva / [en] {count} patches applied"

# Column headers (Hungarian half).
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

# Backwards-compat aliases (original lowercase / short names preserved for any
# downstream caller that referenced them).
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

# Profiles dict - grouped keys for cli_profiles.py (Script #2 per-profile
# audit/flip). Renamed from ``M`` to ``HU_MESSAGES`` (WPS111) and wrapped
# in MappingProxyType to satisfy WPS407 (mutable module constant).
HU_MESSAGES = MappingProxyType(
    {
        # CLI: easter-hermes-sorry-skills-profiles
        "profiles_help_short": (
            "Profilonkénti CSAK OLVASÁS audit a migrált skill-creator "
            "skillhez (Script #2). A script soha nem ír — a "
            "~/.hermes/skills/skill-creator/ útvonalat vizsgálja minden "
            "profil alatt, és kétnyelvű EN/HU riportot ír. A --json "
            "kapcsolóval géppel olvasható kimenetet kaphatunk."
        ),
        "profiles_help_long": (
            "Végigmegy minden Hermes profilon (az alap 'hermes' profil és "
            "minden a hermes_cli.profiles.list_profiles() által visszaadott "
            "elnevezett profil), és auditálja a skill fát a "
            "~/.hermes/skills/skill-creator/ útvonalon. A script szigorúan "
            "CSAK OLVAS: nem ír semmilyen fájlt, nem módosít konfigurációt. "
            "A script a hermes_home_scope() kontextuskezelő alatt fut, "
            "tükrözve a HERMES_HOME-ot mind az override tokenben, mind az "
            "os.environ['HERMES_HOME']-ban."
        ),
        "profiles_opt_json": (
            "A riport kiírása géppel olvasható JSON formátumban a stdout-ra (tooling/pipeline-okhoz)."
        ),
        "profiles_opt_verbose": (
            "Részletes, helyszínenkénti diagnosztika a stderr-re (nem zavarja a stdout kimenetet)."
        ),
        "report_opt_verbose": (
            "Részletes, cellánkénti diagnosztika a stderr-re (minden cella értéke + szekció összegzés)."
        ),
        "profiles_opt_profile": ("A futást egyetlen profilra korlátozza (alap: minden profil)."),
        "profiles_opt_help": ("Megjeleníti ezt a kétnyelvű súgót és kilép."),
        "profiles_section_usage_en": "Usage (English)",
        "profiles_section_usage_hu": "Használat (magyar)",
        # Bilingual runtime messages (Hungarian half)
        "profiles_msg_scanning": "Profilok vizsgálata...",
        "profiles_msg_profile_count": "{n} profil vizsgálandó.",
        "profiles_msg_applying": "Profilonkénti telepítés/csere...",
        "profiles_msg_profile_audit": ("profil={name} jelenleg_letiltva={disabled} jelenleg_telepítve={installed}"),
        "profiles_msg_diff": (
            "diff hozzáadott_letiltva={ad} eltávolított_letiltva={rd} "
            "hozzáadott_telepítve={ai} eltávolított_telepítve={ri}"
        ),
        "profiles_msg_cache_warn": (
            "profil={name} clear_skills_system_prompt_cache kivételt dobott: {err} (folytatás)"
        ),
        "profiles_msg_hub_error": ("profil={name} hub telepítés sikertelen: {err} (folytatás)."),
        "profiles_msg_no_profiles": ("Nem található profil (alap + elnevezett). Nincs mit vizsgálni."),
        "profiles_msg_done": "Kész. Feldolgozott profilok: {n}.",
    }
)
