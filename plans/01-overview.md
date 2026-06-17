<!-- title: Overview, deliverables, acceptance criteria (1.x–7.x) -->
<!-- scope: Mission + ACs. Carries the post-Diagnose fixes (AC-2.4, AC-2.5.1, AC-4.10, bilingual format, MIGRATION split) and the post-V3 fixes (plugin manifest plugin.yaml, flat-skill install via Script #2, skill as separate top-level deliverable, Script #3 reporter). -->
<!-- ACs covered: ALL 1.x–7.x -->

# 01 — Overview, Deliverables, Acceptance Criteria

## Mission

Migrate the Anthropic official `skill-creator` (pinned 2a40fd2e7c52207aa903bd33fc4c65716126966e) to a Hermes-native standalone skill, ship a Hermes plugin that emits a one-time bilingual advisory when the 60-char `extract_skill_description` cap is detected un-raised, ship three idempotent operator scripts (patch + profile-manager + read-only reporter), and emit a 3-file AI-readable migration note. The work is staged entirely in this worktree; the installed Hermes at `~/.hermes/hermes-agent` is never modified.

## Deliverables (mapped to brief sections)

| Brief | Deliverable | Plan file |
| --- | --- | --- |
| §5.1 | Hermes plugin that emits a one-time bilingual advisory when the 60-char cap is detected un-raised. The actual cap-raise is performed by Script #1 (NOT by the plugin). The plugin is purely advisory — it does NOT bundle, contain, or own the migrated skill files. | `03-plugin-spec.md` |
| §5.2 | Script #1: idempotent patch with multi-signal targeting (text+line), all-or-nothing gate, `--force --i-accept-line-drift` (NEVER auto-bypass), opt-in Task E toggle (7 sites), atomic write, `--emit-migration-note`. | `04-script-1-patch.md`, `05-script-1-task-e-toggle.md` |
| §5.3 | Script #2: per-profile audit/flip — disables `openai` + (if present) `skills`; installs the migrated skill-creator via hub at the FLAT path `~/.hermes/skills/skill-creator/` (this is what makes `skill-creator` appear in the `<available_skills>` system-prompt index); deterministic JSON report; `hermes_home_scope` context manager. | `06-script-2-profiles.md` |
| §5.4 | Migrated `skill-creator` skill: a STANDALONE top-level deliverable at `skills/skill-creator/` (worktree root, NOT nested inside the plugin package). Shipped/installed as a flat skill into `~/.hermes/skills/skill-creator/` via Script #2's `do_install`. Passes the hermes-agent-skill-authoring validator; every Claude-specific invocation replaced per the T3 inventory; Claude strengths preserved (subagent split, eval pipeline, eval viewer); `HERMES_SESSION` nesting-guard helper. | `07-skill-creator-migration.md` |
| §5.5 | AI-readable migration note: 3-file split — `MIGRATION.md` (index) + `MIGRATION.hermes-patch.md` (Script #1) + `MIGRATION.skill-port.md` (migrated skill). | `08-migration-note-format.md` |
| §5.6 | The plan files themselves (this output). | `00`–`12` |
| §5.7 (NEW) | Script #3: read-only profile-skill token + usage reporter (`hermes-skill-creator-report`). Lists ENABLED skills per profile; reports per-skill token estimate + use/last-used stats from the Curator; sorts; emits NO writes. Bilingual `--help`. | `06b-script-3-report.md` (referenced by 09, 10, 11) |

## Acceptance criteria

### 1. Plugin (§5.1)

- **AC-1.1** The plugin lives at `src/hermes_skill_creator_plugin/` with manifest `plugin.yaml` (NOT `plugin.json`) declaring `name=hermes-skill-creator-plugin`, `version=0.1.0`. The manifest does NOT declare a `kind` field (Hermes's plugin loader does not require one for a hook+skill plugin). Manifest passes the hermes-agent-skill-authoring validator (run as a subprocess test).
- **AC-1.2** The plugin's `on_session_start` hook performs a SIDE-EFFECT-FREE static AST read of the operator's Hermes checkout (resolved from `HERMES_HERMES_AGENT_TARGET` or, as a fallback, the live `~/.hermes/hermes-agent`) to detect the cap state. If `unpatched`, it writes a marker file under `HERMES_HOME` and emits a one-time bilingual log line. Subsequent sessions with the marker present are silent.
- **AC-1.3** The plugin performs NO cap mutation — neither file write NOR in-process `setattr` on `agent.skill_utils` (or any other Hermes module). The actual cap-raise is Script #1's responsibility against a user-owned checkout. This is enforced by an import-graph test (`test_hooks_does_not_setattr_on_skill_utils`).
- **AC-1.4** The plugin is PURELY ADVISORY. It does NOT call `ctx.register_skill('skill-creator', ...)` to surface the skill into the system prompt — `register_skill` resolves a plugin-registered skill ONLY as `<plugin_name>:<name>` via explicit `skill_view()`, does NOT place it in the flat `~/.hermes/skills/` tree, and does NOT list it in the `<available_skills>` system-prompt index. The migrated skill is surfaced INSTEAD by Script #2's `do_install`, which copies `skills/skill-creator/` to the flat `~/.hermes/skills/skill-creator/` path — this is what makes `skill-creator` appear in the `<available_skills>` index. The plugin's `on_session_start` hook is the sole stateful surface; it detects the cap and emits the advisory. The plugin may still call `ctx.register_skill` for its own internal helpers, but the migrated `skill-creator` skill files are never bundled inside, owned by, or shipped from the plugin package. Documented in 12-risks R5.
- **AC-1.5** The plugin's manifest passes `hermes-agent-skill-authoring` frontmatter validation (when an optional bundled helper skill is present): 64-char name, 1024-char description, 8–15k char body, supported top-level category, `metadata.hermes.tags` and `metadata.hermes.related_skills`.

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
- **AC-2.11** The cap-raise patch on `agent/skill_utils.py` `extract_skill_description` MUST change BOTH the predicate (`> 60` → `> MAX_DESCRIPTION_LENGTH`) AND the slice (`desc[:57]` → `desc[:MAX_DESCRIPTION_LENGTH - 3]`), so that a >1024-char description is truncated to ~1021 (matching the codebase's own idiom in `tools/skills_tool.py`). `MAX_DESCRIPTION_LENGTH` is the tools-layer cap (1024); reused via import or local constant, with import-direction check to avoid an agent<->tools circular import. A test covers a >1024-char description.

### 3. Script #2 (§5.3 + §6.C)

- **AC-3.1** Audits the `hermes` (default) profile AND every named profile returned by `hermes_cli.profiles.list_profiles()`.
- **AC-3.2** For each profile, computes the desired state: `openai` disabled, `skills` disabled (if present as a global plugin), `skill-creator` installed at the flat path `~/.hermes/skills/skill-creator/` via hub if absent, reinstalled/updated if present.
- **AC-3.3** Default mode is dry-run: prints a bilingual EN+HU diff per profile and exits 0 without writing.
- **AC-3.4** `--apply` performs the writes inside `hermes_home_scope(path)` which sets BOTH `hermes_constants.set_hermes_home_override(path)` AND `os.environ['HERMES_HOME']=str(path)`, restoring both on exit (try/finally). This is the single context manager used by both the installer (03) and Script #2.
- **AC-3.5** Audit JSON is deterministic across runs: keyed by `(profile_name, skill_name)`, sorted, stable timestamps (frozen under `HERMES_SKILL_CREATOR_FROZEN_TIME`).
- **AC-3.6** Per-profile `do_install(identifier, ..., force=True, skip_confirm=True, invalidate_cache=True, name_override="")` is called inside `hermes_home_scope` (no path= arg to `load_config`/`save_config`). The `identifier` resolves the migrated skill from the worktree-root `skills/skill-creator/` directory and copies it to the flat `~/.hermes/skills/skill-creator/` path.
- **AC-3.7** Audit output: `{profile_name, current_disabled[], current_installed[], desired_disabled[], desired_installed[], diff: {added, removed}, actions_taken, errors}` per profile.
- **AC-3.8** Calls `clear_skills_system_prompt_cache(clear_snapshot=True)` (imported from `agent.prompt_builder`) after each successful flip. No fallback to deleting a snapshot file at a literal `~/.hermes/...` path; if the function is unavailable, the script logs a bilingual warning and continues (the next session will rebuild the index).
- **AC-3.9** `--help` output is bilingual EN+HU (two top-level sections, mirrored content).
- **AC-3.10** Walks `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` (NOT `gateway/` as a subdir). `gateway.pid` is a flat file in the profile root, stat-only.
- **AC-3.11** `save_disabled_skills(config: dict, disabled: Set[str], platform: Optional[str] = None)` is called with the disabled set as the 2nd positional arg (NOT a `names=` kwarg, since the real signature at `hermes_cli/skills_config.py` does not accept it).

### 4. Migrated skill-creator (§5.4 + §6.D)

- **AC-4.1** Lives at `skills/skill-creator/` at the WORKTREE ROOT (a separate top-level deliverable, NOT inside the plugin package `src/hermes_skill_creator_plugin/`). Shipped/installed as a flat skill into `~/.hermes/skills/skill-creator/` via Script #2's `do_install` — this is also what makes it appear as `skill-creator` in the `<available_skills>` system-prompt index. The plugin must NOT bundle, contain, or own the skill files.
- **AC-4.2** Frontmatter: `name=skill-creator`, `description` <= 60 chars (in `SKILL.md.short`) and a second variant <= 1024 chars (in `SKILL.md`) — the installer selects the right one based on the detected cap state. `metadata.hermes.tags=[authoring, validation, eval, migration]`, `metadata.hermes.related_skills=[hermes-agent-skill-authoring]`.
- **AC-4.3** Subagent split: `agents/{grader,analyzer,comparator}.md` (lowercase per Hermes convention) preserved with the same semantic roles; registered as `agent_name` in Hermes's subagent dispatch.
- **AC-4.4** Eval pipeline: `scripts/{run_eval.py, aggregate_benchmark.py, generate_report.py, improve_description.py, quick_validate.py, package_skill.py, utils.py}` preserved and ported to Hermes.
- **AC-4.5** Every Claude-specific invocation replaced per the T3 inventory (18 rows in 07).
- **AC-4.6** Nesting-guard var: `HERMES_SESSION` (default, see 12-Q1). The `hermes_subprocess_env()` helper in `src/hermes_skill_creator_plugin/_subprocess.py` is the SINGLE source of truth for the var name. The parent process NEVER `os.environ.pop`s the var; the helper strips it from the subprocess env only.
- **AC-4.7** Tool-name matches use `tool_name.lower() in (...)` (Hermes tool names are lowercase per `allowedAndForbiddenInvocations` in `plans/_research/hermesSkillConventions.json`).
- **AC-4.8** CLI invocations use `hermes` not `claude`.
- **AC-4.9** Eval viewer (`eval-viewer/{generate_review.py, viewer.html}`) preserved; `generate_review.py` updated to read Hermes-style streaming JSON event shape (see 12-Q2; adapter-based).
- **AC-4.10** Active-cap detection: the installer MUST detect the active cap (60 vs 1024) by static AST read of `agent/skill_utils.py` at the active target checkout (or the live `~/.hermes/hermes-agent` if `HERMES_HERMES_AGENT_TARGET` is unset). If the description exceeds the active cap, refuse the install with a bilingual error and instruct the operator to apply Script #1 first.

### 5. Migration note (§5.5)

- **AC-5.1** 3-file split: `MIGRATION.md` (top-level index, worktree root) + `MIGRATION.hermes-patch.md` (Script #1's sites, worktree root) + `MIGRATION.skill-port.md` (migrated skill's T3 inventory, worktree root). All three are source-controlled.
- **AC-5.2** Each file contains: source repo URL, skillId, pinned commit hash (Script #1 target git head OR Anthropic upstream commit), exhaustive table.
- **AC-5.3** Changelog table columns: `path:line | current | replacement | anchor` (for `MIGRATION.hermes-patch.md`) and `path:line | claude-binding | hermes-binding | test-id` (for `MIGRATION.skill-port.md`).
- **AC-5.4** Emitted by `--emit-migration-note` on Script #1 (regenerates `MIGRATION.hermes-patch.md` and `MIGRATION.md`) and by the migrated skill's own installer (regenerates `MIGRATION.skill-port.md`). The files are the authoritative artifacts for downstream AI agents.
- **AC-5.5** Determinism + exhaustiveness: byte-identical across runs given the same input and `HERMES_SKILL_CREATOR_FROZEN_TIME`; row count == the T3 inventory count (18) for `MIGRATION.skill-port.md`; row count == 1 (cap) + (7 or 6, depending on `--no-schema-redirect`) for `MIGRATION.hermes-patch.md`.

### 6. Plan files (§5.6)

- **AC-6.1** All files <= 500 lines. Sum <= 4500 (per the per-file budget in `00-index.md`). Enforced by pre-commit hook `tools/check_line_count.py`.
- **AC-6.2** Each file declares its own test cases up front (TDD).
- **AC-6.3** Bilingual console/log messages (single-line `[en] ... / [hu] ...`); code in English. Bilingual `--help` output (two top-level sections). Enforced by pre-commit hook `tools/check_bilingual.py` + `test_help_is_bilingual` per entry point.
- **AC-6.4** Sub-agent delegation map included (`11-sub-agent-delegation-map.md`).

### 7. Script #3 — profile-skill token + usage reporter (§5.7 NEW)

- **AC-7.1** READ-ONLY: asserts zero bytes written against the fixture profile tree under all flag combinations (default, `--sort`, `--profile`, multi-profile). Implemented as an integration test that snapshots the tree, runs every flag combo, and re-snapshots to compare hashes.
- **AC-7.2** `--profile <name>` selects a single profile; without it, iterates the `hermes` (default) profile AND every named profile returned by `hermes_cli.profiles.list_profiles()` (same enumeration as Script #2, AC-3.1).
- **AC-7.3** Enabled-set detection REUSES Script #2's exact logic: the per-profile `config/skills.toml` `disabled` set, profile + platform combined with `platforms:` / conditional exclusions. NOT a re-implementation. A shared helper (`hermes_cli.skill_enablement.enabled_skills_for_profile`) is the single source of truth.
- **AC-7.4** Tokens: tokenize the RENDERED `name + " " + description` string with the configured model's tokenizer (loaded from the active model in `~/.hermes/config.yaml` or `HERMES_MODEL`); fallback to `len(text) // 4` when the tokenizer cannot be loaded. Report per-skill `tokens` and `total_tokens`; optionally project against the 1024 cap with a `% of cap` column.
- **AC-7.5** Usage: `view_count`, `use_count`, `patch_count`, `last_used` (ISO 8601), sourced from the Curator (project ref #45). The integration test FIRST verifies the actual storage backend + field names against the current Hermes source (a fixture recorded at test-write time); where the field is absent in the current source, the column shows `n/a` (not `0`, not blank). The verification gate is a test fixture file, not a live network call.
- **AC-7.6** Output: a sortable table (plain text default; `--format=json` optional) with columns `profile | name | tokens | use_count | patch_count | last_used | % of cap` (some columns may be hidden with `--columns`). `--sort tokens|use_count|last_used` reorders rows. `--help` is bilingual EN+HU, two-section ("Usage (English)" / "Használat (magyar)"), mirrored content.
- **AC-7.7** Integration: NEW standalone read-only entry point `hermes-skill-creator-report` declared under `[project.scripts]` in `pyproject.toml` (10). Referenced by `00-index.md`, `01-overview.md` (this file), `09-test-strategy.md` (TDD cases), and `11-sub-agent-delegation-map.md`. 100% code coverage + 100% branch coverage, enforced by `pytest --cov=hermes_skill_creator_plugin.report --cov-branch --cov-fail-under=100`.

## Fix ledger

- **AC-2.4** rewritten: was "retried with --force" (auto-bypass), now "exits 2; operator must re-run with --force --i-accept-line-drift". (Fixes [blocker from overview lens] AC 2.4.)
- **AC-2.5.1** added: --force requires --i-accept-line-drift second confirmation + TTY pause + audit log. (Fixes [major] --force safety.)
- **AC-4.10** added: active-cap detection at install time. (Fixes [blocker from overview lens] AC 4.2 / 4.10.)
- **AC-5.1** rewritten: MIGRATION is a 3-file split, all source-controlled. (Fixes [refuted claim 10] MIGRATION single file.)
- **AC-1.1** bilingual: "OK: already installed / OK: már telepítve". (Fixes [nit] bilingual format.) — V3: also dropped `kind=skill_authoring`; manifest is `plugin.yaml`.
- **AC-2.1** bilingual: "OK: already patched / OK: már javítva". (Fixes [nit] bilingual format.)
- **AC-1.3** tightened: no setattr on `agent.skill_utils` anywhere; enforced by import-graph test. (Fixes [blocker from safety lens] runtime monkey-patch.)
- **AC-2.10** added exit code 4 for I/O errors including `--target` missing/equal-to-`~/.hermes/hermes-agent`. (Fixes [blocker from safety lens] --target required.)
- **AC-2.11** added: cap-raise patch changes BOTH predicate and slice (so >1024-char desc truncates to ~1021, not 60). (V3 [blocker B2] cap-raise patch incomplete.)
- **AC-3.4** / **AC-3.6** corrected: `hermes_home_scope` mirrors both `set_hermes_home_override` AND `os.environ['HERMES_HOME']`. (Fixes [refuted claim 3] load_config(path=...).)
- **AC-3.8** corrected: cache-clear targets `agent.prompt_builder.clear_skills_system_prompt_cache(clear_snapshot=True)`; no literal-path fallback. (V3 [blocker B3] cache-clear API.)
- **AC-3.10** added: walks `_PROFILE_DIRS`; treats `gateway.pid` as a flat file. (Fixes [refuted claim 5] gateway/ subdir.)
- **AC-3.11** added: `save_disabled_skills` called with set as 2nd positional arg (real sig, no `names=` kwarg). (V3 [blocker B3] save_disabled_skills API.)
- **AC-4.1** rewritten: skill is a SEPARATE top-level deliverable at `skills/skill-creator/` (worktree root), NOT inside the plugin. (V3 [blocker B4] standalone skill.)
- **AC-4.5** / **AC-5.5** count aligned: T3 inventory is 18 rows. (V3 [major M4] T3 count.)
- **AC-4.6** tightened: nesting-guard helper is the single source of truth; parent process never `os.environ.pop`s. (Fixes [refuted claim 11] env-var centralization.)
- **AC-1.4** rewritten: plugin is purely advisory; skill is surfaced by Script #2's flat-path install. `register_skill` cannot achieve `<available_skills>` visibility. (V3 [blocker B3] plugin API mismatches + [blocker B4] standalone skill.)
- **AC-7.x** (NEW cluster): Script #3 read-only profile-skill token + usage reporter per brief §5.7.
- **00-index.md** arithmetic recomputed: sum = 2229 (was 2089 / 2231 — corrected per V3 [minor m1]). New breakdown includes `06b-script-3-report.md` (~165 lines) and adjusts `06-script-2-profiles.md` to ~180 (was 165).
- All hard line-number citations in AC text replaced with symbol + anchor-text references per V3 [major M3].

<!-- end of file: 150 lines (budget 150) -->
