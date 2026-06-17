<!-- title: Risks + open questions + escalation log -->
<!-- scope: Sec 12. Every unresolved question with proposed default + escalation path. -->
<!-- ACs covered: (no AC; meta plan) -->

# 12 — Risks + Open Questions

## Open questions (Q1–Q9, each with a proposed default + escalation)

### Q1 — Hermes nesting-guard env var name

- **Question**: what is the canonical name of the env var Hermes's CLI checks to refuse nesting?
- **Proposed default**: `HERMES_SESSION` (single source of truth in `src/hermes_skill_creator_plugin/_subprocess.py:NESTING_GUARD_VAR`).
- **Alternatives**: `HERMES_AGENT`, `HERMES_PARENT`.
- **Resolution path**: read `~/.hermes/hermes-agent/hermes_cli/` (or equivalent) to confirm. If the var is undocumented, the default stands and the test asserts the helper un-nests a documented stub.
- **Escalation**: if HITL disagrees with the default, rename the constant + re-run the TDD list in 07 §Nesting-guard helper.

### Q2 — Hermes stream-json event shape

- **Question**: what is the NDJSON event shape emitted by `hermes -p --output-format stream-json`?
- **Proposed default**: `{event: "message", role: "assistant", content: "..."}` (single canonical shape, with the adapter in `07` translating to the Anthropic-shaped dict the rest of the pipeline consumes).
- **Resolution path**: read `~/.hermes/hermes-agent/hermes_cli/streaming/` (or equivalent) to confirm. The adapter is the only place that needs to know.
- **Escalation**: if the shape is materially different, the adapter is the only code that changes; the rest of the pipeline is unchanged.

### Q3 — Per-profile directory set (audit)

- **Question**: which directories does the per-profile audit walk?
- **Proposed default**: `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` per `hermes_cli/profiles.py:39-53`. `gateway.pid` is read as a flat file in the profile root (NOT a subdir).
- **Resolution path**: re-read `hermes_cli/profiles.py:39-53` at Phase 5 / D-script-2 implementation time. If `_PROFILE_DIRS` has changed, update 06.
- **Escalation**: if `gateway/` is now a subdir, add it; if `gateway.pid` is gone, remove the read.

### Q4 — Cap-raise safety contract

- **Question**: is the cap-raise safety contract (--target REQUIRED, refuses `~/.hermes/hermes-agent`, plugin is advisory-only) approved?
- **Proposed default**: yes (matches the project safety rule + the Diagnose refuted-claim fix).
- **Resolution path**: HITL gate in Phase 4.
- **Escalation**: if HITL wants the runtime monkey-patch back, the plan is rejected and re-drafted.

### Q5 — Migration-note 3-file split

- **Question**: is the migration note split into MIGRATION.md / MIGRATION.hermes-patch.md / MIGRATION.skill-port.md approved?
- **Proposed default**: yes (matches the Diagnose refuted-claim fix).
- **Resolution path**: HITL gate in Phase 4.
- **Escalation**: if HITL wants a single MIGRATION.md, 08 is re-drafted to one file.

### Q6 — Per-file line budget table

- **Question**: is the per-file line budget (00 90, 01 150, 02 200, 03 220, 04 400, 05 250, 06 400, 07 450, 08 180, 09 300, 10 250, 11 200, 12 200; sum 3490 < 4500) approved?
- **Proposed default**: yes.
- **Resolution path**: HITL gate. Pre-commit hook `check_line_count.py` enforces it.
- **Escalation**: if any file blows the budget, the plan is rejected and that file is split or trimmed.

### Q7 — Bilingual format spec

- **Question**: is the bilingual format (`[en] text / [hu] szöveg` on a single line for console; two top-level sections for `--help`) approved?
- **Proposed default**: yes.
- **Resolution path**: HITL gate. Pre-commit hook `check_bilingual.py` enforces the console format; `test_help_is_bilingual` enforces the two-section structure.
- **Escalation**: if HITL wants a different format, the hooks are updated and the TDD test list is re-run.

### Q8 — Plugin installer interactive safety

- **Question**: is the installer interactive-by-default (TTY confirmation, refuses real `~/.hermes` without `--yes`) approved?
- **Proposed default**: yes.
- **Resolution path**: HITL gate.
- **Escalation**: if HITL wants non-interactive default, the TTY prompt is replaced with a `--yes`-only gate; integration tests use `--yes`.

### Q9 — Active-cap detection at install time

- **Question**: the installer MUST detect the active cap (60 vs 1024) and refuse to install the migrated skill with a bilingual error if the description exceeds the active cap. The skill ships with `description` <= 60 chars by default; `--with-extended-description` substitutes the longer one. Is this approved?
- **Proposed default**: yes.
- **Resolution path**: HITL gate. Tests in 03 cover both cap states.
- **Escalation**: if HITL wants unconditional install (no detection), the bilingual error is replaced with a warning; tests are updated.

## Residual risks (R1–R6)

### R1 — Hermes event shape could change

- The adapter in 07 is the only code that needs to know the Hermes event shape. If Hermes changes the shape, the adapter is updated and the rest of the pipeline is untouched. Risk: low; impact: contained.

### R2 — Cap-raise may not survive a Hermes upgrade

- If the operator upgrades Hermes from v0.16.0 to v0.17.0, the patch in 04 may drift. Script #1's `--check` will detect this and emit `TEXT_DRIFT` / `LINE_DRIFT`. The operator re-applies the patch against the new source. Risk: low; impact: known; mitigation: documented in 04.

### R3 — Anthropic upstream may push breaking changes

- The pinned upstream commit (2a40fd2e7c52207aa903bd33fc4c65716126966e) is the source of truth. If the upstream moves, the T3 inventory in 07 may need updates. The migration note is regenerated; tests are updated. Risk: low; impact: known.

### R4 — Hermes subagent dispatch may not be 1:1 with Anthropic

- The "subagent split" Claude strength is preserved via `agent_name` registration in Hermes. If the dispatch is materially different, the three subagents (grader, analyzer, comparator) may need different wiring. Risk: medium; impact: medium; mitigation: the strength-preservation matrix in 07 has explicit ACs (`test_subagent_dispatch_via_delegate_task`).

### R5 — Vendor-bundled skill may shadow user-local

- If a user has their own `~/.hermes/skills/<cat>/skill-creator/`, the installer's "no overwrite" rule applies (see 03). But the plugin's `register_skill` reads from the BUNDLED copy. If the user's copy has a different description, the agent sees the bundled one in the system prompt. Risk: low; impact: medium; mitigation: documented; precedence rule: bundled in `register_skill`, user-local at `~/.hermes/skills/` for `skill_view`.

### R6 — Hermes `clear_skills_system_prompt_cache` may not exist

- 06's apply sequence calls `clear_skills_system_prompt_cache(clear_snapshot=True)`. If this function does not exist in v0.16.0, 06 falls back to deleting `~/.hermes/.skills_prompt_snapshot.json` directly. Risk: low; impact: contained.

## Escalation log (populated at Phase 4 HITL — 2026-06-17)

| # | Date | Question | Default | HITL decision | Action taken |
| --- | --- | --- | --- | --- | --- |
| E1 | 2026-06-17 | (Q1) nesting-guard var name | HERMES_SESSION | **HERMES_SESSION** (confirmed) | `src/hermes_skill_creator_plugin/_subprocess.py:NESTING_GUARD_VAR` set; tests assert un-nest behaviour. |
| E2 | 2026-06-17 | (Q2) Hermes event shape | adapter-based, single canonical | default accepted | Adapter in `07 §Nesting-guard helper`; re-verify shape at Phase 5 by reading `~/.hermes/hermes-agent/hermes_cli/streaming/`. |
| E3 | 2026-06-17 | (Q3) per-profile dir set | `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` per `hermes_cli/profiles.py:39-53` | default accepted | Script #2 re-reads `hermes_cli/profiles.py:39-53` at Phase 5 implementation; if the list changed, 06 is updated. |
| E4 | 2026-06-17 | (Q4) cap-raise safety contract | --target REQUIRED, no runtime monkey-patch | **accepted** (--target REQUIRED + advisory-only) | Runtime monkey-patch removed from the plan; plugin is purely advisory (static AST read of user-owned checkout); Script #1 refuses to run if `--target == ~/.hermes/hermes-agent`. |
| E5 | 2026-06-17 | (Q5) MIGRATION split | 3 files | **3 files** (confirmed) | `MIGRATION.md` (index) + `MIGRATION.hermes-patch.md` (Script #1's cap-raise + 7 Task E sites) + `MIGRATION.skill-port.md` (T3 inventory of 15 Claude-binding replacements). All three source-controlled. |
| E6 | 2026-06-17 | (Q6) line budget | 3490 sum | default accepted | pre-commit hook `tools/check_line_count.py` enforces per-file budget; sum < 4500. |
| E7 | 2026-06-17 | (Q7) bilingual format | `[en] text / [hu] szöveg` single line + two-section `--help` | default accepted | pre-commit `tools/check_bilingual.py` enforces console format; `test_help_is_bilingual` enforces the two-section structure. |
| E8 | 2026-06-17 | (Q8) installer interactive safety | TTY confirm + `--yes` bypass | default accepted | Installer prompts in TTY, refuses real `~/.hermes` without `--yes`; integration tests use `tmp_path HERMES_HOME` + `--yes`. |
| E9 | 2026-06-17 | (Q9) active-cap detection | refuse if desc > active cap | **refuse + bilingual error** (confirmed) | Installer detects active cap (60 vs 1024) by static AST read of target; refuses install with bilingual error if description exceeds the cap; `--with-short-description` flag substitutes the truncated form. Tests cover both cap states. |

## Out of scope (explicit)

- The 60-char cosmetic preview sites in `tools/skills_tool.py:1509`, `hermes_cli/skills_hub.py:305`, `hermes_cli/mcp_config.py:447`, `hermes_cli/mcp_catalog.py:627`, `tools/browser_tool.py:3795` are NOT patched. They are operator-TUI previews, not on the agent-injection path. Patching them is OUT OF SCOPE.
- `system_prompt.py` is NOT a patch site. It is a consumer of `MEMORY_GUIDANCE` / `SKILLS_GUIDANCE` from `prompt_builder`. Patching `prompt_builder` is sufficient.
- Cowork-specific sections in the Anthropic SKILL.md are removed (per T3.008 / T3.009 / T3.010). Hermes has no Cowork surface. Adding one is OUT OF SCOPE.
- The 60-char code-point slicing (vs grapheme slicing) in `extract_skill_description` is a known limitation. If i18n skill descriptions include ZWJ-emoji, the slice may split a grapheme. This is documented in 04 (the patch inherits the same behaviour, with the same limitation). Fixing it (grapheme-safe slicing) is OUT OF SCOPE for this plan; follow-up work.

<!-- end of file: 120 lines (budget 200) -->
