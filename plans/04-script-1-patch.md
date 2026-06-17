<!-- title: Script #1 — idempotent cap-raise + (opt-in) Task E patch -->
<!-- scope: Sec 5.2 + Sec 6.B. Run against a user-owned Hermes checkout (NEVER ~/.hermes/hermes-agent). -->
<!-- ACs covered: AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.5.1, AC-2.6, AC-2.7, AC-2.8 (Task E flag), AC-2.9, AC-2.10 -->

# 04 — Script #1: Idempotent Patch Script

## Goal

Raise the silent 60-char `extract_skill_description` cap (and, opt-in, redirect the 7 Task E built-in-prompt sites) in a **user-owned** Hermes checkout. The script MUST refuse to run against `~/.hermes/hermes-agent`. The plugin performs NO cap-raise — Script #1 is the SOLE writer.

## Cap-raise site (the one site that ships in default mode)

| site_id | file (relative to `--target`) | line | current_text (8+ char anchor) | replacement_text |
| --- | --- | --- | --- | --- |
| `S1.cap` | `agent/skill_utils.py` | 653 | `if len(desc) > 60:` | `if len(desc) > MAX_DESCRIPTION_LENGTH:` (inserted import: `from tools.skills_tool import MAX_DESCRIPTION_LENGTH`) |

The replacement is idempotent: re-running detects the new `MAX_DESCRIPTION_LENGTH` reference and exits 0 with `OK: already patched / OK: már javítva`.

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
| 4 | I/O error (--target missing, equals ~/.hermes/hermes-agent, or agent/skill_utils.py absent) | bilingual I/O diagnostic with the exact reason |
| 5 | user abort (interactive prompt declined; --force without --i-accept-line-drift) | n/a |

## Multi-signal targeting (AC-2.2)

Each site is identified by BOTH:
1. An 8+ char unique anchor string from the file's current text.
2. A 1-based line number.

Mismatch on either → `LINE_DRIFT` (line) or `TEXT_DRIFT` (anchor). Both abort the run; no site is partially written.

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
    {"site_id": "S1.cap", "reason": "TEXT_DRIFT", "expected": "if len(desc) > 60:", "actual_at_line_649": "if len(desc) > 1024:"}
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

After a successful run, the next `--check` detects each site's `replacement_text` already present, prints `OK: already patched / OK: már javítva` per site, and exits 0.

## Safety gates (HARD)

- `--target` is `argparse(required=True)`. Missing → exit 4 with `[en] --target is required. Refusing to run. / [hu] A --target kötelező. A szkript megtagadja a futtatást.`
- `Path.resolve()(--target) == Path.resolve()(Path.home() / ".hermes" / "hermes-agent")` → exit 4 with the exact resolved paths in both languages.
- `--target/agent/skill_utils.py` must exist (otherwise the cap-raise site cannot be located) → exit 4.

## Bilingual format (HARD)

Every `print()` and `logger.{info,warning,error}` call MUST match `^\[en\] .+ / \[hu\] .+$`. Enforced by pre-commit hook (see `10-toolchain-and-conventions.md`). `--help` MUST use the two-section format above.

## TDD test list

### Happy path
- `test_apply_cap_only_default_idempotent` — first run patches S1.cap, second run exits 0 with `OK: already patched / OK: már javítva`.
- `test_check_no_writes` — `--check` writes zero bytes to target (snapshot sha256 before/after identical).
- `test_apply_creates_state_sidecar` — `.patch.state.json` written with `{S1.cap: "patched"}`.
- `test_force_retries_only_drifted_sites` — pre-patch 1 of 1 sites via fixture; corrupt one; run --force; only the drifted site is re-applied; matched site sha256 unchanged.
- `test_emit_migration_note_writes_worktree_files` — `--emit-migration-note` writes `MIGRATION.md` and `MIGRATION.hermes-patch.md` to worktree root, NOT to target.

### Task E composition
- `test_task_e_default_off` — default `--apply` touches only S1.cap; sha256 of all 4 Task E files unchanged.
- `test_task_e_redirect_on` — `--apply --task-e-redirect` patches all 7 Task E sites + S1.cap.
- `test_task_e_per_site_anchors` — see `05-script-1-task-e-toggle.md` per-site tests.

### Error paths
- `test_target_required_exits_4` — `--target` unset → exit 4 with bilingual message.
- `test_target_resolves_to_hermes_agent_refused` — `--target=~/.hermes/hermes-agent` → exit 4 with the exact resolved paths.
- `test_target_missing_agent_skill_utils_exits_4` — `--target=/tmp/empty` → exit 4.
- `test_target_unwritable_exits_3` — chmod 0o555 the target file → exit 3.
- `test_partial_failure_zero_writes` — fixture with S1.cap valid and a Task E site (when flag is on) corrupted; run `--apply --task-e-redirect`; assert (a) target file sha256 byte-identical to pre-run, (b) `.patch.rejected` exists, (c) it names the failing site.
- `test_force_without_i_accept_line_drift_exits_5` — `--force` alone → exit 5.
- `test_force_with_i_accept_line_drift_pauses_for_tty` — simulate TTY; script prints diff; operator confirms; patch applies; audit log appended.
- `test_force_still_drifts_exits_nonzero` — second drift after --force; exit non-zero with `LINE_DRIFT` again.
- `test_line_drift_exits_2_with_diagnostic` — corrupt only the line content (anchor matches, line does not); exit 2.
- `test_text_drift_exits_2_with_diagnostic` — anchor does not match; exit 2.

### Edge cases
- `test_apply_atomic_on_rename_failure` — mock `os.replace` to raise; original file unchanged; no `.patch.tmp` lingers.
- `test_apply_preserves_mode_bits` — original mode 0o600 survives the patch.
- `test_apply_cross_filesystem_target_warns` — `/tmp` and `~` on different devices → `os.replace` still works because target path is the FILE, not a directory; the warning is logged if `os.statvfs` differs.
- `test_zero_writes_on_validation_failure` — corrupt S1.cap anchor AND a Task E site; `--check` exits non-zero; target sha256 unchanged.
- `test_audit_log_appended_on_force` — `~/.hermes/patch-audit.log` (or worktree-local equivalent) gets a line per --force invocation with timestamp + diff hash.

### Bilingual format
- `test_help_is_bilingual` — `--help` output contains both "Usage (English)" and "Hasznalat (magyar)" sections; mirrored content.
- `test_console_log_lines_match_bilingual_regex` — AST-grep every `print`/`logger.*` call in the script; assert format string matches `^\[en\] .+ / \[hu\] .+$`.

### Idempotency / coverage
- `test_check_already_patched_exits_0` — after a successful --apply, --check exits 0 with per-site `OK: already patched / OK: már javítva`.
- `test_emit_migration_note_byte_identical_across_runs` — run twice; assert sha256 of `MIGRATION.hermes-patch.md` matches.
- `test_state_sidecar_survives_re_run` — second `--apply` reads sidecar and skips matched sites (no re-write).
- `test_no_shebang_or_dunder_version_skew` — `__version__` constant matches `pyproject.toml`; CI assertion.

## Coverage target

100% line + branch coverage. Branches enumerated above. Every `argparse` choice exercised. Every exit code reachable by at least one test.

<!-- end of file: 173 lines (budget 400) -->
