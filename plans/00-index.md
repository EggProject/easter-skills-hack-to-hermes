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
| 00 | `00-index.md` | This file | [emitted] | 90 | 80 |
| 01 | `01-overview.md` | Mission, deliverables, ACs (1.x–6.x) | [emitted] | 150 | 123 |
| 02 | `02-architecture.md` | Component diagram, data flow, sequence, safety | [emitted] | 200 | 184 |
| 03 | `03-plugin-spec.md` | §5.1 plugin (no runtime monkey-patch; static-AST advisory; manifest parser test) | [emitted] | 250 | 226 |
| 04 | `04-script-1-patch.md` | §5.2 Script #1 (cap raise S1.cap line 653; --target REQUIRED; --force) | [emitted] | 400 | 202 |
| 05 | `05-script-1-task-e-toggle.md` | §6.E Task E toggle (7 sites) | [emitted] | 250 | 140 |
| 06 | `06-script-2-profiles.md` | §5.3 Script #2 (per-profile audit/flip; hermes_home_scope w/ real API) | [emitted] | 400 | 238 |
| 07 | `07-skill-creator-migration.md` | §5.4 Migrated skill (T3 18 rows; tool-name mapping full; HERMES_SESSION+CLAUDECODE strip) | [emitted] | 450 | 219 |
| 08 | `08-migration-note-format.md` | §5.5 MIGRATION (3-file split) | [emitted] | 180 | 219 |
| 09 | `09-test-strategy.md` | TDD, fixtures, AST-grep, no-touch sentinels, seed-minimal-fixture contract | [emitted] | 300 | 345 |
| 10 | `10-toolchain-and-conventions.md` | uv, pyproject, pre-commit, bilingual, worktree+PR | [emitted] | 250 | 296 |
| 11 | `11-sub-agent-delegation-map.md` | Phase 5 sub-agent routing | [emitted] | 200 | 130 |
| 12 | `12-risks-and-open-questions.md` | Q1–Q9, residual risks R1–R6, escalation log | [emitted] | 200 | 176 |
| 13 | `13-script-3-report.md` | §5.7 Script #3 (profile-level skill token + usage reporter; READ-ONLY) | [emitted] | 250 | 236 |
| | **Total** | | | **3570** | **2814** |

Sum 2814 < 4500 (sum of budgets 3570). Every file < 500 lines. Enforced by pre-commit hook `tools/check_line_count.py`.

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
- `MIGRATION.report.md` — generated by Script #3: per-profile ENABLED-skill inventory with token + usage stats (READ-ONLY report, refreshed on demand, not bundled with the install artifacts).

All four are source-controlled where applicable. Script #1's `--emit-migration-note` regenerates `MIGRATION.hermes-patch.md`. The migrated skill's installer regenerates `MIGRATION.skill-port.md`. Script #3's `--write-report` regenerates `MIGRATION.report.md`.

## Open questions (escalation at Phase 4 HITL — see 12)

- Q1: Hermes nesting-guard var name (default: `HERMES_SESSION`).
- Q2: Hermes stream-json event shape (default: adapter-based).
- Q3: per-profile directory set (default: `_PROFILE_DIRS`).
- Q4: cap-raise safety contract (default: --target REQUIRED; no runtime monkey-patch).
- Q5: MIGRATION 3-file split (default: 3 files; now extended to 4 to include `MIGRATION.report.md` from Script #3).
- Q6: per-file line budget (default: 3490 sum).
- Q7: bilingual format spec (default: `[en]/[hu]` single line + two-section help).
- Q8: plugin installer interactive safety (default: TTY confirm + --yes).
- Q9: active-cap detection at install (default: refuse if desc > active cap).
- Q10: Script #3 tokenizer selection — real model tokenizer via configured model vs. fallback `~chars/4` heuristic (default: real tokenizer when available, heuristic fallback otherwise; both paths tested).
- Q11: Script #3 usage-data sourcing — Curator project ref #45 field names + storage location; verify before wiring, show `n/a` where data absent (default: read-only probe + `n/a` fallback, no synthetic data).

<!-- end of file -->