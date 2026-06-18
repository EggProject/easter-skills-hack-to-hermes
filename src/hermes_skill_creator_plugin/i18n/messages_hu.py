"""Hungarian UI messages for the hermes-skill-creator-plugin.

See also: plans/03-plugin-spec.md (owner)

TDD test cases:
  test_messages_hu_contains_required_keys
"""

# Cap-state advisory (HU half). Emitted when the 60-character skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_HU = (
    "[hu] A 60 karakteres skill-leírás-korlát még nincs felemelve a Hermes "
    "checkoutban. Futtasd a `hermes-skill-creator-patch` parancsot a felemeléshez."
)

# Reporter messages (mirrored with messages_en.py).
report_help_short = "[hu] Profil skill token + használati riport / [en] Profile skill token + usage reporter"
report_help_long = (
    "[hu] Kilistázza egy profil ENGEDÉLYEZETT skilljeit, tokenizálja a renderelt "
    "name+description szöveget, és a Curator-ból kéri a view/use/patch + "
    "last_used_at számokat. / [en] Lists the ENABLED skills for a profile, "
    "tokenizes the rendered name+description, and joins view/use/patch + "
    "last_used_at counts from the Curator."
)
report_opt_profile = (
    "[hu] Egyetlen profil riportja; alapértelmezetten a `hermes` (alap) profil "
    "ÉS minden elnevezett profil. / [en] Report a single profile; default "
    "iterates the `hermes` (default) profile AND every named profile."
)
report_opt_sort = (
    "[hu] Sorok rendezése: tokens | use_count | last_used_at. Alapértelmezett: "
    "tokens. / [en] Reorder rows: tokens | use_count | last_used_at. Default: tokens."
)
report_opt_format = (
    "[hu] Kimeneti formátum: text (alapértelmezett) | json. / [en] Output format: " "text (default) | json."
)
report_opt_json = (
    "[hu] A riport kiírása PATH-ba (alapértelmezett: ./skill-report.json, ha "
    "--format=json; egyébként figyelmen kívül hagyva). / [en] Write the report "
    "to PATH (default: ./skill-report.json when --format=json; otherwise ignored)."
)
report_opt_help = "[hu] Kétnyelvű EN+HU help megjelenítése. / [en] Show bilingual EN+HU help."

report_usage_header = (
    "[hu] Használat: hermes-skill-creator-report [OPTIONS] / [en] Usage: " "hermes-skill-creator-report [OPTIONS]"
)
report_tokenizer_unavailable = (
    "[hu] a tokenizer nem elérhető, chars/4 becslés / [en] tokenizer " "unavailable, falling back to chars/4"
)
report_enabled_detection_unavailable = (
    "[hu] az enabled-detection modul nem elérhető, a skillek nem listázhatók / [en] "
    "enabled-detection module unavailable, cannot enumerate skills"
)
report_rejected_apply = "[hu] az apply nem támogatott a riporton / [en] apply not supported on the reporter"
report_rejected_emit_migration_note = (
    "[hu] az emit-migration-note nem riport-flag / [en] emit-migration-note is " "not a reporter flag"
)
report_rejected_write_report = "[hu] a write-report nem riport-flag / [en] write-report is not a reporter flag"
report_json_path_inside_hermes_home = (
    "[hu] a --json útvonala a HERMES_HOME alá esik, megtagadva / [en] --json "
    "path resolves under HERMES_HOME, refusing"
)
report_no_profiles = "[hu] nem találhatók profilok / [en] no profiles found"

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
    "[hu] a célpontból hiányzik az agent/skill_utils.py: {path} / " "[en] target missing agent/skill_utils.py: {path}"
)
FORCE_REQUIRES_I_ACCEPT = (
    "[hu] a --force használatához --i-accept-line-drift szükséges / " "[en] --force requires --i-accept-line-drift"
)
LINE_DRIFT = (
    "[hu] sor-eltérés a {site_id} helyen (sor {line}) / " "[en] line drift detected at site {site_id} (line {line})"
)
VALIDATION_FAILED = "[hu] az érvényesítés sikertelen a {site_id} helyen / " "[en] validation failed at site {site_id}"
OK_ALREADY_PATCHED = "[hu] OK: a {site_id} hely már javítva / [en] OK: site {site_id} already patched"
OK_PATCHED = "[hu] OK: a {site_id} hely sikeresen javítva / " "[en] OK: site {site_id} patched successfully"
PERMISSION_DENIED = "[hu] írási engedély megtagadva: {path} / [en] permission denied writing {path}"
IO_ERROR = "[hu] I/O hiba a {path} írásakor: {error} / " "[en] I/O error writing {path}: {error}"
CROSS_FS_WARN = (
    "[hu] figyelmeztetés: a cél és az ideiglenes könyvtár különböző "
    "fájlrendszeren van / [en] warning: target and tmp live on different filesystems"
)
FORCE_AUDIT_LOG = (
    "[hu] --force audit bejegyzés hozzáfűzve: timestamp={timestamp} site={site_id} "
    "diff_sha256={diff_sha} target={target} / "
    "[en] --force audit log entry appended: timestamp={timestamp} site={site_id} "
    "diff_sha256={diff_sha} target={target}"
)
TEXT_DRIFT = "[hu] szöveg-eltérés a {site_id} helyen / " "[en] text drift detected at site {site_id}"
MIGRATION_REGENERATED = (
    "[hu] migrációs jegyzet újragenerálva itt: {path} / " "[en] migration note regenerated at {path}"
)

# Column headers (Hungarian half).
col_profile = "profil"
col_name = "név"
col_description = "leírás"
col_tokens = "tokenek"
col_use_count = "használat_száma"
col_view_count = "megtekintés_száma"
col_patch_count = "patch_száma"
col_last_used_at = "utolsó_használat"
col_last_viewed_at = "utolsó_megtekintés"
col_last_patched_at = "utolsó_patch"
col_pct_of_cap = "% a plafonból"
na_value = "n/a"
total_row_label = "összesen"

# M dict - grouped keys for cli_profiles.py (Script #2 per-profile audit/flip)
M = {
    # CLI: hermes-skill-creator-profiles
    "profiles_help_short": (
        "Profilonkénti audit/csere a migrált skill-creator skillhez (Script #2). "
        "A skill-creator skillet a sík ~/.hermes/skills/skill-creator/ útvonalra "
        "telepíti/cseréli minden profil alatt. Alap mód: száraz futás; "
        "a --apply kapcsolóval hajtódnak végre az írások."
    ),
    "profiles_help_long": (
        "Végigmegy minden Hermes profilon (az alap 'hermes' profil és minden "
        "a hermes_cli.profiles.list_profiles() által visszaadott elnevezett profil), "
        "és auditálja a profilonkénti skill fát. --apply esetén a script meghívja "
        "a hermes_cli.skills_hub.do_install() függvényt, hogy a migrált "
        "skill-creator a helyére kerüljön a ~/.hermes/skills/skill-creator/ útvonalon, "
        "majd törli a skill rendszer-prompt gyorsítótárát. A --json PATH kapcsolóval "
        "a determinisztikus JSON jelentés a PATH helyre íródik. A --yes kapcsoló "
        "elnyomja az interaktív TTY megerősítést. A script a hermes_home_scope() "
        "kontextuskezelő alatt fut, tükrözve a HERMES_HOME-ot mind az override "
        "tokenben, mind az os.environ['HERMES_HOME']-ban."
    ),
    "profiles_opt_apply": ("Végrehajtja az írásokat (alap: száraz futás)."),
    "profiles_opt_audit": ("Csak audit; nem hajt végre írást (alias az alap módhoz)."),
    "profiles_opt_profile": ("A futást egyetlen profilra korlátozza (alap: minden profil)."),
    "profiles_opt_json": ("A determinisztikus JSON jelentést a PATH helyre írja (alap: ./profile-audit.json)."),
    "profiles_opt_yes": ("Elnyomja az interaktív TTY megerősítést (CI / nem-TTY futás)."),
    "profiles_opt_skip_install": ("Csak audit; nem hívja meg a hub telepítőt."),
    "profiles_opt_frozen_time": ("A jelentés generated_at mezőjét stabil ISO 8601 UTC értékre rögzíti."),
    "profiles_opt_help": ("Megjeleníti ezt a kétnyelvű súgót és kilép."),
    "profiles_section_usage_en": "Usage (English)",
    "profiles_section_usage_hu": "Használat (magyar)",
    # Bilingual runtime messages (Hungarian half)
    "profiles_msg_scanning": "Profilok vizsgálata...",
    "profiles_msg_profile_count": "{n} profil vizsgálandó.",
    "profiles_msg_audit_default": ("Alap mód: száraz futás (használja --apply kapcsolót a végrehajtáshoz)."),
    "profiles_msg_applying": "Profilonkénti alkalmazás...",
    "profiles_msg_profile_audit": ("profil={name} jelenleg_letiltva={disabled} jelenleg_telepítve={installed}"),
    "profiles_msg_diff": (
        "diff hozzáadott_letiltva={ad} eltávolított_letiltva={rd} "
        "hozzáadott_telepítve={ai} eltávolított_telepítve={ri}"
    ),
    "profiles_msg_cache_warn": ("profil={name} clear_skills_system_prompt_cache kivételt dobott: {err} " "(folytatás)"),
    "profiles_msg_hub_error": ("profil={name} hub telepítés sikertelen: {err} (folytatás)."),
    "profiles_msg_json_written": "Jelentés írva ide: {path}.",
    "profiles_msg_refuse_no_yes": (
        "A futás megtagadva az élő HERMES_HOME ellen --yes nélkül. " "Futtassa újra --yes kapcsolóval a megerősítéshez."
    ),
    "profiles_msg_no_profiles": ("Nem található profil (alap + elnevezett). Nincs mit vizsgálni."),
    "profiles_msg_done": "Kész. Feldolgozott profilok: {n}.",
}
