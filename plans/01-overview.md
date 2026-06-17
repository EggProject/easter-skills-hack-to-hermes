<!-- title: Overview, deliverables, acceptance criteria (1.x–6.x) -->
<!-- scope: Mission + ACs. Carries the post-Diagnose fixes (AC-2.4, AC-2.5.1, AC-4.10, bilingual format, MIGRATION split). -->
<!-- ACs covered: ALL 1.x–6.x -->

# 01 — Overview, Deliverables, Acceptance Criteria

## Mission

Migrate the Anthropic official `skill-creator` (pinned 2a40fd2e7c52207aa903bd33fc4c65716126966e) to a Hermes-native standalone skill, ship a Hermes plugin that emits a one-time bilingual advisory when the 60-char `extract_skill_description` cap is detected un-raised, ship two idempotent operator scripts (patch + profile-manager), and emit a 3-file AI-readable migration note. The work is staged entirely in this worktree; the installed Hermes at `~/.hermes/hermes-agent` is never modified.

## Deliverables (mapped to brief sections)

| Brief | Deliverable | Plan file |
| --- | --- | --- |
| §5.1 | Hermes plugin that re-publishes the migrated `skill-creator` skill + emits a one-time bilingual advisory when the 60-char cap is detected un-raised. The actual cap-raise is performed by Script #1 (NOT by the plugin). | `03-plugin-spec.md` |
| §5.2 | Script #1: idempotent patch with multi-signal targeting (text+line), all-or-nothing gate, `--force --i-accept-line-drift` (NEVER auto-bypass), opt-in Task E toggle (7 sites), atomic write, `--emit-migration-note`. | `04-script-1-patch.md`, `05-script-1-task-e-toggle.md` |
| §5.3 | Script #2: per-profile audit/flip — disables `openai` + (if present) `skills`; installs the migrated skill-creator via hub; deterministic JSON report; `hermes_home_scope` context manager. | `06-script-2-profiles.md` |
| §5.4 | Migrated `skill-creator` skill: standalone, named `skill-creator`, passes the hermes-agent-skill-authoring validator, every Claude-specific invocation replaced per the T3 inventory, Claude strengths preserved (subagent split, eval pipeline, eval viewer), HERMES_SESSION nesting-guard helper. | `07-skill-creator-migration.md` |
| §5.5 | AI-readable migration note: 3-file split — `MIGRATION.md` (index) + `MIGRATION.hermes-patch.md` (Script #1) + `MIGRATION.skill-port.md` (migrated skill). | `08-migration-note-format.md` |
| §5.6 | The plan files themselves (this output). | `00`–`12` |

## Acceptance criteria

### 1. Plugin (§5.1)

- **AC-1.1** The plugin lives at `src/hermes_skill_creator_plugin/` with manifest `plugin.json` declaring `name=hermes-skill-creator-plugin`, `kind=skill_authoring`, `version=0.1.0`. Manifest passes the hermes-agent-skill-authoring validator (run as a subprocess test).
- **AC-1.2** The plugin's `on_session_start` hook performs a SIDE-EFFECT-FREE static AST read of the operator's Hermes checkout (resolved from `HERMES_HERMES_AGENT_TARGET` or, as a fallback, the live `~/.hermes/hermes-agent`) to detect the cap state. If `unpatched`, it writes a marker file under `HERMES_HOME` and emits a one-time bilingual log line. Subsequent sessions with the marker present are silent.
- **AC-1.3** The plugin performs NO cap mutation — neither file write NOR in-process `setattr` on `agent.skill_utils` (or any other Hermes module). The actual cap-raise is Script #1's responsibility against a user-owned checkout. This is enforced by an import-graph test (`test_hooks_does_not_setattr_on_skill_utils`).
- **AC-1.4** The plugin exposes a `register` entry point that calls `ctx.register_skill('skill-creator', ...)` with the BUNDLED frontmatter (NOT a user-local copy at `~/.hermes/skills/<cat>/skill-creator/`). The user-local copy (if present) is preserved and authoritative for `skill_view`; the bundled copy is authoritative for the system-prompt index. Documented in 12-risks R5.
- **AC-1.5** The plugin passes `hermes-agent-skill-authoring` frontmatter validation (64-char name, 1024-char description, 8–15k char body, supported top-level category, `metadata.hermes.tags` and `metadata.hermes.related_skills`).

### 2. Script #1 (§5.2 + §6.B + §6.E)

- **AC-2.1** Idempotent: re-running on a patched file is a no-op that exits 0 with `OK: already patched / OK: már javítva` per site.
- **AC-2.2** Multi-signal targeting: every site is identified by BOTH a unique 8+ char anchor string AND a 1-based line number; mismatch exits non-zero with a structured diagnostic.
- **AC-2.3** All-or-nothing validation gate: if any one site fails pre-validation, the script writes a `.patch.rejected` report and exits non-zero WITHOUT writing any file (zero bytes written to the target).
- **AC-2.4** Line drift: if the file's content at the expected line does not match the expected current text, the script emits a `LINE_DRIFT` diagnostic with the actual vs expected line, then EXITS 2. The operator MUST explicitly re-run with `--force --i-accept-line-drift` to retry line-only. **Default mode NEVER auto-bypasses the text+line match.**
- **AC-2.5** `--force`: forces line-number-based targeting only, skipping the text-signal match. Retries ONLY sites with `LINE_DRIFT` diagnostic; already-matched sites are NOT re-applied. Reads `.patch.state.json` sidecar.
- **AC-2.5.1** `--force` REQUIRES a second `--i-accept-line-drift` flag. Without it, `--force` exits 5 (user abort). With it, the script prints the diff and pauses for TTY confirmation; the invocation is appended to `~/.hermes/patch-audit.log` with timestamp + diff hash. Bilingual.
- **AC-2.6** `--check`: audit only; no writes.
- **AC-2.7** `--apply`: writes the patch.
- **AC-2.8** Opt-in Task E built-in-prompt toggle: `--task-e-redirect` applies the 7 Task E sites from `docs/maybe-patch-points.md`; absent flag → no Task E site is touched. `--no-schema-redirect` skips the OPTIONAL E6 site.
- **AC-2.9** `--help` output is bilingual EN+HU: two top-level sections ("Usage (English)" and "Használat (magyar)") with mirrored content.
- **AC-2.10** Exit codes: 0=OK/no-op, 1=validation failure, 2=line drift, 3=permission denied, 4=I/O error (incl. `--target` missing or equal to `~/.hermes/hermes-agent`), 5=user abort (incl. `--force` without `--i-accept-line-drift`).

### 3. Script #2 (§5.3 + §6.C)

- **AC-3.1** Audits the `hermes` (default) profile AND every named profile returned by `hermes_cli.profiles.list_profiles()`.
- **AC-3.2** For each profile, computes the desired state: `openai` disabled, `skills` disabled (if present as a global plugin), `skill-creator` installed via hub if absent, reinstalled/updated if present.
- **AC-3.3** Default mode is dry-run: prints a bilingual EN+HU diff per profile and exits 0 without writing.
- **AC-3.4** `--apply` performs the writes inside `hermes_home_scope(path)` which sets BOTH `hermes_constants.set_hermes_home_override(path)` AND `os.environ['HERMES_HOME']=str(path)`, restoring both on exit (try/finally). This is the single context manager used by both the installer (03) and Script #2.
- **AC-3.5** Audit JSON is deterministic across runs: keyed by `(profile_name, skill_name)`, sorted, stable timestamps (frozen under `HERMES_SKILL_CREATOR_FROZEN_TIME`).
- **AC-3.6** Per-profile `do_install(identifier, ..., force=True, skip_confirm=True, invalidate_cache=True, name_override="")` is called inside `hermes_home_scope` (no path= arg to `load_config`/`save_config`).
- **AC-3.7** Audit output: `{profile_name, current_disabled[], current_installed[], desired_disabled[], desired_installed[], diff: {added, removed}, actions_taken, errors}` per profile.
- **AC-3.8** Calls `clear_skills_system_prompt_cache(clear_snapshot=True)` after each successful flip. If the function does not exist in v0.16.0, falls back to deleting `~/.hermes/.skills_prompt_snapshot.json` directly.
- **AC-3.9** `--help` output is bilingual EN+HU (two top-level sections, mirrored content).
- **AC-3.10** Walks `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` (NOT `gateway/` as a subdir). `gateway.pid` is a flat file in the profile root, stat-only.

### 4. Migrated skill-creator (§5.4 + §6.D)

- **AC-4.1** Lives at `src/hermes_skill_creator_plugin/skills/skill-creator/`.
- **AC-4.2** Frontmatter: `name=skill-creator`, `description` <= 60 chars (in `SKILL.md.short`) and a second variant <= 1024 chars (in `SKILL.md`) — the installer selects the right one based on the detected cap state. `metadata.hermes.tags=[authoring, validation, eval, migration]`, `metadata.hermes.related_skills=[hermes-agent-skill-authoring]`.
- **AC-4.3** Subagent split: `agents/{grader,analyzer,comparator}.md` (lowercase per Hermes convention) preserved with the same semantic roles; registered as `agent_name` in Hermes's subagent dispatch.
- **AC-4.4** Eval pipeline: `scripts/{run_eval.py, aggregate_benchmark.py, generate_report.py, improve_description.py, quick_validate.py, package_skill.py, utils.py}` preserved and ported to Hermes.
- **AC-4.5** Every Claude-specific invocation replaced per the T3 inventory (15 rows in 07).
- **AC-4.6** Nesting-guard var: `HERMES_SESSION` (default, TBD per 12-Q1). The `hermes_subprocess_env()` helper in `src/hermes_skill_creator_plugin/_subprocess.py` is the SINGLE source of truth for the var name. The parent process NEVER `os.environ.pop`s the var; the helper strips it from the subprocess env only.
- **AC-4.7** Tool-name matches use `tool_name.lower() in (...)` (Hermes tool names are lowercase per `allowedAndForbiddenInvocations` in `plans/_research/hermesSkillConventions.json`).
- **AC-4.8** CLI invocations use `hermes` not `claude`.
- **AC-4.9** Eval viewer (`eval-viewer/{generate_review.py, viewer.html}`) preserved; `generate_review.py` updated to read Hermes-style streaming JSON event shape (TBD per 12-Q2; adapter-based).
- **AC-4.10** Active-cap detection: the installer MUST detect the active cap (60 vs 1024) by static AST read of `agent/skill_utils.py` at the active target checkout (or the live `~/.hermes/hermes-agent` if `HERMES_HERMES_AGENT_TARGET` is unset). If the description exceeds the active cap, refuse the install with a bilingual error and instruct the operator to apply Script #1 first.

### 5. Migration note (§5.5)

- **AC-5.1** 3-file split: `MIGRATION.md` (top-level index, worktree root) + `MIGRATION.hermes-patch.md` (Script #1's sites, worktree root) + `MIGRATION.skill-port.md` (migrated skill's T3 inventory, worktree root). All three are source-controlled.
- **AC-5.2** Each file contains: source repo URL, skillId, pinned commit hash (Script #1 target git head OR Anthropic upstream commit), exhaustive table.
- **AC-5.3** Changelog table columns: `path:line | current | replacement | anchor` (for `MIGRATION.hermes-patch.md`) and `path:line | claude-binding | hermes-binding | test-id` (for `MIGRATION.skill-port.md`).
- **AC-5.4** Emitted by `--emit-migration-note` on Script #1 (regenerates `MIGRATION.hermes-patch.md` and `MIGRATION.md`) and by the migrated skill's own installer (regenerates `MIGRATION.skill-port.md`). The files are the authoritative artifacts for downstream AI agents.
- **AC-5.5** Determinism + exhaustiveness: byte-identical across runs given the same input and `HERMES_SKILL_CREATOR_FROZEN_TIME`; row count == the T3 inventory count (15) for `MIGRATION.skill-port.md`; row count == 1 (cap) + (7 or 6, depending on `--no-schema-redirect`) for `MIGRATION.hermes-patch.md`.

### 6. Plan files (§5.6)

- **AC-6.1** All files <= 500 lines. Sum <= 4500 (per the per-file budget in `00-index.md`). Enforced by pre-commit hook `tools/check_line_count.py`.
- **AC-6.2** Each file declares its own test cases up front (TDD).
- **AC-6.3** Bilingual console/log messages (single-line `[en] ... / [hu] ...`); code in English. Bilingual `--help` output (two top-level sections). Enforced by pre-commit hook `tools/check_bilingual.py` + `test_help_is_bilingual` per entry point.
- **AC-6.4** Sub-agent delegation map included (`11-sub-agent-delegation-map.md`).

## Fix ledger

- **AC-2.4** rewritten: was "retried with --force" (auto-bypass), now "exits 2; operator must re-run with --force --i-accept-line-drift". (Fixes [blocker from overview lens] AC 2.4.)
- **AC-2.5.1** added: --force requires --i-accept-line-drift second confirmation + TTY pause + audit log. (Fixes [major] --force safety.)
- **AC-4.10** added: active-cap detection at install time. (Fixes [blocker from overview lens] AC 4.2 / 4.10.)
- **AC-5.1** rewritten: MIGRATION is a 3-file split, all source-controlled. (Fixes [refuted claim 10] MIGRATION single file.)
- **AC-1.1** bilingual: "OK: already installed / OK: már telepítve". (Fixes [nit] bilingual format.)
- **AC-2.1** bilingual: "OK: already patched / OK: már javítva". (Fixes [nit] bilingual format.)
- **AC-1.3** tightened: no setattr on `agent.skill_utils` anywhere; enforced by import-graph test. (Fixes [blocker from safety lens] runtime monkey-patch.)
- **AC-2.10** added exit code 4 for I/O errors including `--target` missing/equal-to-`~/.hermes/hermes-agent`. (Fixes [blocker from safety lens] --target required.)
- **AC-3.4** / **AC-3.6** corrected: `hermes_home_scope` mirrors both `set_hermes_home_override` AND `os.environ['HERMES_HOME']`. (Fixes [refuted claim 3] load_config(path=...).)
- **AC-3.10** added: walks `_PROFILE_DIRS`; treats `gateway.pid` as a flat file. (Fixes [refuted claim 5] gateway/ subdir.)
- **AC-4.6** tightened: nesting-guard helper is the single source of truth; parent process never `os.environ.pop`s. (Fixes [refuted claim 11] env-var centralization.)

<!-- end of file: 101 lines (budget 150) -->
