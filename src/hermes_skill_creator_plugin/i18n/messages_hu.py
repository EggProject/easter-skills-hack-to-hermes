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
report_help_short = (
    "[hu] Profil skill token + használati riport / [en] Profile skill token + usage reporter"
)
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
    "[hu] Kimeneti formátum: text (alapértelmezett) | json. / [en] Output format: "
    "text (default) | json."
)
report_opt_json = (
    "[hu] A riport kiírása PATH-ba (alapértelmezett: ./skill-report.json, ha "
    "--format=json; egyébként figyelmen kívül hagyva). / [en] Write the report "
    "to PATH (default: ./skill-report.json when --format=json; otherwise ignored)."
)
report_opt_help = "[hu] Kétnyelvű EN+HU help megjelenítése. / [en] Show bilingual EN+HU help."

report_usage_header = (
    "[hu] Használat: hermes-skill-creator-report [OPTIONS] / [en] Usage: "
    "hermes-skill-creator-report [OPTIONS]"
)
report_tokenizer_unavailable = (
    "[hu] a tokenizer nem elérhető, chars/4 becslés / [en] tokenizer "
    "unavailable, falling back to chars/4"
)
report_enabled_detection_unavailable = (
    "[hu] az enabled-detection modul nem elérhető, a skillek nem listázhatók / [en] "
    "enabled-detection module unavailable, cannot enumerate skills"
)
report_rejected_apply = (
    "[hu] az apply nem támogatott a riporton / [en] apply not supported on the reporter"
)
report_rejected_emit_migration_note = (
    "[hu] az emit-migration-note nem riport-flag / [en] emit-migration-note is "
    "not a reporter flag"
)
report_rejected_write_report = (
    "[hu] a write-report nem riport-flag / [en] write-report is not a reporter flag"
)
report_json_path_inside_hermes_home = (
    "[hu] a --json útvonala a HERMES_HOME alá esik, megtagadva / [en] --json "
    "path resolves under HERMES_HOME, refusing"
)
report_no_profiles = "[hu] nem találhatók profilok / [en] no profiles found"

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