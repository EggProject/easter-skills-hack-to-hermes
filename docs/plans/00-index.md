<!-- title: Index — navigation + file map + per-file budget + status legend + hard constraints -->
<!-- scope: Read FIRST. Updated LAST after every other plan file lands. -->
<!-- ACs covered: AC-6.1 (line budget) -->

# Index — Hermes Skill-Creator Migration + Task E Patch Plan

> Worktree: see `git worktree list` (the path is environment-dependent; this index is read from the worktree root)
> Hermes install (READ-ONLY): `~/.hermes/hermes-agent` (upstream main HEAD 36ae958473b8530ffb1a395c4944b8cdbcae82fe)
> Vendored upstream skill-creator: `research/anthropic-skill-creator-original/` (pinned 2a40fd2e7c52207aa903bd33fc4c65716126966e)
> Spec for Task E redirect: `docs/maybe-patch-points.md`

## How to read this plan

1. Start with `01-overview.md` for mission, deliverables, and acceptance criteria.
2. `02-architecture.md` for component diagram and data flow.
3. Per-deliverable files: `03` (plugin), `04` (Script #1), `05` (Task E toggle), `06` (Script #2), `07` (migrated skill), `08` (migration note), `13` (Script #3 report).
4. Cross-cutting: `09` (test strategy), `10` (toolchain), `11` (sub-agent delegation), `12` (risks + open questions).

## File map + per-file line budget

| # | File | Covers | Status | Budget | Actual |
| --- | --- | --- | --- | --- | --- |
| 00 | `00-index.md` | This file | [emitted] | 130 | 112 |
| 01 | `01-overview.md` | Mission, deliverables, ACs (1.x–6.x) | [emitted] | 150 | 142 |
| 02 | `02-architecture.md` | Component diagram, data flow, sequence, safety | [emitted] | 250 | 241 |
| 03 | `03-plugin-spec.md` | §5.1 plugin (no runtime monkey-patch; static-AST advisory; manifest parser test) | [emitted] | 280 | 267 |
| 04 | `04-script-1-patch.md` | §5.2 Script #1 (cap raise S1.cap line 688 in agent/skill_utils.py; --target REQUIRED; --force) | [emitted] | 400 | 249 |
| 06 | `06-script-2-profiles.md` | §5.3 Script #2 (per-profile audit/flip; hermes_home_scope w/ real API) | [emitted] | 300 | 283 |
| 07 | `07-skill-creator-migration.md` | §5.4 Migrated skill (T3 18 rows; tool-name mapping full; HERMES_SESSION+CLAUDECODE strip) | [emitted] | 450 | 263 |
| 08 | `08-migration-note-format.md` | §5.5 MIGRATION (3-file split) | [emitted] | 220 | 213 |
| 09 | `09-test-strategy.md` | TDD, fixtures, AST-grep, no-touch sentinels, seed-minimal-fixture contract | [emitted] | 400 | 393 |
| 10 | `10-toolchain-and-conventions.md` | uv, pyproject, pre-commit, bilingual, worktree+PR | [emitted] | 340 | 335 |
| 11 | `11-sub-agent-delegation-map.md` | Phase 5 sub-agent routing | [emitted] | 200 | 157 |
| 12 | `12-risks-and-open-questions.md` | Q1–Q9, residual risks R1–R6, escalation log | [emitted] | 210 | 204 |
| 13 | `13-script-3-report.md` | Script #3 (extra-brief feature WE requested: profile-level skill token + usage reporter; READ-ONLY) — NOTE: §5.7 in the original brief is the continuously-maintained Todo list, NOT this deliverable | [emitted] | 400 | 307 |
| | **Total** | | | 3100 | **3166** |

Sum 3166 < 4500 (sum of budgets 3730; per-file budgets raised as needed for the PR-A register-spec expansion). Every file < 500 lines. Enforced by pre-commit hook `tools/check_line_count.py`.

## Hard constraints (HARD)

- **Safety**: NEVER modify `~/.hermes/hermes-agent`. NEITHER file write NOR in-process module mutation. The cap-raise is performed by Script #1 against a user-owned Hermes checkout (NEVER `~/.hermes/hermes-agent`). The plugin is purely advisory (static AST read).
- **Toolchain**: `uv venv` + `pyproject.toml` + `pre-commit` (`ruff` + `black` + `mypy` + `wemake-python-styleguide` at strictest).
- **Bilingual**: code/skills/prompts in English; user-facing console/log messages bilingual EN+HU on a single line (`[en] ... / [hu] ...`); `--help` uses two top-level sections with mirrored content. Enforced by pre-commit `tools/check_bilingual.py`.
- **TDD**: every code file lists its TDD test cases up front; 100% code + branch coverage mandatory (`pytest --cov --cov-branch --cov-fail-under=100`).
- **Worktree+PR**: every Phase 5 task runs in its own worktree; PR after every AC cluster (1.x, 2.x, ..., 6.x).
- **File size**: every plan file <= 500 lines; every source file <= 500 lines; sum of all plan files <= 4500.
- **Standalone skill (B4)**: the migrated skill-creator is a TOP-LEVEL artifact (`skills/skill-creator/` at worktree root), NOT bundled inside the plugin package. It is installed flat into `~/.hermes/skills/skill-creator/` so it appears as `skill-creator` in the `<available_skills>` index. The plugin is advisory-only and never owns the skill files.
- **Script #3 (READ-ONLY)**: Script #3 lists ENABLED skills per profile, computes per-skill token cost and usage stats, and emits a sortable report. It MUST NOT modify any state. Test asserts zero bytes written against the fixture tree.

## Bilingual legend (used in console/log messages across all scripts)

- Console/log: `print("[en] hello / [hu] szia")` — single line, both languages.
- `--help`: two top-level sections `Usage (English)` and `Használat (magyar)` with mirrored content.
- Migration note: English only (technical artifact); the announcement message is bilingual.

## MIGRATION note (3 files, worktree root)

- `MIGRATION.md` — top-level index.
- `MIGRATION.hermes-patch.md` — Script #1's cap-raise + 7 Task E sites.
- `MIGRATION.skill-port.md` — migrated skill's T3 inventory (18 rows).

All three are source-controlled where applicable. Script #1's `--emit-migration-note` regenerates `MIGRATION.hermes-patch.md`. The migrated skill's installer regenerates `MIGRATION.skill-port.md`. Script #3 is STDOUT + `--json PATH` ONLY — it does NOT write to the worktree (READ-ONLY report emitted on demand; not bundled with the install artifacts).

## Open questions (escalation at Phase 4 HITL — see 12)

- Q1: Hermes nesting-guard var name (default: `HERMES_SESSION`).
- Q2: Hermes stream-json event shape (default: adapter-based).
- Q3: per-profile directory set (default: `_PROFILE_DIRS`).
- Q4: cap-raise safety contract (default: --target REQUIRED; no runtime monkey-patch).
- Q5: MIGRATION 3-file split (default: 3 files).
- Q6: per-file line budget (default: 3960 sum; see the file map + budget table above for live values).
- Q7: bilingual format spec (default: `[en]/[hu]` single line + two-section help).
- Q8: plugin installer interactive safety (default: TTY confirm + --yes).
- Q9: active-cap detection at install (default: refuse if desc > active cap).
- Q10: Script #3 tokenizer selection — real model tokenizer via configured model vs. fallback `~chars/4` heuristic (default: real tokenizer when available, heuristic fallback otherwise; both paths tested).
- Q11: Script #3 usage-data sourcing — Curator project ref #45 field names + storage location; verify before wiring, show `n/a` where data absent (default: read-only probe + `n/a` fallback, no synthetic data).

## Decisions & evidence

### D1. Budget table is the single source of truth for plan-file budgets (REC-3)
- **Decision**: 01-overview.md, 12-risks-and-open-questions.md, and the plan-file footers MUST NOT restate per-file counts or totals; they reference this budget table. Standalone prose like "Sum 2829" or "(default: 3490 sum)" is removed in favor of the live table.
- **Rationale**: hard numbers in plan prose drifted across rounds (RR2, RR3, RR4). Centralizing the live values here removes the parallel-truth class of drift.
- **Evidence**: V6 RR2 / RR3 / RR4 findings; the table cells above are computed from `wc -l` and updated after every plan edit. Confidence: inferred (process rule); verified-from-source (live `wc -l`).

### D2. Actual column + Total cell are hand-typed from `wc -l` at file-finalization time (REC-2)
- **Decision**: the `Actual` column is hand-typed from `wc -l` at file-finalization time; the Total cell MUST equal the sum of the Actual column OVER ALL ROWS (00..13, i.e. all 14 plan files — the 00-index row's own Actual count IS included in the Total). The extended `tools/check_line_count.py` hook (see 10 §Extended check_line_count.py spec) asserts at pre-commit time: (a) each file's `<!-- end of file: NN lines -->` footer equals live `wc -l`, AND (b) the 00-index Total cell equals the live sum of the Actual column, AND (c) for every file-map row, the per-file `Actual` cell equals live `wc -l` of that row's path AND the per-file `Budget` cell equals the budget value handed to the hook (per-cell guard; supersedes the aggregate-only check; see D6 for the full rationale).
- **Rationale**: hand-maintained Actual counts drifted in R2 (00=80 vs real 79; 09=345 vs real 347) AND V4 (Total 3206 vs real 3312 = 3206 + file 00's 106 — the old Total omitted row 00 from its own sum). Centralizing the cell values here in this table is the contract; the pre-commit hook then enforces it. Dropping the "auto-generated" claim because the cells are hand-typed and we have already shipped one wrong Total — honesty about the process prevents future drift-class bugs.
- **Reconciliation with D6 (Phase 5 / F-meta)**: in the post-V11 round, F-meta landed `tools/check_line_count.py` with the FOUR invariants specified here (per-file cap, footer drift, budget-table Total, per-cell guard). The hook is the live implementation of the contract described in this D2 — the cells in this table are the source of truth the hook enforces; the hook is the enforcer. Both D2 and D6 agree on the spec; D2 names the contract, D6 names the systemic rationale.
- **Evidence**: V6 RR2 / V4 RR2 verified against the live checkout; live `wc -l` post-F-meta (2026-06-17, updated 2026-06-22 for PR-A register-spec drift): 113,142,242,269,249,183,283,263,213,393,335,157,204,307 = 3352; Total cell = 3352; per-file Budget cells unchanged. Confidence: verified-from-source.

### D3. Hard caps: 500 lines per file, 4500 lines sum
- **Decision**: per-file cap = 500; sum cap = 4500; budgets per file = 90–450.
- **Rationale**: round-1 briefs and V3 review cite 500/4500 as the spec-of-truth ceilings; sub-budgets are the operator hint.
- **Evidence**: V3 [blocker] hard caps; reiterated in 06 / 09 / 10 footer rules. Confidence: verified-from-source (HITL gate + V3 review).

### D4. Footers `<!-- end of file -->` vs `<!-- end of file: NN lines (budget BB) -->`
- **Decision**: 00-index.md uses the bare `<!-- end of file -->` marker; all other files use `<!-- end of file: NN lines (budget BB) -->` so `tools/check_line_count.py --enforce-footer` can assert `NN == wc -l`.
- **Rationale**: this file is the budget source of truth — its own footer cannot reference itself (chicken-and-egg). The other 13 files carry live-NN footers that the pre-commit hook validates.
- **Evidence**: V6 RR5 footer-drift class + REC-2 spec. Confidence: inferred.

### D5. 13 plan files, 14 deliverables (13 + README)
- **Decision**: plan set = 00..13 (14 files); file map covers all of them.
- **Rationale**: round-2/3 review added `13-script-3-report.md` for the WE-requested Script #3 report (extra-brief feature, NOT the original §5.7 — §5.7 in the brief is the continuously-maintained Todo list, which is a separate artifact tracked outside this plan set). 00-index grew an Actual/Total row for Script #3.
- **Evidence**: V3 review added Script #3 deliverable; V4 RR4 S6 clarified §5.7 vs Script #3 ownership. Confidence: verified-from-source (V3 review + AC-7.1..AC-7.7 in 01).

### D6. Per-cell arithmetic guard closes the V1 drift class (REC-2 systemic)
- **Decision**: `tools/check_line_count.py` asserts at pre-commit time, FOR EVERY ROW of the file map, that (a) the per-file `Actual` cell equals live `wc -l` for the cited path, AND (b) the per-file `Budget` cell equals the live budget value as it appears in this table (i.e. the per-file budgets the operator hands to the hook come FROM this table — the table is the budget spec, not a derived view). Additionally the 00-index Total cell MUST equal the sum of the Actual column. The pre-commit hook fails on any per-cell mismatch, not just the aggregate. Documented in 09 §Test strategy (per-cell guard spec) and 10 §Extended check_line_count.py spec.
- **Implementation (Phase 5 / F-meta, 2026-06-17)**: `tools/check_line_count.py` exposes `check_per_cell_guard(root: Path) -> list[str]` and `check_budget_table_total(root: Path) -> list[str]`. The hook is wired into `.pre-commit-config.yaml` via the `check-line-count` local hook with flags `--enforce-footer --enforce-budget-table --enforce-per-cell` (all on by default). TDD test list lives at the top of `tools/check_line_count.py` and is mirrored in `tests/meta/test_meta_check_line_count.py`. The four invariants — (1) per-file cap (<=500), (2) footer drift (NN == wc -l), (3) 00-index Total == live sum, (4) per-cell Actual==wc -l AND Budget>=Actual — close the V1 drift class mechanically: a stale cell fails before the aggregate Total==sum is ever computed.
- **Rationale**: the V1 class reopened in V7 RR2 because the old hook only checked `Total == sum(Actual)` and missed the per-cell drift (07 Actual left at 256 after 07 grew to 259; Total read 3320 from a hand-typed value; sum-of-column equalled 3317 — but a hand-typed Total can mask a per-cell mistake). Per-cell assertions make the class un-reopenable: a stale cell fails before the aggregate ever gets computed. The systemic version also asserts the Budget cell against the budget column, which protects the analogous (currently theoretical) class.
- **Evidence**: V1 finding (this round) + V6 RR2 / V4 RR2. Confidence: inferred (process rule); verified-from-source (live `wc -l` for all 14 files post-fix, updated 2026-06-22 for PR-A register-spec drift: 113,142,241,269,249,183,283,263,213,393,335,157,204,307 = 3352; Total cell = 3352; per-file Budget cells unchanged from V7).

<!-- end of file -->