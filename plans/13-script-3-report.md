<!-- title: Script #3 — read-only profile-skill token + usage reporter -->
<!-- scope: Sec 5.X (extra-brief feature WE requested — V6 S6 renamed from §5.7 to free §5.7 for the brief's original Todo list deliverable). REUSES Script #2's enabled-detection module. -->
<!-- ACs covered: AC-7.1 .. AC-7.7 -->

# 13 — Script #3: Profile Skill Token + Usage Reporter

## Goal

List the ENABLED skills for a profile so the operator can decide what to turn off. REPORT ONLY — the script MUST NOT modify anything. The reporter shares the enabled-detection module with Script #2 (06) so its view of "enabled" matches what Script #2 audits. Token counts come from the configured model's tokenizer (with a deterministic `chars // 4` fallback). Use / last-used stats come from the Curator (project ref #45) — when the field is absent in the current source, the column renders `n/a`.

The reporter is the operator's "what is on right now, and what does it cost?" view. It is purely informational: NO file writes, NO config flips, NO install calls. Bilingual `--help`. Sortable output. 100% code + branch coverage.

**Write contract (binding, per V5/R11).** Script #3 is STDOUT + `--json PATH` ONLY. It does NOT write to the worktree. It does NOT emit `MIGRATION.report.md`. It does NOT have an `--emit-migration-note` flag and does NOT have a `--write-report` flag. The only filesystem write is the operator-chosen `--json PATH`, which by default is `./skill-report.json` under cwd (an operator-chosen path OUTSIDE the fixture tree). The read-only contract test (`test_report_read_only_zero_writes`) snapshots a fixture HERMES_HOME tree, runs every flag combination, and asserts byte-identical snapshots before/after.

## CLI surface

```
Usage (English):
  uv run hermes-skill-creator-report [--profile <name>] [--sort tokens|use_count|last_used_at]
                                     [--format text|json] [--json PATH] [--help]

Használat (magyar):
  uv run hermes-skill-creator-report [--profile <name>] [--sort tokens|use_count|last_used_at]
                                     [--format text|json] [--json PATH] [--help]

Options:
  --profile <name>    Report a single profile; default iterates the
                      `hermes` (default) profile AND every named profile
                      returned by `hermes_cli.profiles.list_profiles()`.
  --sort <key>        Reorder rows: tokens | use_count | last_used_at.
                      Default: tokens (descending). Stable secondary
                      key: skill name (ascending) for determinism.
  --format <fmt>      Output format: text (default) | json.
  --json PATH         Write the report to PATH (default: ./skill-report.json
                      when --format=json; otherwise ignored).
  --help              Show this help (bilingual EN+HU, two-section).
```

The reporter is a single console script `hermes-skill-creator-report` declared in `pyproject.toml` `[project.scripts]` (10), pointing at `hermes_skill_creator_plugin.entrypoints:report_main`. There is no `--apply` flag — its absence is intentional and is enforced by an `--apply`-rejection test.

## Enabled-set detection (SHARED with Script #2)

The reporter REUSES Script #2's exact enabled-detection logic. The single source of truth is the helper module `src/hermes_skill_creator_plugin/_enabled_detection` (owned by D-script-2, consumed by G-report per 11):

```python
def get_enabled_skills(
    profile_path: Path,
    *,
    platform: Optional[str] = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for `profile_path`, honoring:

    1. `config[toggle]` per-skill on/off (the `disabled` list).
    2. Profile- AND platform-scoped conditional exclusions.
    3. `platforms:` frontmatter `disable_if_platform_present` lists.
    """
```

The reporter imports this function unchanged. It does NOT re-derive the set from `config.yaml` directly, does NOT walk the `skills/` tree and assume everything inside is enabled, and does NOT re-implement the platform filter. The integration test `test_report_shares_enabled_detection_with_script_2` asserts (a) the reporter imports from `hermes_skill_creator_plugin._enabled_detection`, (b) the set it returns is byte-identical to the set Script #2's apply path would compute for the same fixture, and (c) the function is NOT redefined inside the reporter package.

If the shared module is unavailable at import time (an extremely defensive fallback for the case where the operator has only installed the reporter subpackage), the reporter aborts with a bilingual error and exit code 6 — it does NOT fall back to a local re-implementation, because that would defeat the point of sharing the logic.

## Tokens (per-skill + total + % of cap)

For each enabled skill, the reporter tokenizes the rendered name+description string — `name` plus the FULL description (NOT the truncated index form) — and reports the count. The token count covers the full description for an accurate cost estimate; the operator should note that the system prompt's `<available_skills>` index renders the truncated form (see note below).

```python
def estimate_tokens(name: str, description: str, *, tokenizer=None) -> int:
    """Tokenize `f"{name} {description}"` with the configured model's tokenizer.

    Fallback: `len(rendered) // 4` when `tokenizer` is None or raises.
    Returns a non-negative int.
    """
```

**Index form note (binding).** The system prompt's `<available_skills>` index line is `f"    - {name}: {desc}"` (`agent/prompt_builder.py:1399`), where `desc` is `extract_skill_description(frontmatter)` (`agent/skill_utils.py:682`) — a TRUNCATED form: `desc[:57] + "..."` when `len(desc) > 60`, otherwise the full description (`skill_utils.py:688-689`). The reporter tokenizes the FULL description for an accurate cost estimate; the operator sees that the index uses the truncated form (so the actual on-the-wire cost per skill is lower than the reporter's per-skill count would imply when the description is longer than 60 chars).

The tokenizer is loaded from the active model in `~/.hermes/config.yaml` (or the `HERMES_MODEL` env var) via the standard transformers / tiktoken loader that Hermes already uses for its own prompt-budget reports. When the loader is unavailable, the reporter logs a one-line bilingual warning (`[en] tokenizer unavailable, falling back to chars/4 / [hu] a tokenizer nem elérhető, chars/4 becslés`) and proceeds with the deterministic fallback. The fallback estimate is the same approximation used elsewhere in the Hermes codebase for budget planning; the test fixture injects a known tokenizer stub so the integration test asserts the EXACT token count, not an approximation.

The reporter prints:
- A per-skill `tokens` column.
- A `total_tokens` row at the bottom of each profile block.
- An optional `pct_of_cap` column showing `total_tokens / 1024` rounded to one decimal place. The 1024 cap is a constant `MAX_DESCRIPTION_LENGTH` imported from `tools.skills_tool` (98) when the import is safe; otherwise a local constant `_REPORTER_MAX_DESCRIPTION_LENGTH = 1024` is used to avoid an agent<->tools circular import (same direction-check the cap-raise patch in 04 uses).

## Usage (view / use / patch counts + last_used_at)

Usage stats come from the Curator (project ref #45). The reporter's first implementation step is a verification pass — BEFORE writing the reporter, the implementer MUST read the Curator's actual storage backend and field names in the current Hermes source tree and record the findings in a test fixture (`tests/fixtures/curator/recorded_fields.json`). The fixture captures: the storage class, the field names (`view_count`, `use_count`, `patch_count`, `last_used_at`, `last_viewed_at`, `last_patched_at`), the field types, and the record-key format (e.g. is the key the skill name, a slug, or a `(profile, skill)` tuple?).

**Curator field names (binding, per V5/R12a).** The real field names, verified against `tools/skill_usage.py:155, 169, 463-468`, are:

| Field         | Type   | Source line | Meaning                                  |
|---------------|--------|-------------|------------------------------------------|
| `last_used_at`| ISO 8601 string or None | `skill_usage.py:465` | Timestamp of most recent `use_count` bump (skill_usage.py:600-607). |
| `last_viewed_at` | ISO 8601 string or None | `skill_usage.py:466` | Timestamp of most recent `view_count` bump (skill_usage.py:588-595). |
| `last_patched_at` | ISO 8601 string or None | `skill_usage.py:468` | Timestamp of most recent `patch_count` bump (skill_usage.py:612-618). |
| `use_count`   | int    | `skill_usage.py:463` | Number of times the skill was actively used. |
| `view_count`  | int    | `skill_usage.py:464` | Number of times the skill was loaded via `skill_view()`. |
| `patch_count` | int    | `skill_usage.py:467` | Number of times the skill was patched/edited. |

The reporter MUST NOT use the legacy `last_used` field (it does not exist in the current source — `skill_usage.py` uses the `_at` suffixed names per the verification above). The fixture `recorded_fields.json` enumerates these exact six field names; any reporter code that references a field NOT in this set fails `test_report_usage_does_not_invent_fields`.

The verification pass is gated by a test: `test_report_curator_field_verification_recorded` reads the fixture and asserts it was updated within the current Phase 5 window (mtime < 7 days from HEAD). If the fixture is stale, the test FAILS and the implementer is forced to re-verify the actual source. This prevents the reporter from quoting field names that drifted since the fixture was recorded.

When the Curator is absent from the current Hermes source (i.e. the project ref #45 is not yet merged, or the field names in the recorded fixture are not present in the loaded Curator module), the reporter renders `n/a` for the absent columns — it does NOT render `0` (zero is a meaningful value, "we don't know" is not), and it does NOT raise. The test `test_report_usage_n_a_when_curator_absent` covers this path explicitly.

When the Curator IS present and the fields are recorded, the reporter joins the enabled-skill set against the Curator's view of usage and renders `n/a` only for skills that exist in the enabled set but not in the Curator's records (a newly installed skill that has not yet been used).

## Output (sortable table)

Default format: a plain-text table rendered with a small in-tree formatter (no third-party tabulate dep). Columns: `profile | name | description (truncated to 60) | tokens | use_count | patch_count | view_count | last_used_at | % of cap`. The description is truncated to 60 chars with a trailing ellipsis (`...`) — this matches the rendered form the system prompt's index uses under the unpatched cap (see "Index form note" above), and it is what the operator will visually recognize from the agent's session output. The full description is preserved in the `--format=json` output.

Sorting:
- `--sort tokens` (default): descending by token count, stable secondary key by skill name ascending.
- `--sort use_count`: descending by `use_count`, stable secondary key by skill name ascending. Rows with `n/a` sort LAST (they represent unknown, not zero).
- `--sort last_used_at`: descending by `last_used_at` (most recent first), stable secondary key by skill name ascending. Rows with `n/a` sort LAST.

The sort is stable: equal keys keep the order from the underlying enabled-detection walk, which itself walks the `skills/` directory in a sorted order. A test asserts the byte-identical output across two runs on the same fixture.

`--format=json` emits a single JSON object with the same shape Script #2 uses, plus the token and usage columns:

```json
{
  "tool": "hermes-skill-creator-report",
  "version": "0.1.0",
  "generated_at": "2026-06-17T00:00:00Z",
  "profiles": [
    {
      "profile_name": "hermes",
      "enabled_skills": [
        {
          "name": "skill-creator",
          "description": "<full text, up to 1024 chars>",
          "tokens": 47,
          "use_count": 3,
          "view_count": 5,
          "patch_count": 1,
          "last_used_at": "2026-06-16T22:14:03Z",
          "last_viewed_at": "2026-06-16T22:14:03Z",
          "last_patched_at": "2026-06-10T08:00:00Z",
          "pct_of_cap": 4.6
        }
      ],
      "total_tokens": 312
    }
  ]
}
```

`generated_at` is stable when `HERMES_SKILL_CREATOR_FROZEN_TIME` is set (same env var Script #2 uses), byte-identical across runs given identical input. Otherwise it is the wall clock at run time.

## Safety (READ-ONLY)

The reporter MUST NOT write to the filesystem under any flag combination. This is enforced by an integration test that:

1. Snapshots a fixture HERMES_HOME tree (sha256 of every file under it).
2. Runs the reporter with every flag combination: default, `--profile <name>`, `--sort tokens`, `--sort use_count`, `--sort last_used_at`, `--format=json`, `--json PATH` (which writes OUTSIDE the fixture, to a tmp path), and all combinations of the above.
3. Re-snapshots the fixture HERMES_HOME tree.
4. Asserts the two snapshots are byte-identical (the same sentinels Script #2 uses for its no-touch contract — see 09).

If any test variant writes a single byte to the fixture tree, the test fails. The reporter's source code MUST NOT contain any of: `open(..., "w")`, `Path.write_text`, `Path.write_bytes`, `os.replace`, `shutil.copy`, `shutil.copytree`, `subprocess.run` with a write side-effect, or any other write primitive. A static AST-grep test (`test_report_no_write_calls_in_source`) walks the reporter's source tree and fails on any match. The fixture-mtime sentinel covers imports and any indirect write path the AST scan misses.

The `--json PATH` flag writes to a path OUTSIDE the fixture tree (a tmp dir) so the read-only contract is preserved even when the operator wants machine-readable output. The reporter documents this in `--help`: the `--json` output is the only write, and it is controlled by the operator's chosen path.

`--help` is bilingual EN+HU, two top-level sections ("Usage (English)" / "Használat (magyar)") with mirrored content. The integration test `test_report_help_is_bilingual` parses the `--help` output and asserts both sections are present with the expected headers, and `test_report_console_log_lines_match_bilingual_regex` asserts every console / log line matches `^.*\[en\] .+ / \[hu\] .+$` (the project's bilingual regex).

## Definition of Done

- 100% code + branch coverage (`pytest --cov=hermes_skill_creator_plugin.report --cov-branch --cov-fail-under=100`).
- TDD: every test in the list below is written FIRST and is in the initial failing state before any reporter code lands.
- Bilingual format: all console + log lines match the project regex; `--help` is two-section.
- Pre-commit clean: `pre-commit run --all-files` exits 0 (ruff + black + mypy + wemake + check_bilingual + check_line_count).
- The reporter's source tree contains NO write calls (AST-grep test).
- The integration no-touch sentinel test passes for every flag combination.
- The shared enabled-detection module is imported, not re-implemented (static import test).
- The Curator field-verification fixture is recorded within the current Phase 5 window (mtime sentinel).

## Integration

The reporter is a NEW standalone read-only entry point:

- Console script: `hermes-skill-creator-report` in `pyproject.toml` `[project.scripts]` (10).
- Module: `src/hermes_skill_creator_plugin/report/` (sibling to `entrypoints.py`, alongside the future `patch/` and `profiles/` subpackages if/when those are split out).
- Entrypoint: `hermes_skill_creator_plugin.entrypoints:report_main` (10 already declares it).
- Test location: `tests/report/` (unit + integration + the `curator/recorded_fields.json` fixture).
- Plan references: this file is `13-script-3-report.md`. The 00-index, 01-overview, 09-test-strategy, 10-toolchain-and-conventions, and 11-sub-agent-delegation-map files all reference it; the index row is updated to reflect the actual line count after the file is written.
- Dependency on the shared enabled-detection module: the reporter imports `get_enabled_skills` from `src/hermes_skill_creator_plugin/_enabled_detection`. The implementer MUST verify the import direction (reporter depends on the shared module, not the other way around) — the shared module MUST NOT import from the reporter.
- Dependency on the Curator (project ref #45): gated on the field-verification fixture being recorded. If the Curator is not yet merged, the reporter renders `n/a` for the usage columns and exits 0; the verification-fixture mtime sentinel prevents shipping the reporter against an unverified Curator.

## TDD test list

### Read-only contract
- `test_report_read_only_zero_writes` — snapshot the fixture HERMES_HOME; run every flag combination; re-snapshot; assert byte-identical (covers default, `--profile`, `--sort tokens`, `--sort use_count`, `--sort last_used_at`, `--format=json`, `--json PATH`, and every pairwise combination).
- `test_report_no_write_calls_in_source` — AST-grep the reporter's source tree; fail on `open(..., "w")`, `Path.write_text`, `Path.write_bytes`, `os.replace`, `shutil.copy`, `shutil.copytree`, `subprocess.run` with a write side-effect, `Path.unlink`, `os.remove`, `shutil.rmtree`.
- `test_report_rejects_apply_flag` — pass `--apply`; assert the reporter exits non-zero with a bilingual error message ("apply not supported on the reporter / az apply nem támogatott a riporton"); the fixture tree is unchanged.
- `test_report_rejects_emit_migration_note_flag` — pass `--emit-migration-note`; assert the reporter exits non-zero with a bilingual error message ("emit-migration-note is not a reporter flag / az emit-migration-note nem riport-flag"); the fixture tree is unchanged. Binds the V5/R11 contract: Script #3 has no migration-note flag.
- `test_report_rejects_write_report_flag` — pass `--write-report`; assert the reporter exits non-zero with a bilingual error message ("write-report is not a reporter flag / a write-report nem riport-flag"); the fixture tree is unchanged. Binds the V5/R11 contract.
- `test_report_no_migration_report_file_emitted` — run every flag combination; assert no `MIGRATION.report.md` file is created anywhere under cwd or fixture tree.
- `test_report_json_path_outside_fixture` — `--json PATH` writes to PATH; PATH defaults to a tmp dir, NOT inside the fixture tree; if the operator passes an absolute path inside the fixture tree, the reporter exits 6 and does NOT write.

### Enabled-set detection (shared with Script #2)
- `test_report_shares_enabled_detection_with_script_2` — assert (a) the reporter imports `get_enabled_skills` from `hermes_skill_creator_plugin._enabled_detection`, (b) the import is at module top-level (not inside a function), (c) the function is NOT redefined in the reporter package, (d) the set returned for a fixture matches the set Script #2's apply path would compute.
- `test_report_default_profile` — fixture with default profile only; assert the report covers the `hermes` profile.
- `test_report_named_profile` — `--profile work` selects the `work` profile only; assert the report does NOT include other profiles.
- `test_report_multi_profile_default` — no `--profile`; fixture with `hermes` + two named profiles; assert all three are reported in stable sorted order.
- `test_report_honors_disabled_toggle` — fixture with `disabled: [foo]`; assert `foo` is excluded.
- `test_report_honors_platform_filter` — fixture with `disable_if_platform: [bar]` for `darwin`; assert `bar` is excluded when `platform="darwin"`.
- `test_report_honors_conditional_exclusions` — fixture with a per-skill `disable_if` rule; assert the rule wins over the toggle list.

### Tokenization
- `test_report_tokens_match_fixture` — fixture with a known tokenizer stub (returns a fixed token count per call); assert the rendered per-skill token count matches the stub's output for `f"{name} {description}"` (FULL description, not truncated).
- `test_report_tokens_use_full_description_not_truncated` — fixture with a 200-char description; assert the tokenizer is called with the full 200-char text (the reporter tokenizes the full form for an accurate cost estimate; the index form is truncated separately).
- `test_report_total_tokens` — assert the `total_tokens` row equals the sum of per-skill counts.
- `test_report_pct_of_cap` — assert the `pct_of_cap` column equals `total_tokens / 1024 * 100` rounded to one decimal.
- `test_report_tokenizer_fallback_chars_div_4` — fixture with no tokenizer; assert the reporter uses `len(rendered) // 4`; a bilingual warning is logged once.
- `test_report_tokenizer_raises_uses_fallback` — fixture where the tokenizer raises on every call; assert the reporter falls back to `len(rendered) // 4` and continues (no exception propagates to the caller).
- `test_report_no_circular_import_with_tools_skills_tool` — assert the reporter does NOT import `tools.skills_tool` at module top-level (the import direction would be agent<->tools cyclic); the constant is local or imported lazily inside the function.

### Usage (Curator)
- `test_report_curator_field_verification_recorded` — assert the fixture `tests/fixtures/curator/recorded_fields.json` exists, parses as JSON, enumerates exactly the six documented field names (`use_count`, `view_count`, `patch_count`, `last_used_at`, `last_viewed_at`, `last_patched_at`), and was updated within 7 days of HEAD (mtime sentinel).
- `test_report_usage_n_a_when_curator_absent` — fixture with no Curator module; assert every usage column renders `n/a`; the reporter exits 0.
- `test_report_usage_n_a_for_unseen_skill` — fixture with Curator + a skill present in the enabled set but absent from the Curator's records; assert the per-row usage columns render `n/a` for that skill.
- `test_report_usage_view_use_patch_counts` — fixture with a known Curator record; assert `use_count`, `view_count`, `patch_count` match the fixture's recorded values.
- `test_report_usage_last_used_at_iso8601` — assert `last_used_at` is rendered as an ISO 8601 string (NOT the legacy `last_used`); assert the column is sortable.
- `test_report_usage_last_viewed_at_and_last_patched_at_present` — fixture with a Curator record that has `last_viewed_at` and `last_patched_at` populated; assert both columns render their ISO 8601 values.
- `test_report_usage_does_not_invent_fields` — assert the reporter does NOT render any field name that is not in `recorded_fields.json` (defensive against Curator schema drift); the legacy `last_used` field MUST NOT appear anywhere in reporter output.
- `test_report_uses_at_suffixed_timestamps` — assert the reporter code references `last_used_at`, `last_viewed_at`, `last_patched_at` (the `_at` suffixed forms) and does NOT reference the unsuffixed `last_used` form (which does not exist in `tools/skill_usage.py`).

### Sorting
- `test_report_sort_by_tokens` — fixture with three skills of different token counts; assert the rendered order is descending by tokens.
- `test_report_sort_by_use_count` — fixture with three skills of different use counts; assert the rendered order is descending by use_count, with `n/a` rows last.
- `test_report_sort_by_last_used_at` — fixture with three skills of different `last_used_at` timestamps; assert the rendered order is most-recent first, with `n/a` rows last.
- `test_report_sort_stable_secondary_key_by_name` — fixture with two skills of equal primary key; assert the secondary sort is by name ascending.
- `test_report_default_sort_is_tokens` — no `--sort`; assert the rendered order matches `--sort tokens`.

### Output format
- `test_report_text_format_columns` — fixture; assert the plain-text output contains all expected columns (incl. `view_count`, `last_viewed_at`, `last_patched_at`) and the rows are aligned.
- `test_report_text_format_truncates_description_to_60` — fixture with a 200-char description; assert the text output shows 60 chars + ellipsis (matching `extract_skill_description` form); the JSON output preserves the full text.
- `test_report_json_format_shape` — `--format=json`; assert the JSON shape matches the documented schema (profile_name, enabled_skills[] with all six usage fields, total_tokens).
- `test_report_json_deterministic_with_frozen_time` — run twice with `HERMES_SKILL_CREATOR_FROZEN_TIME` set; assert sha256 of output is byte-identical.
- `test_report_json_path_default_under_cwd` — `--format=json` with no `--json`; assert the file is written to `./skill-report.json` under cwd; absolute path is also accepted.

### Bilingual + CLI
- `test_report_help_is_bilingual` — assert `--help` contains both "Usage (English)" and "Használat (magyar)" sections; mirrored content.
- `test_report_console_log_lines_match_bilingual_regex` — capture all stdout / stderr; assert every line matches `^.*\[en\] .+ / \[hu\] .+$`.
- `test_report_exit_zero_on_success` — fixture with valid data; assert exit 0.
- `test_report_exit_six_when_enabled_detection_unavailable` — mock the import to raise; assert exit 6; bilingual error message.
- `test_report_no_subprocess_for_writes` — assert the reporter does NOT call `subprocess.run` against any Hermes CLI in a way that could write (it MAY call `hermes_cli.profiles.list_profiles()`, which is a pure read; the test stubs it to confirm no write side-effects).

### Coverage
- `test_report_coverage_100_percent` — `pytest --cov=hermes_skill_creator_plugin.report --cov-branch --cov-fail-under=100` exits 0; the diff shows 100% covered lines and 100% covered branches (every `if` / `for` / `except` / `with` branch hit by at least one test).

## ACs covered

- **AC-7.1** READ-ONLY — `test_report_read_only_zero_writes` + `test_report_no_write_calls_in_source` + `test_report_rejects_apply_flag` + `test_report_rejects_emit_migration_note_flag` + `test_report_rejects_write_report_flag` + `test_report_no_migration_report_file_emitted` + `test_report_json_path_outside_fixture`.
- **AC-7.2** `--profile`, `--sort`, `--format`, `--json` — `test_report_named_profile` + sort tests + `test_report_text_format_columns` + `test_report_json_format_shape`.
- **AC-7.3** `--help` bilingual two-section — `test_report_help_is_bilingual`.
- **AC-7.4** shares enabled-detection with Script #2 — `test_report_shares_enabled_detection_with_script_2` + the platform / toggle / conditional-exclusion tests.
- **AC-7.5** tokens from rendered name+description — `test_report_tokens_match_fixture` + `test_report_tokens_use_full_description_not_truncated` + `test_report_total_tokens` + `test_report_pct_of_cap` + `test_report_tokenizer_fallback_chars_div_4` + `test_report_tokenizer_raises_uses_fallback`.
- **AC-7.6** usage from Curator, n/a when missing — `test_report_curator_field_verification_recorded` + `test_report_usage_n_a_when_curator_absent` + `test_report_usage_n_a_for_unseen_skill` + `test_report_usage_does_not_invent_fields` + `test_report_uses_at_suffixed_timestamps`.
- **AC-7.7** 100% coverage, TDD — `test_report_coverage_100_percent` + the TDD ordering documented in "Definition of Done".

## Decisions & evidence

### D1. Script #3 is READ-ONLY end-to-end (R11 fix)
- **Decision**: Script #3 (`hermes-skill-creator-report`) is STDOUT + `--json PATH` ONLY. No `--apply`, no `--emit-migration-note`, no `--write-report`, no `MIGRATION.report.md`. The only filesystem write is the operator-chosen `--json PATH`, which defaults to `./skill-report.json` under cwd (outside any fixture tree).
- **Rationale**: a read-only reporter that writes a MIGRATION note or any worktree file would violate the "no state mutation" contract and would need a sentinel test of its own. STDOUT + optional JSON keeps the contract trivially auditable.
- **Evidence**: V5 R11; AC-7.1 in 01; `test_report_read_only_zero_writes` + `test_report_no_write_calls_in_source` + `test_report_no_migration_report_file_emitted` in this file. Confidence: verified-from-source.

### D2. Curator field names: `_at`-suffixed timestamps (R12 fix)
- **Decision**: usage columns reference the `_at`-suffixed fields verified against `tools/skill_usage.py:463-468`: `last_used_at`, `last_viewed_at`, `last_patched_at`, `use_count`, `view_count`, `patch_count`. The legacy unsuffixed `last_used` field is NOT used (it does not exist in the current source).
- **Rationale**: round-2 review found the reporter assumed a `last_used` field that does not exist; round-2 R12 fix pins the exact six field names from the real source.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skill_usage.py:155, 169, 463-468`; V5 R12; `test_report_curator_field_verification_recorded` + `test_report_usage_does_not_invent_fields` + `test_report_uses_at_suffixed_timestamps` in this file. Confidence: verified-from-source.

### D3. Tokenize FULL description, not truncated index form (R12 fix)
- **Decision**: the reporter tokenizes the FULL `name + " " + description` string. The text-format table truncates the displayed description to 60 chars (matching the system-prompt index form), but the JSON output preserves the full description.
- **Rationale**: round-2 review found the reporter tokenizing the truncated 60-char form, which underestimates cost. The reporter's job is an accurate cost estimate; the index form is a separate concern (operator-facing display).
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `agent/prompt_builder.py:1399` (`f"    - {name}: {desc}"`) and `agent/skill_utils.py:682, 688-689` (`extract_skill_description`); V5 R12; `test_report_tokens_use_full_description_not_truncated` + `test_report_text_format_truncates_description_to_60` in this file. Confidence: verified-from-source.

### D4. Shared enabled-detection helper (R4 fix)
- **Decision**: `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills(profile_path, *, platform=None) -> frozenset[str]` is imported at module top-level by the reporter. The reporter NEVER redefines the function locally. If the shared module is unavailable at import time, the reporter aborts with exit 6 (not a local re-implementation).
- **Rationale**: round-2 review found the reporter about to re-derive the enabled set locally; sharing prevents drift between audit (Script #2) and report (Script #3).
- **Evidence**: V5 R4 + R10; 06 §Shared enabled-detection module; AC-7.3 in 01; `test_report_shares_enabled_detection_with_script_2` + `test_report_exit_six_when_enabled_detection_unavailable` in this file. Confidence: verified-from-source.

### D5. Sort stability + `n/a` rows last (binding)
- **Decision**: all `--sort` modes sort descending on the primary key, with `skill_name` (ascending) as a stable secondary key. Rows with `n/a` on the primary sort column sort LAST (they represent unknown, not zero).
- **Rationale**: deterministic output across runs is required for snapshot tests; `n/a` last avoids clustering unknown skills with real zeros.
- **Evidence**: 13 §Sorting; `test_report_sort_stable_secondary_key_by_name` + `test_report_sort_by_use_count` + `test_report_sort_by_last_used_at` in this file. Confidence: inferred.

### D6. Tokenizer fallback: `chars // 4` when loader raises or is unavailable
- **Decision**: when the configured model's tokenizer is unavailable or raises on every call, the reporter logs a one-line bilingual warning and proceeds with `len(rendered) // 4`.
- **Rationale**: the fallback matches Hermes's own budget-planning approximation; failing the run would deny the operator the report entirely.
- **Evidence**: 13 §Tokens; `test_report_tokenizer_fallback_chars_div_4` + `test_report_tokenizer_raises_uses_fallback` in this file. Confidence: inferred.

### D7. JSON determinism: frozen timestamp + sorted rows
- **Decision**: `--format=json` output's `generated_at` reads `HERMES_SKILL_CREATOR_FROZEN_TIME` when set; otherwise wall clock. Rows are sorted by the active sort key; profile order is sorted; JSON keys are sorted.
- **Rationale**: byte-identical output across runs is required for snapshot tests and downstream-agent diffs.
- **Evidence**: 13 §Output; `test_report_json_deterministic_with_frozen_time` in this file. Confidence: inferred.

### D8. Curator field-verification fixture: `tests/fixtures/curator/recorded_fields.json`
- **Decision**: the implementer MUST record the Curator's storage class, field names, and field types in a JSON fixture BEFORE writing the reporter code. The fixture's mtime is enforced < 7 days from HEAD (mtime sentinel).
- **Rationale**: round-2 review found the reporter quoting field names that had drifted; a verification step gated on recency prevents the reporter from going stale.
- **Evidence**: 13 §Usage; `test_report_curator_field_verification_recorded` in this file. Confidence: inferred.

<!-- end of file: 304 lines (budget 400) -->
