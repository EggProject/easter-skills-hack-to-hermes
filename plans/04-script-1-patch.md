<!-- title: Script #1 — idempotent cap-raise + (opt-in) Task E patch -->
<!-- scope: Sec 5.2 + Sec 6.B. Run against a user-owned Hermes checkout (NEVER ~/.hermes/hermes-agent). -->
<!-- ACs covered: AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.5.1, AC-2.6, AC-2.7, AC-2.8 (Task E flag), AC-2.9, AC-2.10 -->

# 04 — Script #1: Idempotent Patch Script

## Goal

Raise the silent 60-char `extract_skill_description` cap (and, opt-in, redirect the 7 Task E built-in-prompt sites) in a **user-owned** Hermes checkout. The script MUST refuse to run against `~/.hermes/hermes-agent`. The plugin performs NO cap-raise — Script #1 is the SOLE writer.

## Provenance

- **GitHub issue(s):** TBD (verify via WebFetch at Phase 5 implementation; do NOT emit unverified refs into `MIGRATION.hermes-patch.md` — same gate as 08).
- **Upstream commit:** `36ae958473b8530ffb1a395c4944b8cdbcae82fe` (NousResearch/hermes-agent @ main). Commit SHA is verified against the local `~/.hermes/hermes-agent` checkout used during planning; do NOT mark the *reason* the cap-raise is needed as verified by this SHA alone — the cap-raise need is a **code-shape** fact observable from `agent/skill_utils.py` regardless of upstream issue state.
- **Cap-raise target:** `agent/skill_utils.py` `extract_skill_description` — TWO co-located sites that MUST be patched together:
  1. The length-check predicate `if len(desc) > 60:` (the silent drop threshold).
  2. The slice-and-ellipsis return `return desc[:57] + "..."` (the truncation expression).

  Both sites encode the same 60-char cap in two places; raising only one breaks the function (the check passes but the slice still chops, or the slice is loosened but the check still drops). They are a single logical edit (`S1.cap`) and Script #1 patches them atomically (see "All-or-nothing gate" below).

## Cap-raise sites (the one default site, with both B2 lines)

The cap-raise has TWO co-located edits in `agent/skill_utils.py` (function `extract_skill_description`). Both MUST be applied atomically as `S1.cap` — if either fails, neither is written.

| site_id | file (relative to `--target`) | symbol | current_text (8+ char anchor) | replacement_text |
| --- | --- | --- | --- | --- |
| `S1.cap.a` | `agent/skill_utils.py` | `extract_skill_description` | `if len(desc) > 60:` | `if len(desc) > MAX_DESCRIPTION_LENGTH:` |
| `S1.cap.b` | `agent/skill_utils.py` | `extract_skill_description` | `return desc[:57] + "..."` | `return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` |

`MAX_DESCRIPTION_LENGTH` = 1024 is defined in `tools/skills_tool.py`. Two acceptable import strategies, picked in this order:

1. **Preferred:** insert `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` at the top of `agent/skill_utils.py`.
   - **Pre-flight check (CI / pre-commit / script startup):** `python -c "from tools.skills_tool import MAX_DESCRIPTION_LENGTH"` must succeed when run from the target checkout root, AND `agent/skill_utils.py` must NOT already import anything from `tools.skills_tool` that would create a cycle. The script MUST grep the top of `agent/skill_utils.py` for `from tools.skills_tool import` and abort with exit 4 ("potential circular import — define a local constant _MAX_DESCRIPTION_LENGTH = 1024 instead") if it finds one.
2. **Fallback (always safe):** define a local constant `_MAX_DESCRIPTION_LENGTH = 1024` at the top of `agent/skill_utils.py` (above `extract_skill_description`). The fallback is the default unless the import-pre-flight passes.

The replacement is idempotent: re-running detects the new `MAX_DESCRIPTION_LENGTH` (or `_MAX_DESCRIPTION_LENGTH`) reference and exits 0 with `OK: already patched / OK: már javítva`.

## Task E sites (opt-in, `--task-e-redirect`)

See `05-script-1-task-e-toggle.md` for the 7-site table. Default mode NEVER touches Task E.

## CLI surface

```
Usage (English):
  uv run hermes-skill-creator-patch --check      --target <dir>
  uv run hermes-skill-creator-patch --apply      --target <dir> [--task-e-redirect] [--i-accept-line-drift]
  uv run hermes-skill-creator-patch --emit-migration-note --target <dir>
  uv run hermes-skill-creator-patch --help

Használat (magyar):
  uv run hermes-skill-creator-patch --check      --target <mappa>
  uv run hermes-skill-creator-patch --apply      --target <mappa> [--task-e-redirect] [--i-accept-line-drift]
  uv run hermes-skill-creator-patch --emit-migration-note --target <mappa>
  uv run hermes-skill-creator-patch --help

Options:
  --target DIR                 REQUIRED. User-owned Hermes checkout. Refuses
                               ~/.hermes/hermes-agent (resolve() comparison).
  --check                      Audit only; no writes. Default.
  --apply                      Write the patch atomically.
  --task-e-redirect            Opt-in: also patch the 7 Task E sites.
  --i-accept-line-drift        Required iff --force is set; explicit second
                               confirmation. Without it, --force exits 5.
  --force                      Line-only override. Requires --i-accept-line-drift.
                               Retries ONLY sites with LINE_DRIFT diagnostic.
                               Reads .patch.state.json sidecar to skip
                               already-matched sites (see resume semantics).
  --emit-migration-note        Regenerates MIGRATION.hermes-patch.md and
                               MIGRATION.md index in the WORKTREE (not the
                               target). See 08-migration-note-format.md.
  --yes                        Suppresses interactive TTY confirmation for
                               --force. --yes alone does not bypass --target
                               refusal.
  --verbose                    Print bilingual per-site diagnostics.
  --help                       Show this help.
```

## Exit code matrix

| code | meaning | remediation printed in diagnostic |
| --- | --- | --- |
| 0 | OK / no-op / already patched | n/a |
| 1 | validation failure (text+line mismatch) | "Re-run with --force after reviewing the diff" |
| 2 | LINE_DRIFT (one or more sites drifted) | "Re-run with --force --i-accept-line-drift to retry line-only" |
| 3 | permission denied (target not writable) | "chmod u+w <target> or pick a writable target" |
| 4 | I/O error (--target missing, equals ~/.hermes/hermes-agent, agent/skill_utils.py absent, or pre-flight import cycle detected) | bilingual I/O diagnostic with the exact reason |
| 5 | user abort (interactive prompt declined; --force without --i-accept-line-drift) | n/a |

## Multi-signal targeting (AC-2.2)

Each site is identified by BOTH:
1. An 8+ char unique anchor string from the file's current text.
2. A 1-based line number.

Mismatch on either → `LINE_DRIFT` (line) or `TEXT_DRIFT` (anchor). Both abort the run; no site is partially written.

`S1.cap` is a single `site_id` with TWO anchor lines (a + b). Both anchors must match before any write; if one matches and the other does not, the whole `S1.cap` group fails and zero bytes are written.

## All-or-nothing gate (AC-2.3)

1. **Pre-validate every site** in a single pass before any write.
2. If ALL pass → proceed to atomic write (see below).
3. If ANY fails → write `.patch.rejected` report naming the failing site, exit non-zero, **zero bytes written to the target**.

`.patch.rejected` format (JSON, one per failed run):
```json
{
  "tool": "hermes-skill-creator-patch",
  "version": "0.1.0",
  "target": "<resolved-target-path>",
  "git_head": "<sha of target>",
  "failures": [
    {"site_id": "S1.cap", "reason": "TEXT_DRIFT", "expected": "if len(desc) > 60:", "actual_at_line_<n>": "if len(desc) > 1024:"}
  ],
  "remediation_en": "Re-run with --force --i-accept-line-drift after reviewing the diff.",
  "remediation_hu": "Futtassa újra --force --i-accept-line-drift kapcsolóval a diff átnézése után."
}
```

## Atomic write protocol

For every patched file:
1. Read the original bytes.
2. Compute the patched bytes in-memory.
3. Write the patched bytes to `<file>.patch.tmp` (same dir, `os.O_CREAT | os.O_EXCL`, mode 0o644 minus umask).
4. `os.replace(<file>.patch.tmp, <file>)` (POSIX-atomic on same filesystem).
5. On any exception in steps 1–4: delete `<file>.patch.tmp` if it exists, restore `<file>` from a pre-read snapshot, exit 3 (perm) or 4 (I/O).
6. Preserve file mode bits: `os.chmod(<file>, original_stat.st_mode, follow_symlinks=False)` after rename.

`.patch.state.json` sidecar (per `--target`): tracks `{site_id: "matched" | "drifted" | "patched"}`. `--force` reads it to skip `matched`/`patched` sites and retry only `drifted` sites.

## Idempotency (AC-2.1)

After a successful run, the next `--check` detects each site's `replacement_text` already present, prints `OK: already patched / OK: már javítva` per site, and exits 0. For `S1.cap`, both `a` and `b` anchors must be replaced for the site to be considered patched; partial replacement is treated as drift.

## Migration note row counts (AC-2.4 / M4)

`--emit-migration-note` writes `MIGRATION.hermes-patch.md` with EXACTLY:
- **Default mode (`--apply` alone):** 1 row (`S1.cap`).
- **`--apply --task-e-redirect`:** 1 + 7 = 8 rows.
- **`--apply --task-e-redirect --no-schema-redirect` (future flag, see `05`):** 1 + 6 = 7 rows.

The header table MUST match the actual count for the invocation mode. Counts are computed at runtime from the sites table; never hard-coded.

## Safety gates (HARD)

- `--target` is `argparse(required=True)`. Missing → exit 4 with `[en] --target is required. Refusing to run. / [hu] A --target kötelező. A szkript megtagadja a futtatást.`
- `Path.resolve()(--target) == Path.resolve()(Path.home() / ".hermes" / "hermes-agent")` → exit 4 with the exact resolved paths in both languages.
- `--target/agent/skill_utils.py` must exist (otherwise the cap-raise site cannot be located) → exit 4.
- Pre-flight `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` cycle check (see Cap-raise sites §1) — abort with exit 4 if a cycle is detected.

## Bilingual format (HARD)

Every `print()` and `logger.{info,warning,error}` call MUST match `^\[en\] .+ / \[hu\] .+$`. Enforced by pre-commit hook (see `10-toolchain-and-conventions.md`). `--help` MUST use the two-section format above.

## TDD test list

### Happy path
- `test_apply_cap_only_default_idempotent` — first run patches S1.cap (both a + b), second run exits 0 with `OK: already patched / OK: már javítva`.
- `test_check_no_writes` — `--check` writes zero bytes to target (snapshot sha256 before/after identical).
- `test_apply_creates_state_sidecar` — `.patch.state.json` written with `{S1.cap: "patched"}`.
- `test_force_retries_only_drifted_sites` — pre-patch 1 of 1 sites via fixture; corrupt one; run --force; only the drifted site is re-applied; matched site sha256 unchanged.
- `test_emit_migration_note_writes_worktree_files` — `--emit-migration-note` writes `MIGRATION.md` and `MIGRATION.hermes-patch.md` to worktree root, NOT to target.
- `test_emit_migration_note_default_one_row` — default invocation writes a 1-row `MIGRATION.hermes-patch.md` table (cap only).
- `test_emit_migration_note_task_e_redirect_eight_rows` — `--task-e-redirect` writes an 8-row table (1 cap + 7 Task E).
- `test_emit_migration_note_byte_identical_across_runs` — run twice; assert sha256 of `MIGRATION.hermes-patch.md` matches.

### Cap-raise specifics (B2)
- `test_apply_cap_raise_with_long_description` — fixture where `extract_skill_description` is called with a >1024-char description; after patch, the function returns ~1021 chars (`MAX_DESCRIPTION_LENGTH - 3 + "..."`), NOT 60 chars. Asserts both `S1.cap.a` and `S1.cap.b` were applied.
- `test_apply_cap_raise_two_sites_atomic` — fixture where `S1.cap.a` is valid and `S1.cap.b` is corrupted; `--apply` exits non-zero AND target file sha256 byte-identical to pre-run; `.patch.rejected` names `S1.cap`.
- `test_apply_cap_raise_max_description_length_defined` — assert `MAX_DESCRIPTION_LENGTH` is importable from `tools.skills_tool` AND, if the import-strategy pre-flight detects a cycle, a local `_MAX_DESCRIPTION_LENGTH = 1024` constant is defined at the top of `agent/skill_utils.py`. Both branches of the import-strategy decision are covered.

### Task E composition
- `test_task_e_default_off` — default `--apply` touches only `S1.cap`; sha256 of all 4 Task E files unchanged.
- `test_task_e_redirect_on` — `--apply --task-e-redirect` patches all 7 Task E sites + `S1.cap` (8 sites total).
- `test_task_e_per_site_anchors` — see `05-script-1-task-e-toggle.md` per-site tests.

### Error paths
- `test_target_required_exits_4` — `--target` unset → exit 4 with bilingual message.
- `test_target_resolves_to_hermes_agent_refused` — `--target=~/.hermes/hermes-agent` → exit 4 with the exact resolved paths.
- `test_target_missing_agent_skill_utils_exits_4` — `--target=/tmp/empty` → exit 4.
- `test_target_unwritable_exits_3` — chmod 0o555 the target file → exit 3.
- `test_partial_failure_zero_writes` — fixture with `S1.cap.a` valid and `S1.cap.b` corrupted; run `--apply`; assert (a) target file sha256 byte-identical to pre-run, (b) `.patch.rejected` exists, (c) it names `S1.cap`.
- `test_circular_import_preflight_exits_4` — fixture where `agent/skill_utils.py` already has `from tools.skills_tool import ...`; `--apply` aborts with exit 4 and a bilingual "potential circular import" diagnostic before any write.
- `test_force_without_i_accept_line_drift_exits_5` — `--force` alone → exit 5.
- `test_force_with_i_accept_line_drift_pauses_for_tty` — simulate TTY; script prints diff; operator confirms; patch applies; audit log appended.
- `test_force_still_drifts_exits_nonzero` — second drift after --force; exit non-zero with `LINE_DRIFT` again.
- `test_line_drift_exits_2_with_diagnostic` — corrupt only the line content (anchor matches, line does not); exit 2.
- `test_text_drift_exits_2_with_diagnostic` — anchor does not match; exit 2.

### Edge cases
- `test_apply_atomic_on_rename_failure` — mock `os.replace` to raise; original file unchanged; no `.patch.tmp` lingers.
- `test_apply_preserves_mode_bits` — original mode 0o600 survives the patch.
- `test_apply_cross_filesystem_target_warns` — `/tmp` and `~` on different devices → `os.replace` still works because target path is the FILE, not a directory; the warning is logged if `os.statvfs` differs.
- `test_zero_writes_on_validation_failure` — corrupt `S1.cap.a` anchor AND a Task E site; `--check` exits non-zero; target sha256 unchanged.
- `test_audit_log_appended_on_force` — `~/.hermes/patch-audit.log` (or worktree-local equivalent) gets a line per --force invocation with timestamp + diff hash.

### Bilingual format
- `test_help_is_bilingual` — `--help` output contains both "Usage (English)" and "Használat (magyar)" sections; mirrored content.
- `test_console_log_lines_match_bilingual_regex` — AST-grep every `print`/`logger.*` call in the script; assert format string matches `^\[en\] .+ / \[hu\] .+$`.

### Idempotency / coverage
- `test_check_already_patched_exits_0` — after a successful --apply, --check exits 0 with per-site `OK: already patched / OK: már javítva`.
- `test_state_sidecar_survives_re_run` — second `--apply` reads sidecar and skips matched sites (no re-write).
- `test_no_shebang_or_dunder_version_skew` — `__version__` constant matches `pyproject.toml`; CI assertion.

## Coverage target

100% line + branch coverage. Branches enumerated above. Every `argparse` choice exercised. Every exit code reachable by at least one test.

## Decisions & evidence

### D1. Cap-raise is a two-site atomic patch (B2)
- **Decision**: `S1.cap` patches BOTH the comparator (`if len(desc) > 60:` → `if len(desc) > MAX_DESCRIPTION_LENGTH:`) AND the slice (`return desc[:57] + "..."` → `return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."`) as a SINGLE `site_id` with two anchors.
- **Rationale**: the function encodes the cap in two places; patching only one breaks it (either the check still drops, or the slice still chops at 57). They are a single logical edit and MUST land atomically.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `agent/skill_utils.py:653` (comparator) and `:654` (slice); PC5 in 12; V3 [blocker B2]. Confidence: verified-from-source.

### D2. `MAX_DESCRIPTION_LENGTH` import strategy with circular-import guard
- **Decision**: prefer `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` at the top of `agent/skill_utils.py`; pre-flight check greps the existing file for any `from tools.skills_tool import` and aborts with exit 4 ("potential circular import — define a local constant _MAX_DESCRIPTION_LENGTH = 1024 instead") if found. Fallback is a LOCAL constant `_MAX_DESCRIPTION_LENGTH = 1024` defined at the top of `agent/skill_utils.py`.
- **Rationale**: `MAX_DESCRIPTION_LENGTH` already exists in `tools/skills_tool.py` (line 98). Reusing it keeps the patched cap aligned with the codebase idiom (slice `[:MAX_DESCRIPTION_LENGTH - 3]` matches lines 659 + 814 of the same file). The pre-flight guard prevents an `agent<->tools` cycle.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skills_tool.py:98, 659, 814`; 04 §Cap-raise sites; `test_apply_cap_raise_max_description_length_defined` in this file. Confidence: verified-from-source.

### D3. `--target` is REQUIRED (Q4)
- **Decision**: `--target` is `argparse(required=True)`. Missing → exit 4 with `[en] --target is required. Refusing to run. / [hu] A --target kötelező. A szkript megtagadja a futtatást.`
- **Rationale**: round-1 default behavior of "fall back to `~/.hermes/hermes-agent`" would mutate the installed Hermes and violate the HARD safety rule. Requiring an explicit user-owned checkout closes that door.
- **Evidence**: HITL-confirmed Q4; V3 [blocker from safety lens] `--target` required; AC-2.10 in 01; 04 §Safety gates. Confidence: verified-from-source.

### D4. `--force` requires `--i-accept-line-drift` as a SECOND flag (Q4 / AC-2.5.1)
- **Decision**: `--force` alone exits 5. `--force --i-accept-line-drift` pauses for TTY confirmation, prints the diff, and appends to `~/.hermes/patch-audit.log` with timestamp + diff hash.
- **Rationale**: round-1 review rejected `--force` as an auto-bypass; requiring a separate `--i-accept-line-drift` flag forces explicit acknowledgement that line-only targeting can patch the wrong site. The TTY pause + audit log closes the silent-bypass class.
- **Evidence**: V3 [major] `--force` safety; AC-2.5 / AC-2.5.1 in 01; 04 §Multi-signal targeting. Confidence: verified-from-source.

### D5. Multi-signal targeting: 8+ char anchor + 1-based line number (AC-2.2)
- **Decision**: every site is identified by BOTH a unique 8+ char anchor string AND a 1-based line number. Mismatch → `TEXT_DRIFT` (anchor) or `LINE_DRIFT` (line). Both abort the run.
- **Rationale**: a single-signal match (anchor only) is vulnerable to upstream drift and copy-paste duplication; the dual match makes accidental matches vanishingly unlikely.
- **Evidence**: V3 [major M3] (symbol + anchor, no hard line numbers); 04 §Multi-signal targeting; AC-2.2 in 01. Confidence: verified-from-source.

### D6. Atomic write protocol: tmp + `os.replace` + restore on exception
- **Decision**: every patched file is written via `<file>.patch.tmp` + `os.replace`, with the original bytes snapshotted in memory; on exception, the tmp file is deleted and the original restored. Mode bits preserved via `os.chmod`.
- **Rationale**: a direct `Path.write_text` would leave a half-written file on crash; the tmp + `os.replace` pair is POSIX-atomic on the same filesystem.
- **Evidence**: V3 [blocker from safety lens] atomic write; 04 §Atomic write protocol; `test_apply_atomic_on_rename_failure` in this file. Confidence: verified-from-source.

### D7. MIGRATION row counts: 1 (default) or 1+7 or 1+6 (with `--no-schema-redirect`)
- **Decision**: `--emit-migration-note` writes `MIGRATION.hermes-patch.md` with EXACTLY 1 row (cap only) by default; 1+7=8 rows with `--task-e-redirect`; 1+6=7 rows with `--task-e-redirect --no-schema-redirect`. Counts are computed at runtime from the sites table — never hard-coded.
- **Rationale**: hard-coded counts in the migration note have drifted in past rounds; computing from the live site table removes that drift.
- **Evidence**: V3 [major M4] T3 count; V4 R10 (R11 was about Script #3, not Script #1); 04 §Migration note row counts; AC-5.5 in 01. Confidence: verified-from-source.

<!-- end of file: 249 lines (budget 400) -->
