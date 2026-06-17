# Hermes Skills Plan Index

## Plan files (chunked, each ≤500 lines)

- [`00-index.md`](00-index.md) — 00 — Index and How to Read This Plan
- [`01-overview.md`](01-overview.md) — 01 — Overview, Deliverables, Acceptance Criteria
- [`02-architecture.md`](02-architecture.md) — 02 — Architecture, Component Diagram, Data Flow
- [`03-plugin-spec.md`](03-plugin-spec.md) — 03 — Hermes Plugin Spec (§5.1, 60→1024 Cap Raise)
- [`04-script-1-patch.md`](04-script-1-patch.md) — 04 — Script #1 (cap-raise patch; --target REQUIRED)
- [`05-script-1-task-e-toggle.md`](05-script-1-task-e-toggle.md) — 05 — Task E toggle (7 sites, byte-accurate anchors)
- [`06-script-2-profiles.md`](06-script-2-profiles.md) — 06 — Script #2 (per-profile audit/flip; hermes_home_scope)
- [`07-skill-creator-migration.md`](07-skill-creator-migration.md) — 07 — Migrated skill (T3 18 rows; tool-name mapping; HERMES_SESSION+CLAUDECODE strip)
- [`08-migration-note-format.md`](08-migration-note-format.md) — 08 — MIGRATION (3-file split)
- [`09-test-strategy.md`](09-test-strategy.md) — 09 — TDD, fixtures, AST-grep, no-touch sentinels
- [`10-toolchain-and-conventions.md`](10-toolchain-and-conventions.md) — 10 — uv, pyproject, pre-commit, bilingual, worktree+PR
- [`11-sub-agent-delegation-map.md`](11-sub-agent-delegation-map.md) — 11 — Phase 5 sub-agent routing
- [`12-risks-and-open-questions.md`](12-risks-and-open-questions.md) — 12 — Q1–Q11, residual risks R1–R7, escalation log
- [`13-script-3-report.md`](13-script-3-report.md) — 13 — Script #3 (extra-brief feature WE requested: profile-level skill token + usage reporter; READ-ONLY)

All 14 plan files (00–13) are emitted. Every file is under 500 lines; see `00-index.md` for the live per-file counts, sum, and budget table (budget sum 3960, hard cap 4500). V8 plan-repair fixes (T1–T6, building on V3–V7) are applied. See `docs/review/` for the full round-by-round fix log.

## Supporting artefacts

- [`_synthesis.md`](_synthesis.md) — Synthesized research brief
- [`_plan_reviews.md`](_plan_reviews.md) — Adversarial plan reviews (4 lenses)
- [`_research/`](_research/) — Raw research JSON per topic
- [`docs/review/`](docs/review/) — V2–V8 plan-repair logs + TASK_E_PROMPT_EDITS anchors

## Open questions for the HITL gate

- Q1: Hermes nesting-guard env var name → `HERMES_SESSION` (HITL-confirmed E1).
- Q4: cap-raise safety contract → `--target REQUIRED` + plugin advisory-only (HITL-confirmed E4; the §5.1 re-scope to "advisory-only + Script #1 does the patch" is surfaced at E4a as a literal deviation from the brief).
- Q5: MIGRATION 3-file split → confirmed (E5).
- Q9: active-cap detection at install → refuse + bilingual error (confirmed E9).
- Q2 / Q3 / Q6 / Q7 / Q8 / Q10 / Q11: defaults accepted; pending Phase 5 re-verify.
