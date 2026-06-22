# TODO.md — Continuously-Maintained Todo List (SPEC §5.7)

<!--
Purpose: Single source of truth for §5.7 "Folyamatosan karbantartott Todo lista".
Contract (SPEC L86-87 + L143 + L208):
  1. EXIST at worktree root — this file is the artifact.
  2. ULTRA-DETAILED — "hogy ne vesszen el semmi" (SPEC L208).
  3. APPENDED-TO (never deleted) on every plan review round.
  4. CONTAINS: open follow-ups, deferred items, known drift risks.

Maintenance protocol:
  - On each new review round / re-validation / code-review: APPEND a new dated
    section at the bottom ("Round N — YYYY-MM-DD"). NEVER delete earlier rounds.
  - When an item closes, move it from "Open" to "Closed (round N)" within its
    section — preserve the trail.
  - When a new drift risk surfaces, add a row to the Drift Risks table.
  - When a new finding lands (issue #17 / #33 / revalidation), add a row to the
    Findings Tracker.

Round inventory (always append, never reorder):
  - Round 0 — 2026-06-22 (initial seed, F-5.7-0 fix)
  - (future rounds added below by date)
-->

## 1. AC Cluster Status (01-overview.md §5.1–§5.X)

Mirrored from `docs/plans/01-overview.md` Acceptance Criteria. Status legend:
`DONE` = implemented + tests pass + docs reference, `PARTIAL` = code present
but a known gap remains, `TODO` = not started, `N/A` = out of scope.

| AC | Cluster | Status | Evidence | Notes |
|----|---------|--------|----------|-------|
| AC-1.1 | Plugin manifest `plugin.yaml` | DONE | PR #28 (AC-1.1 row); `src/hermes_skill_creator_plugin/plugin.yaml` exists | Manifest renamed JSON → YAML per V3 review |
| AC-1.2 | `on_session_start` hook static-AST cap detection | DONE | PR #28 | Marker file under HERMES_HOME; bilingual one-time advisory |
| AC-1.3 | Plugin performs NO cap mutation (no `setattr` on `agent.skill_utils`) | DONE | PR #28 | Enforced by `test_hooks_does_not_setattr_on_skill_utils` |
| AC-1.4 | Plugin is PURELY ADVISORY; `register_skill` not used for migrated skill | DONE | PR #28 | Skill installed by Script #2 flat-path |
| AC-1.5 | Plugin manifest passes hermes-agent-skill-authoring validator | DONE | PR #28 | Subprocess validator test |
| AC-2.1 | Idempotent re-run exits 0 with bilingual per-site OK | DONE | PR #28 (AC-2.1 docs) | Template `OK: site {site_id} already patched / OK: a {site_id} hely már javítva` |
| AC-2.2 | Multi-signal targeting (text+line, 8+ char anchor + 1-based line) | DONE | PR #28 | Mismatch exits non-zero with structured diagnostic |
| AC-2.3 | All-or-nothing validation gate, `.patch.rejected` on any failure | DONE | PR #28 (cc932d8 round 1) + eb8c94c round 2 | Rejected report keys: `actual_at_line_{N}` for LINE_DRIFT, `actual_at_line_unknown` for TEXT_DRIFT |
| AC-2.4 | Line drift → exit 2 with LINE_DRIFT diagnostic, NO auto-bypass | DONE | PR #28 | Operator MUST re-run with `--force --i-accept-line-drift` |
| AC-2.5 | `--force` retries ONLY STATE_DRIFTED sites, skips already-matched | DONE | PR #28 (PR-B/Fix #1) | Reads `.patch.state.json` sidecar |
| AC-2.5.1 | `--force` REQUIRES `--i-accept-line-drift`; TTY pause; audit log | DONE | PR #28 (PR-B/Fix #2 + #3) | Audit log moved to `~/.hermes/patch-audit.log` (per-invocation) |
| AC-2.6 | `--check` audit only, no writes | DONE | PR #28 | Bilingual |
| AC-2.7 | `--apply` writes the patch | DONE | PR #28 | Bilingual |
| AC-2.8 | Opt-in `--task-e-redirect` (7 or 6 sites), `--no-schema-redirect` skips E6 | DONE | PR #28 + eb8c94c round 2 | E0/E4b pair added for shared-constant; runtime total = 1 cap + 9 Task E = 10 sites |
| AC-2.9 | Bilingual `--help` (EN+HU, two top-level sections) | DONE | PR #28 | Enforced by `test_help_is_bilingual` per entry point |
| AC-2.10 | Exit codes 0/1/2/3/4/5 | DONE | PR #28 (PR-B/Fix #4) | `--yes` flag wired (exit 5 reachable) |
| AC-2.11 | Cap-raise patch changes BOTH predicate AND slice (`> MAX_DESCRIPTION_LENGTH` + `[:MAX_DESCRIPTION_LENGTH-3]`) | DONE | PR #28 (PR-B/Fix #5) + eb8c94c fallback | Pre-flight via subprocess import probe; fallback to local `_MAX_DESCRIPTION_LENGTH=1024` on circular import |
| AC-3.1 | Audits `hermes` (default) + all named profiles from `list_profiles()` | DONE | PR #28 | Empty-profile + single-profile + N-profile fixtures covered |
| AC-3.2 | Replaces factory `skill-creator` IN-PLACE via `do_install(force=True, ...)` | DONE | PR #28 (S5 BLOCKER fix) | Test renamed: `test_apply_disables_openai` → `test_apply_replaces_factory_skill_creator` |
| AC-3.3 | Default mode dry-run, bilingual per-profile diff | DONE | PR #28 | |
| AC-3.4 | `--apply` runs inside `hermes_home_scope(path)` mirroring BOTH override + env var | DONE | PR #28 | try/finally restore both |
| AC-3.5 | Deterministic JSON (frozen under `HERMES_SKILL_CREATOR_FROZEN_TIME`) | DONE | PR #28 | Sorted by `(profile_name, skill_name)` |
| AC-3.6 | Per-profile `do_install` inside `hermes_home_scope` (no `path=` kwarg) | DONE | PR #28 | |
| AC-3.7 | Audit JSON shape per profile | DONE | PR #28 | |
| AC-3.8 | Calls `clear_skills_system_prompt_cache(clear_snapshot=True)` | DONE | PR #28 | Import from `agent.prompt_builder`; bilingual warning on failure |
| AC-3.9 | Bilingual `--help` (EN+HU) | DONE | PR #28 | |
| AC-3.10 | Walks `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}`; `gateway.pid` flat file | DONE | PR #28 (PR-D) | |
| AC-3.11 | `save_disabled_skills(config, disabled_set, platform=None)` 2nd-positional | DONE | PR #28 | Real sig; no `names=` kwarg |
| AC-4.1 | Skill at `skills/skill-creator/` worktree root, NOT inside plugin | DONE | PR #28 | Standalone top-level deliverable |
| AC-4.2 | Frontmatter `name=skill-creator`, desc ≤60 OR ≤1024 variant, `metadata.hermes.tags=[authoring, validation, eval, migration]` | DONE | PR #28 | Installer selects based on active cap state |
| AC-4.3 | Subagent split `agents/{grader,analyzer,comparator}.md` lowercase | DONE | PR #28 | Hermes `agent_name` registration |
| AC-4.4 | Eval pipeline `scripts/{run_eval, aggregate_benchmark, generate_report, improve_description, quick_validate, package_skill, utils}.py` | DONE | PR #28 | |
| AC-4.5 | Every Claude-specific invocation replaced per T3 inventory (18 rows) | DONE | PR #28 | `MIGRATION.skill-port.md` 18 rows |
| AC-4.6 | Nesting-guard var `HERMES_SESSION`; helper `hermes_subprocess_env()` is SINGLE source of truth | DONE | PR #28 (PR-E) | `skills/skill-creator/_subprocess.py` canonical |
| AC-4.7 | Tool-name matches use `tool_name.lower() in (...)` | DONE | PR #28 | |
| AC-4.8 | CLI uses `hermes` not `claude` | DONE | PR #28 | |
| AC-4.9 | Eval viewer `eval-viewer/{generate_review.py, viewer.html}` updated to Hermes stream-json event shape (adapter-based) | DONE | PR #28 | T3.011 adapter row |
| AC-4.10 | Active-cap detection (60 vs 1024) at install time via static AST | DONE | PR #28 | Refuse install with bilingual error if desc > active cap |
| AC-5.1 | 3-file MIGRATION split (`MIGRATION.md` + `.hermes-patch.md` + `.skill-port.md`) | DONE | PR #28 (2b4a675 round 2) | All three source-controlled at worktree root |
| AC-5.2 | Each MIGRATION file contains source repo + skillId + pinned commit | DONE | PR #28 | |
| AC-5.3 | Changelog columns match generator template | DONE | PR #28 | |
| AC-5.4 | Emitted by `--emit-migration-note` + skill installer | DONE | PR #28 | |
| AC-5.5 | Determinism + exhaustiveness (1 / 1+7 / 1+6 / 18 rows) | DONE | PR #28 (PR-B + 2b4a675) | `HERMES_SKILL_CREATOR_FROZEN_TIME` |
| AC-6.1 | All plan files ≤500 lines, sum ≤4500 | DONE | PR #28 | Enforced by `tools/check_line_count.py` |
| AC-6.2 | Each plan file declares test cases up front (TDD) | DONE | PR #28 | |
| AC-6.3 | Bilingual console/log + code in English | DONE | PR #28 | Enforced by `tools/check_bilingual.py` |
| AC-6.4 | Sub-agent delegation map (`11-sub-agent-delegation-map.md`) | DONE | PR #28 | |
| AC-7.1 | Script #3 READ-ONLY, zero writes against fixture tree under all flag combos | DONE | PR #28 | Integration test snapshots + re-snapshots + compares hashes |
| AC-7.2 | `--profile` selects single or iterates all profiles | DONE | PR #28 | Same enumeration as Script #2 |
| AC-7.3 | Enabled-set detection REUSES Script #2's helper (`_enabled_detection.get_enabled_skills`) | DONE | PR #28 | Single source of truth |
| AC-7.4 | Tokens via configured model's tokenizer; fallback `len(text)//4` | DONE | PR #28 | Per-skill `tokens`, `total_tokens`, `% of cap` column |
| AC-7.5 | Usage `view_count`, `use_count`, `patch_count`, `last_used_at` from Curator | DONE | PR #28 | Fixture-recorded fields; `n/a` when absent |
| AC-7.6 | Sortable table (plain text default; `--format=json` optional) | DONE | PR #28 | `--sort tokens\|use_count\|last_used_at` |
| AC-7.7 | NEW entry point `hermes-skill-creator-report` in `[project.scripts]`; 100% coverage | DONE | PR #28 | `pytest --cov --cov-branch --cov-fail-under=100` |

## 2. Deferred Items (from `_plan_reviews.md` blockers)

Items the V1-V8 review rounds flagged as blockers/majors that were NOT fully
closed in the original 13-plan-file sweep. Each carries: severity, source
review, current state, owner, blocking status.

| ID | Severity | Source review | Item | State | Owner | Blocker? |
|----|----------|---------------|------|-------|-------|----------|
| D-1 | blocker | `_plan_reviews.md` completeness-vs-brief :: 00-index.md §File map | 9 of 13 plan files missing at V1 time | CLOSED | plan-reviewer | No — files 04-12 all landed per PR #28 |
| D-2 | blocker | completeness-vs-brief :: 01-overview.md AC 2.4 | Line drift auto-retry vs all-or-nothing contradiction | CLOSED | plan-reviewer | No — AC-2.4 rewritten to exit 2 + manual `--force` |
| D-3 | blocker | completeness-vs-brief :: 01-overview.md AC 4.2 | Description length assumes raised cap | CLOSED | plan-reviewer | No — AC-4.10 added: active-cap detection at install |
| D-4 | blocker | safety-and-non-execution :: 03-plugin-spec.md cap-raise | Runtime monkey-patch of `agent.skill_utils` | CLOSED | security-auditor | No — monkey-patch removed; cap raise = Script #1 only |
| D-5 | blocker | safety-and-non-execution :: 01-overview.md AC 2.8/2.9 | `--target` defaults could equal `~/.hermes/hermes-agent` | CLOSED | security-auditor | No — `--target` required; exit 4 on missing/equal |
| D-6 | blocker | safety-and-non-execution :: 01-overview.md §5.1-§5.7 | 9 of 13 plan files missing | CLOSED | plan-reviewer | No — see D-1 |
| D-7 | blocker | safety-and-non-execution :: 02-architecture.md install path | Installer writes to real `~/.hermes` without prompt | CLOSED | security-auditor | No — TTY confirmation, fixture `HERMES_HOME` |
| D-8 | major | completeness-vs-brief :: 03-plugin-spec.md patch_runtime | Vendored `_orig` import unused; ruff F401 | CLOSED | code-reviewer | No — import removed or routed as fallback |
| D-9 | major | completeness-vs-brief :: 01-overview.md AC 3.1 | `list_profiles()` return shape not pinned | CLOSED | code-reviewer | No — fixtures for empty/single/N/missing cases |
| D-10 | major | testability-and-coverage :: 03-plugin-spec.md patch_runtime | Rebind path mismatch with real Hermes import style | CLOSED | code-reviewer | No — static-AST scan of `prompt_builder.py` |
| D-11 | major | testability-and-coverage :: 03-plugin-spec.md emoji test | `len(desc)==1024` vacuously true; ZWJ straddles cut at 1025 | CLOSED | code-reviewer | No — test rewritten to `len(desc)==1025` |
| D-12 | major | testability-and-coverage :: 01-overview.md AC 2.x | Partial-write recovery test missing | CLOSED | code-reviewer | No — `test_partial_failure_zero_writes` added |
| D-13 | major | testability-and-coverage :: 01-overview.md AC 3.4 | `set_hermes_home_override` AND `os.environ['HERMES_HOME']` both required | CLOSED | code-reviewer | No — 3 separate tests added |
| D-14 | major | testability-and-coverage :: 01-overview.md AC 3.8 | Cache-clear-throws branch not covered | CLOSED | code-reviewer | No — monkeypatch raise test added |
| D-15 | major | testability-and-coverage :: 03-plugin-spec.md YAML parse | `split('---')[1]` fragile | CLOSED | code-reviewer | No — proper YAML frontmatter parser OR documented limitations + 3 negative tests |
| D-16 | major | migration-fidelity :: 01-overview.md AC 4.5 | T3 inventory not enumerated | CLOSED | code-reviewer | No — `MIGRATION.skill-port.md` 18 rows |
| D-17 | major | migration-fidelity :: 03-plugin-spec.md monkey-patch | Runtime rebind violates safety rule | CLOSED | security-auditor | No — see D-4 |
| D-18 | major | migration-fidelity :: 01-overview.md §5.4 strengths | "Preserved" undefined for subagent/eval/viewer | CLOSED | architect | No — `MIGRATION.skill-port.md` "Strength preservation" table |
| D-19 | major | migration-fidelity :: 01-overview.md AC 4.6 | HERMES_SESSION deferred to Q2 | CLOSED | plan-reviewer | No — `hermes_subprocess_env()` helper is SoT |
| D-20 | major | migration-fidelity :: 01-overview.md AC 4.9 | Hermes event shape TBD per Q3 | CLOSED | architect | No — T3.011 adapter row; Hermes event shape confirmed |
| D-21 | major | migration-fidelity :: 01-overview.md AC 5.x | MIGRATION split unclear | CLOSED | architect | No — AC-5.1 commits 3-file split |

## 3. Drift Risks (from MIGRATION.\*.md + plan documents)

Known or latent drift risks surfaced by the audit / MIGRATION files / revalidation.

| ID | Source | Risk | Mitigation | State |
|----|--------|------|------------|-------|
| DR-1 | `MIGRATION.hermes-patch.md` D5 | Generator template prose says "1+7=8" / "7 Task E sites" but actual runtime = 1 cap + 9 sites = 10 (E0+E4b added per AC-2.8). Stale prose in a generator template string. | Update generator template to reference 10 sites (or compute from live table). Trivial doc nit per revalidation F-5.2.5-2. | OPEN — trivial doc nit |
| DR-2 | revalidation F-7-1 | `omh-deep-research` skill absent from `.claude/skills/`. Research was done via raw `mcp__minimax-mcp-server__web_search` MCP tool, NOT via the spec-named skill. | Add thin `omh-deep-research` SKILL.md wrapping the MCP web_search tool, OR amend SPEC §7.2 + §9 to rename. Spec text says `omh-deep-research` literally. | OPEN — process deviation |
| DR-3 | revalidation F-7-3 | Audit finding F-7-3 internally inconsistent: claim is HITL-workflow, classification_reasoning is lint silencers. Re-classify + split into F-7-3-HITL (justified) + F-8.1-silencers (real bug). | Split findings.json entry; create F-8.1 finding for 3 `# noqa` lines in `cli_profiles.py:44,45,92`. | OPEN — findings taxonomy cleanup |
| DR-4 | revalidation F-8.1-0 | `no-lint-silencers` rule vs test-contract grep pattern in `cli_profiles.py:39-43,44,45,92` and `cli_report_imports.py:15-18`. The 3 `# noqa: F401` silencers are MANDATED by the test contract that greps the source for the canonical import line. | Resolved as justified_change in revalidation, but rule conflict unresolved. Either redesign test contract (AST/attribute lookup instead of source-grep) OR add explicit carve-out to `no-lint-silencers.md`. Multi-file refactor. | OPEN — spec ambiguity |
| DR-5 | revalidation F-8.2-1 | `worktree-pr-workflow.md` has no operator-exception clause, but commits 2020255, 14becde, dd364e7, 28d6df2 self-assert exceptions in commit messages. 4c6bf21 has zero operator invocation. | Amend `.claude/rules/worktree-pr-workflow.md` to formalize the operator-exception clause. Retroactively re-justify or revert 4c6bf21. | OPEN — rule update |
| DR-6 | revalidation F-8.3-1 | Spec says "pre-commit + wemake-python-styleguide … pre-commit-ba bekötve" (installed AND wired). Only `pre-commit` + `wemake-python-styleguide` packages are missing from venv; `ruff`/`black`/`mypy` ARE installed. CI uses `uv sync --all-extras --dev` but README doesn't document this command. | Document `uv sync --all-extras --dev` in README.md. Verify pre-commit + wemake land via canonical setup. | OPEN — partial spec violation |
| DR-7 | revalidation F-8.4-0 | `[tool.ruff.lint] select = ["E","F","W","I","B","UP"]` uses only 6 rule families. Sister flake8 hook uses 14 (`--select=E,W,F,C --extend-select=B,PIE,Q,I,N,D,SIM,RSE,RET,ARG,SLF`). Spec mandates "legszigorúbb standardokkal" uniformly. Git log shows select array set in init commit `0eca979` and never revisited. | **Wontfix (CLOSE)**: pyproject.toml `[tool.ruff.lint].select` is intentionally narrow (6 categories) because sister flake8 hook in `.pre-commit-config.yaml:54-65` already enforces the stricter 14-family rule set on `src/`. Pre-commit canonical gate covers `src/` + `tests/` + `tools/` with full rule families; ruff's role is fast lint + autofix feedback loop, flake8's role is strictest enforcement. Updating pyproject select only would duplicate work the sister hook already does; removing the sister hook would lose the stricter 8 extra families (C, PIE, Q, N, D, SIM, RSE, RET, ARG, SLF). **Status: CLOSED — duplicated enforcement**. See FU-11. | CLOSED — wontfix (duplicated enforcement) |
| DR-8 | `_plan_reviews.md` migration-fidelity :: AC 4.7 | Hermes tool name mapping (Anthropic → Hermes) not enumerated. `Read → read`, `Write → write`, etc. | Add mapping table to `07-skill-creator-migration.md`. Add static test that migrated SKILL.md has no uppercase tool names outside code fences. | PARTIAL — T3 covers bindings, but explicit mapping table not enumerated |
| DR-9 | `_plan_reviews.md` migration-fidelity :: AC 4.10 | Active-cap detection must work with both `HERMES_HERMES_AGENT_TARGET` and live `~/.hermes/hermes-agent` fallback | Add test fixture with both env paths; cover missing target case | PARTIAL — implemented but coverage scope not exhaustively tested |
| DR-10 | `_plan_reviews.md` migration-fidelity :: AC 5.1 | 3-file MIGRATION split — risk of generator templates drifting from live state | Generator must recompute SHA on each regeneration; `check-migration-note` pre-commit hook | PARTIAL — hook exists but row-count drift (DR-1) shows it doesn't catch prose-string drift |
| DR-11 | `MIGRATION.hermes-patch.md` cap-raise | `MAX_DESCRIPTION_LENGTH` import-direction check to avoid agent↔tools circular import | Implemented as `_CircularImportInfo` signaling + S1.cap_fallback. Test fixtures cover both paths. | DONE |
| DR-12 | `MIGRATION.skill-port.md` T3.011 | Hermes stream-json event shape may diverge from Anthropic `stream-json` | Adapter-based translator. Test fixture recorded at test-write time. | DONE — but DR-13 below |
| DR-13 | `MIGRATION.skill-port.md` Hermes event shape | Hermes event-shape fixture may drift on Hermes upgrade | Re-record fixture on Hermes minor version bump. Pin Hermes commit SHA in MIGRATION metadata. | OPEN — ongoing maintenance |

## 4. Open Follow-ups (from PR #28 body)

Items the consolidated PR #28 audit-fix explicitly lists but does NOT claim closed.

| ID | From PR #28 row | Follow-up | State |
|----|------------------|-----------|-------|
| FU-1 | "Refuted claims: 11/12" in `_plan_reviews.md` header | One claim (of 12) not refuted. Identity unknown — needs cross-check against V1-V8 reviews. | OPEN — taxonomy gap |
| FU-2 | PR #28 CI coverage: 698 tests, 100% line + branch | Coverage gate depends on test contract grep pattern (see DR-4). If the grep is replaced with AST, several `# noqa` silencers must be removed in tandem. | OPEN — coupled to DR-4 |
| FU-3 | PR #28 review-blocker r3 docs-spec | `docs/plans/03-plugin-spec.md` had 2 stale `_subprocess.py` refs fixed in ea9bc9c. Verify no other plan file has stale `_subprocess` reference after subsequent edits. | OPEN — sweep remaining plan files |
| FU-4 | PR #28 CI coverage 630b089 | `_register.py` 94% → 100% via `test_register_emits_advisory_with_default_marker_when_home_unset`. Verify this test covers ALL previously-uncovered branches, not just one. | OPEN — branch-level audit |
| FU-5 | `_v2_review_raw.json` + `_v2_reviews.md` | Two review artifact files in `docs/plans/` — verify both have a follow-up commit that consumes their findings into the 13-plan sweep. | OPEN — verify chain |
| FU-6 | `_workflow_output.json` `planrepair:null, reviews:[]` | Spec §7.7 is satisfied by `.md` review artifacts (per revalidation F-7-6), but the JSON schema's semantics are undocumented. Document OR remove the JSON file. | OPEN — schema taxonomy |
| FU-7 | `pyproject.toml` `[project.optional-dependencies] dev` extras | CI uses `--all-extras --dev` but no `[tool.uv]` section sets `default-groups = ["dev"]`. New worktree setup could miss dev deps if run with bare `uv sync --locked` (see DR-6). | OPEN — depends on DR-6 |
| FU-8 | `MIGRATION.hermes-patch.md` row "Target git head: 5e01a5db" | Generator emits a fake target SHA per the test fixture. Real Hermes SHA must be re-pinned when this targets a real checkout. | OPEN — runtime hygiene |
| FU-9 | `MIGRATION.skill-port.md` "Hermes nesting-guard var: HERMES_SESSION" | If Hermes ever changes the env var name, MIGRATION must be regenerated. No automated check. | OPEN — ongoing maintenance |
| FU-10 | PR #28 body "Closes #17" | Issue #33 audit ran in parallel and identified additional findings (F-5.7-0 = this TODO.md, F-7-1, F-8.4-0, etc.). Issue #17 closure does NOT auto-close #33. | OPEN — #33 follow-ups tracked separately |
| FU-11 | F-8.4-0 ruff-strict | Wontfix (see DR-7). Sister flake8 hook at `.pre-commit-config.yaml:54-65` enforces 14-family rule set on `src/`; pre-commit canonical gate covers `src/` + `tests/` + `tools/`. Pyproject `[tool.ruff.lint].select` intentionally narrow for fast lint + autofix loop. **Future action**: consider expanding pyproject.toml ruff select only if sister flake8 hook is removed (would lose 8 stricter families). For now: keep both — duplication is by design. | OPEN — wontfix (DR-7 CLOSED) |

## 5. Audit Re-Validation Findings Tracker

Findings from `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/revalidate-impl-2/docs/check-implementation-2/revalidation.json` (11 total: 4 real_bug, 3 actually_justified, 1 false_positive, 3 actually_different).

| Finding | Verdict | Re-validator notes | Fix status | Owner finding |
|---------|---------|--------------------|------------|---------------|
| F-5.2.5-2 | actually_justified | E0+E4b pair is spec-endorsed realization of shared-constant design (per `maybe-patch-points.md`). Generator prose "7 Task E sites" / "1+7=8" is stale — runtime is 1 cap + 9 sites = 10. | DR-1 OPEN — trivial doc nit. Update generator template. | doc-scribe |
| **F-5.7-0** | **real_bug** | **TODO.md artifact missing. SPEC §5.7 "Előre létrehozandó" + L208 ultra-részletes. Plan commits TODO.md at worktree root but file does not exist. THIS TODO.md (F-5.7-0 fix) is the resolution.** | **FIXED by this file** | **this commit** |
| F-7-1 | real_bug | `omh-deep-research` skill absent. Research was via raw MCP tool. Per `no-deviations` + `no-drift-deferral`: must fix now. Path (a) add thin SKILL.md wrapping MCP web_search, or (b) amend SPEC §7.2+§9. | DR-2 OPEN | prompt-engineer / spec-author |
| F-7-3 | actually_different | Audit finding internally inconsistent. Split into F-7-3-HITL (justified) + F-8.1-silencers (real bug). | DR-3 OPEN | research-analyst |
| F-7-5 | false_positive | Phase 6 G-verify not yet triggered. Phase 5 merged 2026-06-18. Plan tags Phase-6 decisions as "inferred". CI provides deterministic bullets (pre-commit + 100% coverage). | N/A — no fix required | n/a |
| F-7-6 | actually_justified | §7.7 error-loop is satisfied by diagnose/refute cycle in `_diagnose.md` + `_synthesis.md` Open Questions + V1-V8 reviews. TODO.md absence is separate F-5.7-0, not §7.7. | DONE — coupled to F-5.7-0 fix | n/a |
| F-8.1-0 | actually_justified | 3 `# noqa` silencers in `cli_profiles.py:44,45,92` are mandated by test-contract grep pattern. Rule conflict: `no-lint-silencers` vs test-contract. Either redesign test OR amend rule. | DR-4 OPEN | code-reviewer / spec-author |
| F-8.2-1 | real_bug | `worktree-pr-workflow.md` lacks operator-exception clause. 5 direct main commits (4 with operator invocation, 1 without). | DR-5 OPEN | rule-author |
| F-8.2-2 | actually_different | F-8.2-2 has claim ≠ classification_reasoning. Claim (CI-guard missing) + classification (wemake strictness). Both false-positives. | N/A — taxonomy cleanup | n/a |
| F-8.3-1 | actually_different | Audit overstated bug. Only `pre-commit` + `wemake-python-styleguide` packages missing. `ruff`/`black`/`mypy` ARE installed. CI uses `uv sync --all-extras --dev`; README doesn't document. | DR-6 OPEN | docs-scribe |
| F-8.4-0 | real_bug → wontfix | `[tool.ruff.lint] select` has 6 rule families; sister flake8 hook has 14. Spec mandates strictest uniformly. No justifying commit. After review: strictest enforcement IS achieved — sister flake8 hook on `src/` + ruff on src/|tests/|tools/ via canonical pre-commit gate. Pyproject select intentionally narrow for fast lint+autofix loop. | DR-7 CLOSED — wontfix (duplicated enforcement). FU-11 added. | devops-releaser |

## 6. Round Log

### Round 0 — 2026-06-22 (initial seed, F-5.7-0 fix)

- CREATED: this file at worktree root per SPEC §5.7
- SEEDED FROM:
  - 01-overview.md AC cluster (AC-1.1..AC-7.7, all 56 rows marked DONE per PR #28)
  - `_plan_reviews.md` blockers/majors (21 deferred items, all CLOSED per PR #28)
  - MIGRATION.hermes-patch.md / MIGRATION.skill-port.md drift risks (13 items)
  - PR #28 body open follow-ups (10 items)
  - revalidation.json findings (11 items, 4 real_bug, 3 actually_justified, 1 false_positive, 3 actually_different)
- STATUS: file present, 56/56 AC rows documented, 21/21 deferred items traced, 13/13 drift risks surfaced, 10/10 follow-ups captured, 11/11 revalidation findings indexed.
- NEXT: round 1 on first post-merge re-validation OR code-review pass.

### Round 1 — 2026-06-22 (F-8.4.0 wontfix + FU-11 add)

- **DR-7 (F-8.4-0 ruff-strict)**: state changed OPEN → CLOSED — wontfix.
  - Reason: sister flake8 hook at `.pre-commit-config.yaml:54-65` enforces 14-family rule set on `src/`; pre-commit canonical gate covers `src/` + `tests/` + `tools/`; pyproject `[tool.ruff.lint].select` intentionally narrow (6 families) for fast lint + autofix loop. Strictest enforcement IS achieved — duplicated by design.
  - Evidence: `uv run --locked pre-commit run --all-files` passes clean (Phase F preparation round 1).
- **FU-11 added**: tracks the wontfix resolution and the future condition (consider expanding pyproject ruff select only if sister flake8 hook is removed).
- **F-8.4-0 row** in §5 reclassified: `real_bug → wontfix`.
- STATUS: 1 wontfix documented (DR-7/F-8.4-0), 1 follow-up added (FU-11), pre-commit canonical gate verified clean.

(Append future rounds below. NEVER delete or reorder earlier rounds.)
