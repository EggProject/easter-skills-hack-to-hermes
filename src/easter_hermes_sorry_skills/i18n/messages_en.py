"""English UI messages for the easter-hermes-sorry-skills-plugin.

See also: plans/03-plugin-spec.md (owner)

TDD test cases:
  test_messages_en_contains_required_keys
  test_messages_en_bilingual_format_for_console
"""

from types import MappingProxyType

# Cap-state advisory (EN half). Emitted when the 60-char skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_EN = (
    "[en] The 60-character skill-description cap is un-raised in your "
    "Hermes checkout. Run `easter-hermes-sorry-skills-patch` to raise it."
)

# Script #3 (reporter) messages — bilingual format: [en] text / [hu] text.
REPORT_HELP_SHORT = "[en] Profile skill token + usage reporter / [hu] Profil skill token + használati riport"
REPORT_HELP_LONG = (
    "[en] Lists the ENABLED skills for a profile, tokenizes the rendered "
    "name+description, and joins view/use/patch + last_used_at counts "
    "from the Curator. / [hu] Kilistázza egy profil ENGEDÉLYEZETT "
    "skilljeit, tokenizálja a renderelt name+description szöveget, és a "
    "Curator-ból kéri a view/use/patch + last_used_at számokat."
)
REPORT_OPT_PROFILE = (
    "[en] Report a single profile; default iterates the `hermes` "
    "(default) profile AND every named profile. / "
    "[hu] Egyetlen profil riportja; alapértelmezetten a `hermes` (alap) "
    "profil ÉS minden elnevezett profil."
)
REPORT_OPT_SORT = (
    "[en] Reorder rows: tokens | use_count | last_used_at. "
    "Default: tokens. / "
    "[hu] Sorok rendezése: tokens | use_count | last_used_at. "
    "Alapértelmezett: tokens."
)
REPORT_OPT_FORMAT = (
    "[en] Output format: text (default) | json. / [hu] Kimeneti formátum: text (alapértelmezett) | json."
)
REPORT_OPT_JSON = (
    "[en] Write the report to PATH (default: ./skill-report.json when "
    "--format=json; otherwise ignored). / "
    "[hu] A riport kiírása PATH-ba (alapértelmezett: ./skill-report.json, "
    "ha --format=json; egyébként figyelmen kívül hagyva)."
)
REPORT_OPT_HELP = "[en] Show bilingual EN+HU help. / [hu] Kétnyelvű EN+HU help megjelenítése."

REPORT_USAGE_HEADER = (
    "[en] Usage: easter-hermes-sorry-skills-report [OPTIONS] / "
    "[hu] Használat: easter-hermes-sorry-skills-report [OPTIONS]"
)
REPORT_TOKENIZER_UNAVAILABLE = (
    "[en] tokenizer unavailable, falling back to chars/4 / [hu] a tokenizer nem elérhető, chars/4 becslés"
)
REPORT_ENABLED_DETECTION_UNAVAILABLE = (
    "[en] enabled-detection module unavailable, cannot enumerate "
    "skills / [hu] az enabled-detection modul nem elérhető, a skillek "
    "nem listázhatók"
)
REPORT_REJECTED_APPLY = "[en] apply not supported on the reporter / [hu] az apply nem támogatott a riporton"
REPORT_REJECTED_EMIT_MIGRATION_NOTE = (
    "[en] emit-migration-note is not a reporter flag / [hu] az emit-migration-note nem riport-flag"
)
REPORT_REJECTED_WRITE_REPORT = "[en] write-report is not a reporter flag / [hu] a write-report nem riport-flag"
REPORT_JSON_PATH_INSIDE_HERMES_HOME = (
    "[en] --json path resolves under HERMES_HOME, refusing / [hu] a --json útvonala a HERMES_HOME alá esik, megtagadva"
)
REPORT_NO_PROFILES = "[en] no profiles found / [hu] nem találhatók profilok"

# Patcher preflight diagnostics (EN half — HU half lives in messages_hu.py).
CIRCULAR_IMPORT_PREFLIGHT = (
    "[en] potential circular import detected in agent/skill_utils.py (imports from tools.skills_tool)"
)

# Patcher diagnostics (EN half). Bilingual format: [en] text / [hu] text.
TARGET_REQUIRED = "[en] --target is required / [hu] a --target megadása kötelező"
TARGET_IS_HERMES_AGENT = (
    "[en] refusing to patch the live hermes-agent checkout: "
    "{resolved} / [hu] az élő hermes-agent checkout patchelése "
    "megtagadva: {resolved}"
)
TARGET_MISSING_SKILL_UTILS = (
    "[en] target missing agent/skill_utils.py: {path} / [hu] a célpontból hiányzik az agent/skill_utils.py: {path}"
)
FORCE_REQUIRES_I_ACCEPT = (
    "[en] --force requires --i-accept-line-drift / [hu] a --force használatához --i-accept-line-drift szükséges"
)
LINE_DRIFT = (
    "[en] line drift detected at site {site_id} (line {line}) / [hu] sor-eltérés a {site_id} helyen (sor {line})"
)
VALIDATION_FAILED = "[en] validation failed at site {site_id} / [hu] az érvényesítés sikertelen a {site_id} helyen"
OK_ALREADY_PATCHED = "[en] OK: site {site_id} already patched / [hu] OK: a {site_id} hely már javítva"
OK_PATCHED = "[en] OK: site {site_id} patched successfully / [hu] OK: a {site_id} hely sikeresen javítva"
PERMISSION_DENIED = "[en] permission denied writing {path} / [hu] írási engedély megtagadva: {path}"
IO_ERROR = "[en] I/O error writing {path}: {error} / [hu] I/O hiba a {path} írásakor: {error}"
CROSS_FS_WARN = (
    "[en] warning: target and tmp live on different filesystems / "
    "[hu] figyelmeztetés: a cél és az ideiglenes könyvtár különböző "
    "fájlrendszeren van"
)
FORCE_AUDIT_LOG = (
    "[en] --force audit log entry appended: timestamp={timestamp} "
    "site={site_id} diff_sha256={diff_sha} target={target} / "
    "[hu] --force audit bejegyzés hozzáfűzve: timestamp={timestamp} "
    "site={site_id} diff_sha256={diff_sha} target={target}"
)
TEXT_DRIFT = "[en] text drift detected at site {site_id} / [hu] szöveg-eltérés a {site_id} helyen"
MIGRATION_REGENERATED = "[en] migration note regenerated at {path} / [hu] migrációs jegyzet újragenerálva itt: {path}"
FORCE_CONFIRM_DIFF_HEADER = (
    "[en] --force: planned diff (unified) for {sites} / [hu] --force: tervezett diff (unified) ehhez: {sites}"
)

# Column headers (English half — the Hungarian half lives in messages_hu.py).
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

# Backwards-compat aliases (original lowercase / short names preserved for any
# downstream caller that referenced them).
report_help_short = REPORT_HELP_SHORT
report_help_long = REPORT_HELP_LONG
report_opt_profile = REPORT_OPT_PROFILE
report_opt_sort = REPORT_OPT_SORT
report_opt_format = REPORT_OPT_FORMAT
report_opt_json = REPORT_OPT_JSON
report_opt_help = REPORT_OPT_HELP
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
# audit/flip). Renamed from ``M`` to ``EN_MESSAGES`` (WPS111) and wrapped
# in MappingProxyType to satisfy WPS407 (mutable module constant).
EN_MESSAGES = MappingProxyType(
    {
        # CLI: easter-hermes-sorry-skills-profiles
        "profiles_help_short": (
            "Per-profile audit/flip for the migrated skill-creator skill "
            "(Script #2). Installs/replaces the skill-creator skill at the "
            "flat ~/.hermes/skills/skill-creator/ path under each profile. "
            "Default mode is dry-run; pass --apply to perform the writes."
        ),
        "profiles_help_long": (
            "Walks every Hermes profile (the default 'hermes' profile and "
            "every named profile returned by hermes_cli.profiles."
            "list_profiles()) and audits the per-profile skills tree. "
            "With --apply, the script calls hermes_cli.skills_hub."
            "do_install() to install/replace the migrated skill-creator "
            "in-place at ~/.hermes/skills/skill-creator/ and clears the "
            "skills system-prompt cache. With --json PATH, the "
            "deterministic JSON report is written to PATH. With --yes, "
            "the interactive TTY confirmation is suppressed. The script "
            "runs under the hermes_home_scope() context manager, "
            "mirroring HERMES_HOME in both the override token and "
            "os.environ['HERMES_HOME']."
        ),
        "profiles_opt_apply": ("Write the audit findings to the target (DEFAULT behavior)."),
        "profiles_opt_audit": ("Run audit only; do not write (inverse of default)."),
        "profiles_opt_dry_run": ("Same as --audit (do not write)."),
        "profiles_opt_profile": ("Restrict the run to a single profile (default: every profile)."),
        "profiles_opt_json": ("Write the deterministic JSON report to PATH (default: ./profile-audit.json)."),
        "profiles_opt_yes": ("Suppress the interactive TTY confirmation (CI / non-TTY runs)."),
        "profiles_opt_skip_install": ("Audit only; do not call hub_install_or_update."),
        "profiles_opt_frozen_time": ("Pin the report's generated_at to a stable ISO 8601 UTC string."),
        "profiles_opt_help": ("Show this bilingual help and exit."),
        "profiles_section_usage_en": "Usage (English)",
        "profiles_section_usage_hu": "Használat (magyar)",
        # Bilingual runtime messages
        "profiles_msg_scanning": "Scanning profiles...",
        "profiles_msg_profile_count": "Found {n} profile(s) to audit.",
        "profiles_msg_audit_default": ("Default mode: dry-run (use --apply to perform writes)."),
        "profiles_msg_applying": "Applying per-profile flip...",
        "profiles_msg_profile_audit": ("profile={name} current_disabled={disabled} current_installed={installed}"),
        "profiles_msg_diff": (
            "diff added_disabled={ad} removed_disabled={rd} added_installed={ai} removed_installed={ri}"
        ),
        "profiles_msg_cache_warn": ("profile={name} clear_skills_system_prompt_cache raised: {err} (continuing)"),
        "profiles_msg_hub_error": ("profile={name} hub install failed: {err} (continuing)."),
        "profiles_msg_json_written": "Report written to {path}.",
        "profiles_msg_refuse_no_yes": (
            "Refusing to run against the live HERMES_HOME without --yes. Re-run with --yes to confirm."
        ),
        "profiles_msg_no_profiles": ("No profiles found (default + named). Nothing to audit."),
        "profiles_msg_done": "Done. Profiles processed: {n}.",
    }
)
