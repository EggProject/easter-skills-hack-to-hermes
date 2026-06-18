"""English UI messages for the hermes-skill-creator-plugin.

See also: plans/03-plugin-spec.md (owner)

TDD test cases:
  test_messages_en_contains_required_keys
  test_messages_en_bilingual_format_for_console
"""

# Cap-state advisory (EN half). Emitted when the 60-char skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_EN = (
    "[en] The 60-character skill-description cap is un-raised in your Hermes "
    "checkout. Run `hermes-skill-creator-patch` to raise it."
)

# Script #3 (reporter) messages — bilingual format: [en] text / [hu] text.
report_help_short = (
    "[en] Profile skill token + usage reporter / [hu] Profil skill token + használati riport"
)
report_help_long = (
    "[en] Lists the ENABLED skills for a profile, tokenizes the rendered "
    "name+description, and joins view/use/patch + last_used_at counts "
    "from the Curator. / [hu] Kilistázza egy profil ENGEDÉLYEZETT skilljeit, "
    "tokenizálja a renderelt name+description szöveget, és a Curator-ból "
    "kéri a view/use/patch + last_used_at számokat."
)
report_opt_profile = (
    "[en] Report a single profile; default iterates the `hermes` (default) "
    "profile AND every named profile. / [hu] Egyetlen profil riportja; "
    "alapértelmezetten a `hermes` (alap) profil ÉS minden elnevezett profil."
)
report_opt_sort = (
    "[en] Reorder rows: tokens | use_count | last_used_at. Default: tokens. "
    "/ [hu] Sorok rendezése: tokens | use_count | last_used_at. "
    "Alapértelmezett: tokens."
)
report_opt_format = (
    "[en] Output format: text (default) | json. / [hu] Kimeneti formátum: "
    "text (alapértelmezett) | json."
)
report_opt_json = (
    "[en] Write the report to PATH (default: ./skill-report.json when "
    "--format=json; otherwise ignored). / [hu] A riport kiírása PATH-ba "
    "(alapértelmezett: ./skill-report.json, ha --format=json; egyébként figyelmen kívül hagyva)."
)
report_opt_help = "[en] Show bilingual EN+HU help. / [hu] Kétnyelvű EN+HU help megjelenítése."

report_usage_header = (
    "[en] Usage: hermes-skill-creator-report [OPTIONS] / [hu] Használat: "
    "hermes-skill-creator-report [OPTIONS]"
)
report_tokenizer_unavailable = (
    "[en] tokenizer unavailable, falling back to chars/4 / [hu] a tokenizer "
    "nem elérhető, chars/4 becslés"
)
report_enabled_detection_unavailable = (
    "[en] enabled-detection module unavailable, cannot enumerate skills / [hu] "
    "az enabled-detection modul nem elérhető, a skillek nem listázhatók"
)
report_rejected_apply = (
    "[en] apply not supported on the reporter / [hu] az apply nem támogatott a riporton"
)
report_rejected_emit_migration_note = (
    "[en] emit-migration-note is not a reporter flag / [hu] az "
    "emit-migration-note nem riport-flag"
)
report_rejected_write_report = (
    "[en] write-report is not a reporter flag / [hu] a write-report nem riport-flag"
)
report_json_path_inside_hermes_home = (
    "[en] --json path resolves under HERMES_HOME, refusing / [hu] a --json "
    "útvonala a HERMES_HOME alá esik, megtagadva"
)
report_no_profiles = "[en] no profiles found / [hu] nem találhatók profilok"

# Column headers (English half — the Hungarian half lives in messages_hu.py).
col_profile = "profile"
col_name = "name"
col_description = "description"
col_tokens = "tokens"
col_use_count = "use_count"
col_view_count = "view_count"
col_patch_count = "patch_count"
col_last_used_at = "last_used_at"
col_last_viewed_at = "last_viewed_at"
col_last_patched_at = "last_patched_at"
col_pct_of_cap = "% of cap"
na_value = "n/a"
total_row_label = "total"