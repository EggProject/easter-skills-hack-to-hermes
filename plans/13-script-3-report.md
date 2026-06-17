<!-- title: Script #3 — read-only profile-skill token + usage reporter -->
<!-- scope: Sec 5.7 (NEW in V3). REUSES Script #2's enabled-detection module. -->
<!-- ACs covered: AC-7.1 .. AC-7.7 -->

# 13 — Script #3: Profile Skill Token + Usage Reporter

## Goal

List the ENABLED skills for a profile so the operator can decide what to turn off. REPORT ONLY — the script MUST NOT modify anything. The reporter shares the enabled-detection module with Script #2 (06) so its view of "enabled" matches what Script #2 audits. Token counts come from the configured model's tokenizer (with a deterministic `chars // 4` fallback). Use / last-used stats come from the Curator (project ref #45) — when the field is absent in the current source, the column renders `n/a`.

The reporter is the operator's "what is on right now, and what does it cost?" view. It is purely informational: NO file writes, NO config flips, NO install calls. Bilingual `--help`. Sortable output. 100% code + branch coverage.

## CLI surface

```
Usage (English):
  uv run hermes-skill-creator-report [--profile <name>] [--sort tokens|use_count|last_used]
                                     [--format text|json] [--json PATH] [--help]

Használat (magyar):
  uv run hermes-skill-creator-report [--profile <name>] [--sort tokens|use_count|last_used]
                                     [--format text|json] [--json PATH] [--help]

Options:
  --profile <name>    Report a single profile; default iterates the
                      `hermes` (default) profile AND every named profile
                      returned by `hermes_cli.profiles.list_profiles()`.
  --sort <key>        Reorder rows: tokens | use_count | last_used.
                      Default: tokens (descending). Stable secondary
                      key: skill name (ascending) for determinism.
  --format <fmt>      Output format: text (default) | json.
  --json PATH         Write the report to PATH (default: ./skill-report.json
                      when --format=json; otherwise ignored).
  --help              Show this help (bilingual EN+HU, two-section).
```

The reporter is a single console script `hermes-skill-creator-report` declared in `pyproject.toml` `[project.scripts]` (10), pointing at `hermes_skill_creator_plugin.entrypoints:report_main`. There is no `--apply` flag — its absence is intentional and is enforced by an `--apply`-rejection test.

## Enabled-set detection (SHARED with Script #2)

The reporter REUSES Script #2's exact enabled-detection logic. The single source of truth is the helper module `src/hermes_skill_creator_plugin/_enabled.py` (owned by D-script-2, consumed by G-report per 11):

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

The reporter imports this function unchanged. It does NOT re-derive the set from `config.yaml` directly, does NOT walk the `skills/` tree and assume everything inside is enabled, and does NOT re-implement the platform filter. The integration test `test_report_shares_enabled_detection_with_script_2` asserts (a) the reporter imports from `_enabled.py`, (b) the set it returns is byte-identical to the set Script #2's apply path would compute for the same fixture, and (c) the function is NOT redefined inside the reporter package.

If the shared module is unavailable at import time (an extremely defensive fallback for the case where the operator has only installed the reporter subpackage), the reporter aborts with a bilingual error and exit code 6 — it does NOT fall back to a local re-implementation, because that would defeat the point of sharing the logic.

## Tokens (per-skill + total + % of cap)

For each enabled skill, the reporter tokenizes the RENDERED name+description string — the same string the system prompt's `<available_skills>` index will display — and reports the count.

```python
def estimate_tokens(name: str, description: str, *, tokenizer=None) -> int:
    """Tokenize `f"{name} {description}"` with the configured model's tokenizer.

    Fallback: `len(rendered) // 4` when `tokenizer` is None or raises.
    Returns a non-negative int.
    """
```

The tokenizer is loaded from the active model in `~/.hermes/config.yaml` (or the `HERMES_MODEL` env var) via the standard transformers / tiktoken loader that Hermes already uses for its own prompt-budget reports. When the loader is unavailable, the reporter logs a one-line bilingual warning (`[en] tokenizer unavailable, falling back to chars/4 / [hu] a tokenizer nem elérhető, chars/4 becslés`) and proceeds with the deterministic fallback. The fallback estimate is the same approximation used elsewhere in the Hermes codebase for budget planning; the test fixture injects a known tokenizer stub so the integration test asserts the EXACT token count, not an approximation.

The reporter prints:
- A per-skill `tokens` column.
- A `total_tokens` row at the bottom of each profile block.
- An optional `pct_of_cap` column showing `total_tokens / 1024` rounded to one decimal place. The 1024 cap is a constant `MAX_DESCRIPTION_LENGTH` imported from `tools.skills_tool` (98) when the import is safe; otherwise a local constant `_REPORTER_MAX_DESCRIPTION_LENGTH = 1024` is used to avoid an agent<->tools circular import (same direction-check the cap-raise patch in 04 uses).

## Usage (view / use / patch counts + last_used)

Usage stats come from the Curator (project ref #45). The reporter's first implementation step is a verification pass — BEFORE writing the reporter, the implementer MUST read the Curator's actual storage backend and field names in the current Hermes source tree and record the findings in a test fixture (`tests/fixtures/curator/recorded_fields.json`). The fixture captures: the storage class, the field names (`view_count`, `use_count`, `patch_count`, `last_used`), the field types, and the record-key format (e.g. is the key the skill name, a slug, or a `(profile, skill)` tuple?).

The verification pass is gated by a test: `test_report_curator_field_verification_recorded` reads the fixture and asserts it was updated within the current Phase 5 window (mtime < 7 days from HEAD). If the fixture is stale, the test FAILS and the implementer is forced to re-verify the actual source. This prevents the reporter from quoting field names that drifted since the fixture was recorded.

When the Curator is absent from the current Hermes source (i.e. the project ref #45 is not yet merged, or the field names in the recorded fixture are not present in the loaded Curator module), the reporter renders `n/a` for the absent columns — it does NOT render `0` (zero is a meaningful value, "we don't know" is not), and it does NOT raise. The test `test_report_usage_n_a_when_curator_absent` covers this path explicitly.

When the Curator IS present and the fields are recorded, the reporter joins the enabled-skill set against the Curator's view of usage and renders `n/a` only for skills that exist in the enabled set but not in the Curator's records (a newly installed skill that has not yet been used).

## Output (sortable table)

Default format: a plain-text table rendered with a small in-tree formatter (no third-party tabulate dep). Columns: `profile | name | description (truncated to 60) | tokens | use_count | patch_count | last_used | % of cap`. The description is truncated to 60 chars with a trailing ellipsis (`...`) — this is the rendered form the system prompt's index uses under the unpatched cap, and it is what the operator will visually recognize from the agent's session output. The full description is preserved in the `--format=json` output.

Sorting:
- `--sort tokens` (default): descending by token count, stable secondary key by skill name ascending.
- `--sort use_count`: descending by `use_count`, stable secondary key by skill name ascending. Rows with `n/a` sort LAST (they represent unknown, not zero).
- `--sort last_used`: descending by `last_used` (most recent first), stable secondary key by skill name ascending. Rows with `n/a` sort LAST.

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
          "patch_count": 1,
          "last_used": "2026-06-16T22:14:03Z",
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
2. Runs the reporter with every flag combination: default, `--profile <name>`, `--sort tokens`, `--sort use_count`, `--sort last_used`, `--format=json`, `--json PATH` (which writes OUTSIDE the fixture, to a tmp path), and all combinations of the above.
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
- Dependency on the shared enabled-detection module: the reporter imports `get_enabled_skills` from `src/hermes_skill_creator_plugin/_enabled.py`. The implementer MUST verify the import direction (reporter depends on the shared module, not the other way around) — the shared module MUST NOT import from the reporter.
- Dependency on the Curator (project ref #45): gated on the field-verification fixture being recorded. If the Curator is not yet merged, the reporter renders `n/a` for the usage columns and exits 0; the verification-fixture mtime sentinel prevents shipping the reporter against an unverified Curator.

## TDD test list

### Read-only contract
- `test_report_read_only_zero_writes` — snapshot the fixture HERMES_HOME; run every flag combination; re-snapshot; assert byte-identical (covers default, `--profile`, `--sort tokens`, `--sort use_count`, `--sort last_used`, `--format=json`, `--json PATH`, and every pairwise combination).
- `test_report_no_write_calls_in_source` — AST-grep the reporter's source tree; fail on `open(..., "w")`, `Path.write_text`, `Path.write_bytes`, `os.replace`, `shutil.copy`, `shutil.copytree`, `subprocess.run` with a write side-effect, `Path.unlink`, `os.remove`, `shutil.rmtree`.
- `test_report_rejects_apply_flag` — pass `--apply`; assert the reporter exits non-zero with a bilingual error message ("apply not supported on the reporter / az apply nem támogatott a riporton"); the fixture tree is unchanged.
- `test_report_json_path_outside_fixture` — `--json PATH` writes to PATH; PATH defaults to a tmp dir, NOT inside the fixture tree; if the operator passes an absolute path inside the fixture tree, the reporter exits 6 and does NOT write.

### Enabled-set detection (shared with Script #2)
- `test_report_shares_enabled_detection_with_script_2` — assert (a) the reporter imports `get_enabled_skills` from `hermes_skill_creator_plugin._enabled`, (b) the import is at module top-level (not inside a function), (c) the function is NOT redefined in the reporter package, (d) the set returned for a fixture matches the set Script #2's apply path would compute.
- `test_report_default_profile` — fixture with default profile only; assert the report covers the `hermes` profile.
- `test_report_named_profile` — `--profile work` selects the `work` profile only; assert the report does NOT include other profiles.
- `test_report_multi_profile_default` — no `--profile`; fixture with `hermes` + two named profiles; assert all three are reported in stable sorted order.
- `test_report_honors_disabled_toggle` — fixture with `disabled: [foo]`; assert `foo` is excluded.
- `test_report_honors_platform_filter` — fixture with `disable_if_platform: [bar]` for `darwin`; assert `bar` is excluded when `platform="darwin"`.
- `test_report_honors_conditional_exclusions` — fixture with a per-skill `disable_if` rule; assert the rule wins over the toggle list.

### Tokenization
- `test_report_tokens_match_fixture` — fixture with a known tokenizer stub (returns a fixed token count per call); assert the rendered per-skill token count matches the stub's output for `f"{name} {description}"`.
- `test_report_total_tokens` — assert the `total_tokens` row equals the sum of per-skill counts.
- `test_report_pct_of_cap` — assert the `pct_of_cap` column equals `total_tokens / 1024 * 100` rounded to one decimal.
- `test_report_tokenizer_fallback_chars_div_4` — fixture with no tokenizer; assert the reporter uses `len(rendered) // 4`; a bilingual warning is logged once.
- `test_report_tokenizer_raises_uses_fallback` — fixture where the tokenizer raises on every call; assert the reporter falls back to `len(rendered) // 4` and continues (no exception propagates to the caller).
- `test_report_no_circular_import_with_tools_skills_tool` — assert the reporter does NOT import `tools.skills_tool` at module top-level (the import direction would be agent<->tools cyclic); the constant is local or imported lazily inside the function.

### Usage (Curator)
- `test_report_curator_field_verification_recorded` — assert the fixture `tests/fixtures/curator/recorded_fields.json` exists, parses as JSON, and was updated within 7 days of HEAD (mtime sentinel).
- `test_report_usage_n_a_when_curator_absent` — fixture with no Curator module; assert every usage column renders `n/a`; the reporter exits 0.
- `test_report_usage_n_a_for_unseen_skill` — fixture with Curator + a skill present in the enabled set but absent from the Curator's records; assert the per-row usage columns render `n/a` for that skill.
- `test_report_usage_view_use_patch_counts` — fixture with a known Curator record; assert `use_count`, `patch_count`, and `view_count` (if recorded) match the fixture's recorded values.
- `test_report_usage_last_used_iso8601` — assert `last_used` is rendered as an ISO 8601 string; assert the column is sortable.
- `test_report_usage_does_not_invent_fields` — assert the reporter does NOT render any field name that is not in `recorded_fields.json` (defensive against Curator schema drift).

### Sorting
- `test_report_sort_by_tokens` — fixture with three skills of different token counts; assert the rendered order is descending by tokens.
- `test_report_sort_by_use_count` — fixture with three skills of different use counts; assert the rendered order is descending by use_count, with `n/a` rows last.
- `test_report_sort_by_last_used` — fixture with three skills of different last_used timestamps; assert the rendered order is most-recent first, with `n/a` rows last.
- `test_report_sort_stable_secondary_key_by_name` — fixture with two skills of equal primary key; assert the secondary sort is by name ascending.
- `test_report_default_sort_is_tokens` — no `--sort`; assert the rendered order matches `--sort tokens`.

### Output format
- `test_report_text_format_columns` — fixture; assert the plain-text output contains all expected columns and the rows are aligned.
- `test_report_text_format_truncates_description_to_60` — fixture with a 200-char description; assert the text output shows 60 chars + ellipsis; the JSON output preserves the full text.
- `test_report_json_format_shape` — `--format=json`; assert the JSON shape matches the documented schema (profile_name, enabled_skills[], total_tokens).
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

- **AC-7.1** READ-ONLY — `test_report_read_only_zero_writes` + `test_report_no_write_calls_in_source` + `test_report_rejects_apply_flag` + `test_report_json_path_outside_fixture`.
- **AC-7.2** `--profile`, `--sort`, `--format`, `--json` — `test_report_named_profile` + sort tests + `test_report_text_format_columns` + `test_report_json_format_shape`.
- **AC-7.3** `--help` bilingual two-section — `test_report_help_is_bilingual`.
- **AC-7.4** shares enabled-detection with Script #2 — `test_report_shares_enabled_detection_with_script_2` + the platform / toggle / conditional-exclusion tests.
- **AC-7.5** tokens from rendered name+description — `test_report_tokens_match_fixture` + `test_report_total_tokens` + `test_report_pct_of_cap` + `test_report_tokenizer_fallback_chars_div_4` + `test_report_tokenizer_raises_uses_fallback`.
- **AC-7.6** usage from Curator, n/a when missing — `test_report_curator_field_verification_recorded` + `test_report_usage_n_a_when_curator_absent` + `test_report_usage_n_a_for_unseen_skill` + `test_report_usage_does_not_invent_fields`.
- **AC-7.7** 100% coverage, TDD — `test_report_coverage_100_percent` + the TDD ordering documented in "Definition of Done".

<!-- end of file: 236 lines (budget 400) -->
