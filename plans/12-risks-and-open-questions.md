<!-- title: Risks + open questions + escalation log -->
<!-- scope: Sec 12. Every unresolved question with proposed default + escalation path. -->
<!-- ACs covered: (no AC; meta plan) -->

# 12 — Risks + Open Questions

## Open questions (Q1–Q11, each with a proposed default + escalation)

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
- **Proposed default**: `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` per `hermes_cli/profiles.py:_PROFILE_DIRS`. `gateway.pid` is read as a flat file in the profile root (NOT a subdir).
- **Resolution path**: re-read `hermes_cli/profiles.py` (anchor: `_PROFILE_DIRS` symbol) at Phase 5 / D-script-2 implementation time. If `_PROFILE_DIRS` has changed, update 06.
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

### Q10 — Script #3 enabled-detection module: share with Script #2 or duplicate?

- **Question**: Script #3 (Profile-level skill token + usage reporter) needs the same enabled-detection logic as Script #2 (toggle, profile + platform; honor `platforms:` / conditional exclusions). Should Script #3 import a shared helper from Script #2, or duplicate the logic?
- **Proposed default**: SHARE — extract the enabled-detection into a shared helper (e.g. `hermes_skill_creator_plugin/_enabled_detection.py`) consumed by both Script #2 (`do_audit`) and Script #3 (`do_report`). Single source of truth; consistent behaviour when `platforms:` is added/removed.
- **Alternatives**: duplicate (faster to ship, but two copies drift over time).
- **Resolution path**: Phase 5 D-script-2 + G-report; one PR introduces the shared helper, both scripts depend on it.
- **Escalation**: if sharing introduces a circular import, fall back to duplicate with a comment cross-referencing the two sites; add a regression test that asserts both produce the same enabled set for a given fixture.

### Q11 — Script #3 usage data source: Curator only, or also Hermes-level log?

- **Question**: Script #3's usage columns (view/use/patch counts + last_used) are sourced from the Curator (project ref #45). If the Curator store is missing or its schema differs, should Script #3 also fall back to a Hermes-level log, or just show `n/a`?
- **Proposed default**: CURATOR ONLY — show `n/a` for any column whose backing data is missing or whose schema does not match the expected field names. Graceful degradation; no hidden second source of truth.
- **Alternatives**: Hermes-level log fallback (more code, more chance of disagreement with the Curator).
- **Resolution path**: Phase 5 G-report verification. Script #3 MUST verify the actual storage location + field names of the Curator store FIRST (read code, not docs), then code against the verified schema. If the schema is unexpected, the implementation updates the field-name map and documents the deviation in MIGRATION.skill-port.md.
- **Escalation**: if the Curator is unavailable in the user's Hermes install, MIGRATION.skill-port.md documents the manual work-around (e.g. `--no-usage` flag); the columns still render, just blank.

## Residual risks (R1–R7)

### R1 — Hermes event shape could change

- The adapter in 07 is the only code that needs to know the Hermes event shape. If Hermes changes the shape, the adapter is updated and the rest of the pipeline is untouched. Risk: low; impact: contained.

### R2 — Cap-raise may not survive a Hermes upgrade

- If the operator upgrades Hermes from v0.16.0 to v0.17.0, the patch in 04 may drift. Script #1's `--check` will detect this and emit `TEXT_DRIFT` / `LINE_DRIFT`. The operator re-applies the patch against the new source. Risk: low; impact: known; mitigation: documented in 04.

### R3 — Anthropic upstream may push breaking changes

- The pinned upstream commit (2a40fd2e7c52207aa903bd33fc4c65716126966e) is the source of truth. If the upstream moves, the T3 inventory in 07 may need updates. The migration note is regenerated; tests are updated. Risk: low; impact: known. **NOTE (V3 / M5):** GitHub issue references (#46005, #46024) and the upstream Anthropic commit `2a40fd2e...` MUST be re-verified on GitHub at Phase 5 implementation time. Do not present unverified claims as confirmed in the MIGRATION note. The pin is provisional until re-verified.

### R4 — Hermes subagent dispatch may not be 1:1 with Anthropic

- The "subagent split" Claude strength is preserved via `agent_name` registration in Hermes. If the dispatch is materially different, the three subagents (grader, analyzer, comparator) may need different wiring. Risk: medium; impact: medium; mitigation: the strength-preservation matrix in 07 has explicit ACs (`test_subagent_dispatch_via_delegate_task`).

### R5 — Vendor-bundled skill may shadow user-local

- If a user has their own `~/.hermes/skills/<cat>/skill-creator/`, the installer's "no overwrite" rule applies (see 03). The migrated skill is installed as a FLAT skill into `~/.hermes/skills/skill-creator/` (B4 — see R7 notes). If the user's copy has a different description, the agent sees the user-local one in the system prompt. Precedence rule: user-local `~/.hermes/skills/` wins for `skill_view`; the plugin's advisory hook (if any) MUST NOT bundle the skill. Risk: low; impact: medium.

### R6 — `clear_skills_system_prompt_cache` existence

- **RESOLVED (V3).** `agent.prompt_builder.clear_skills_system_prompt_cache` EXISTS at the `build_skills_system_prompt` module (verified line ~1022 of upstream main HEAD `36ae958473b8530ffb1a395c4944b8cdbcae82fe`). Signature: `clear_skills_system_prompt_cache(*, clear_snapshot: bool = False)`. 06's apply sequence calls it with `clear_snapshot=True`. The earlier "may not exist" fallback in 06 IS REMOVED. The fallback path (deleting `~/.hermes/.skills_prompt_snapshot.json` directly) is dropped; if any cache reset is still needed, it targets `<scoped HERMES_HOME>/.skills_prompt_snapshot.json`, never the literal `~/.hermes/...`. Risk: low; impact: contained; mitigation: import the symbol from `agent.prompt_builder` (no circular-import risk; `agent` may import from `tools` but not vice versa).

### R7 — Script #3 Curator-store schema drift

- Script #3 depends on the Curator's usage store (project ref #45) for the `use_count` / `last_used` / view / patch columns. If the storage format or field names differ from what Script #3 assumes, the affected usage columns show `n/a` (graceful degradation; the table still renders, just blank for that skill). **The Script #3 implementation MUST verify the actual storage location + field names FIRST, before assuming any schema** — read the Curator code, not docs, and pin the discovered schema in `MIGRATION.skill-port.md`. If the schema is unexpected, update the field-name map and re-run the TDD list. Risk: low; impact: known; mitigation: `n/a` fallback + documented deviation.

## Plan-craft risks (PC1–PC5)

### PC1 — Plugin manifest has NO `kind` field (V3 / M1)

- The plugin manifest does NOT carry a `kind` field. Per V3 review (M1) and `pluginAuthoring.json`, the only known valid value for `kind` is `"backend"`; a hook+skill plugin has no kind at all, and `kind: "backend"` is the wrong declaration. **AC-1.1 is fixed to OMIT `kind`.** The plugin manifest exposes `name`, `version`, `description`, `author`, `provides_hooks`, `provides_skills`, and any other fields the loader actually reads — nothing else. No `kind` key in `plugin.yaml`. Risk: low; impact: contained; mitigation: schema check in 03's plugin-loader test.

### PC2 — Plugin manifest format is `plugin.yaml`, not `plugin.json` (V3 / M2)

- The plugin manifest is `plugin.yaml`, NOT `plugin.json`. Per V3 review (M2) and `hermes_cli/plugins.py` (anchor: "Each directory plugin must contain a `plugin.yaml` manifest"). Plan files that referenced `plugin.json` or a `entry_points` map are corrected: the load model is a single `register(ctx)` in the package `__init__.py` (or a pip entry point in group `hermes_agent.plugins`) that itself calls `ctx.register_hook('on_session_start', cb)` and `ctx.register_skill(...)`. There is NO manifest `entry_points` map and NO separate hooks/skill register entry points. Risk: low; impact: contained; mitigation: the manifest template in 03 is `plugin.yaml`; the load code in 03 calls `register(ctx)` exactly once.

### PC3 — Hard line numbers in the plan are stale (V3 / M3)

- All hard line numbers in this plan are STALE vs upstream main HEAD `36ae958473b8530ffb1a395c4944b8cdbcae82fe` (Hermes) and the upstream Anthropic commit. Per V3 review (M3), and per `docs/maybe-patch-points.md` ("Locate symbols by name; do not rely on line numbers"), the plan and all sub-files target SYMBOLS + ANCHOR TEXT, not line numbers. Where line numbers are quoted in this document (e.g. "agent/prompt_builder.py SKILLS_GUIDANCE at line 173"), they are illustrative of the V3 review pass and MUST be re-verified at Phase 5 by locating the symbol first and confirming the anchor string. Risk: low; impact: contained; mitigation: Phase 5 implementation script (`tools/rehydrate_anchors.py` or equivalent) resolves symbols → current line numbers before any patch is applied.

### PC4 — Migrated skill must be a standalone artifact, NOT embedded in the plugin (V3 / B4)

- Brief §5.4 + §6.D.6 + acceptance criteria explicitly require the migrated `skill-creator` to be a STANDALONE artifact, NOT bundled inside the plugin package. Earlier plan versions placed it at `src/hermes_skill_creator_plugin/skills/skill-creator/` — that layout is REJECTED. Correct layout:
  - `skills/skill-creator/` at the worktree root (independent top-level deliverable, sibling to `src/`, `tests/`, `docs/`).
  - Shipped/installed as a FLAT skill into `~/.hermes/skills/skill-creator/` via the hub / Script #2 `do_install` (this is also what makes `skill-creator` appear in the `<available_skills>` index).
  - The plugin MUST NOT bundle, contain, or own the skill files. The plugin's `register_skill` is REMOVED from the migration scope (or re-scoped to advisory only, with no `register_skill` call) — `ctx.register_skill` does NOT place a plugin-registered skill in the flat `~/.hermes/skills/` tree, does NOT list it in the system prompt index, and resolves only as `<plugin_name>:<name>` via explicit `skill_view()`. Surfacing the skill via `register_skill` does NOT satisfy AC-1.4 / AC-4.1.
  - AC-4.1, the 03 / 07 / 10 directory layouts, and 10 packaging are updated so the skill directory is NOT shipped inside `src/hermes_skill_creator_plugin/`.
  - Risk: low; impact: contained; mitigation: 10's `[tool.hatch.build.targets.wheel]` packages `src/hermes_skill_creator_plugin/` AND `skills/skill-creator/` as separate top-level wheels / data; the test in 03 asserts the skill directory exists at the worktree root and is not under `src/`.

### PC5 — `extract_skill_description` cap-raise patch is incomplete (V3 / B2)

- The real function `agent/skill_utils.py:extract_skill_description` (anchor: `def extract_skill_description(desc: str) -> str:`) currently returns `desc[:57] + "..."` when `len(desc) > 60`. The plan's first cut only changed `> 60` to `> MAX_DESCRIPTION_LENGTH` but left the slice as `desc[:57]`, so a >1024-char description is cut to 60 chars, not ~1021.
- The full patch MUST:
  1. Change the comparison to `if len(desc) > MAX_DESCRIPTION_LENGTH:`.
  2. Change the slice to `return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` — the codebase's own idiom (see `tools/skills_tool.py` at anchors `description[:MAX_DESCRIPTION_LENGTH - 3] + "..."`).
  3. Reuse the `MAX_DESCRIPTION_LENGTH` constant. It exists in BOTH `tools/skills_tool.py` (line ~98) and `tools/skill_manager_tool.py` (separate tools-layer cap, distinct from the system-prompt-index cap). Reusing the value is fine, BUT verify the import direction before adding `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` into `agent/skill_utils.py` (avoid `agent<->tools` circular import); if risky, define a local constant in `agent/skill_utils.py`.
  4. Add the second patch site (the slice) plus a TDD test for a >1024-char description that asserts the result is `MAX_DESCRIPTION_LENGTH` chars (not 60).
- Risk: low; impact: contained; mitigation: both patch sites are in one TDD cycle; the test fails before the second patch is applied.

## Escalation log (populated at Phase 4 HITL — 2026-06-17)

| # | Date | Question | Default | HITL decision | Action taken |
| --- | --- | --- | --- | --- | --- |
| E1 | 2026-06-17 | (Q1) nesting-guard var name | HERMES_SESSION | **HERMES_SESSION** (confirmed) | `src/hermes_skill_creator_plugin/_subprocess.py:NESTING_GUARD_VAR` set; tests assert un-nest behaviour. |
| E2 | 2026-06-17 | (Q2) Hermes event shape | adapter-based, single canonical | default accepted | Adapter in `07 §Nesting-guard helper`; re-verify shape at Phase 5 by reading `~/.hermes/hermes-agent/hermes_cli/streaming/`. |
| E3 | 2026-06-17 | (Q3) per-profile dir set | `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}` per `hermes_cli/profiles.py:_PROFILE_DIRS` | default accepted | Script #2 re-reads `hermes_cli/profiles.py:_PROFILE_DIRS` at Phase 5 implementation; if the list changed, 06 is updated. |
| E4 | 2026-06-17 | (Q4) cap-raise safety contract | --target REQUIRED, no runtime monkey-patch | **accepted** (--target REQUIRED + advisory-only) | Runtime monkey-patch removed from the plan; plugin is purely advisory (static AST read of user-owned checkout); Script #1 refuses to run if `--target == ~/.hermes/hermes-agent`. |
| E5 | 2026-06-17 | (Q5) MIGRATION split | 3 files | **3 files** (confirmed) | `MIGRATION.md` (index) + `MIGRATION.hermes-patch.md` (Script #1's cap-raise + 7 Task E sites) + `MIGRATION.skill-port.md` (T3 inventory of 15 Claude-binding replacements). All three source-controlled. |
| E6 | 2026-06-17 | (Q6) line budget | 3490 sum | default accepted | pre-commit hook `tools/check_line_count.py` enforces per-file budget; sum < 4500. |
| E7 | 2026-06-17 | (Q7) bilingual format | `[en] text / [hu] szöveg` single line + two-section `--help` | default accepted | pre-commit `tools/check_bilingual.py` enforces console format; `test_help_is_bilingual` enforces the two-section structure. |
| E8 | 2026-06-17 | (Q8) installer interactive safety | TTY confirm + `--yes` bypass | default accepted | Installer prompts in TTY, refuses real `~/.hermes` without `--yes`; integration tests use `tmp_path HERMES_HOME` + `--yes`. |
| E9 | 2026-06-17 | (Q9) active-cap detection | refuse if desc > active cap | **refuse + bilingual error** (confirmed) | Installer detects active cap (60 vs 1024) by static AST read of target; refuses install with bilingual error if description exceeds the cap; `--with-short-description` flag substitutes the truncated form. Tests cover both cap states. |
| E10 | (Phase 5) | (Q10) Script #3 enabled-detection — share with Script #2? | share via `hermes_skill_creator_plugin/_enabled_detection.py` | pending Phase 5 | (no action yet) |
| E11 | (Phase 5) | (Q11) Script #3 usage source — Curator only? | Curator only, show `n/a` on missing | pending Phase 5 | (no action yet) |

## Out of scope (explicit)

- The 60-char cosmetic preview sites in `tools/skills_tool.py`, `hermes_cli/skills_hub.py`, `hermes_cli/mcp_config.py`, `hermes_cli/mcp_catalog.py`, `tools/browser_tool.py` (locate by anchor string, e.g. `[:57] + "..."` near a comment `# preview`) are NOT patched. They are operator-TUI previews, not on the agent-injection path. Patching them is OUT OF SCOPE.
- `system_prompt.py` is NOT a patch site. It is a consumer of `MEMORY_GUIDANCE` / `SKILLS_GUIDANCE` from `prompt_builder`. Patching `prompt_builder` is sufficient.
- Cowork-specific sections in the Anthropic SKILL.md are removed (per T3.008 / T3.009 / T3.010). Hermes has no Cowork surface. Adding one is OUT OF SCOPE.
- The 60-char code-point slicing (vs grapheme slicing) in `extract_skill_description` is a known limitation. If i18n skill descriptions include ZWJ-emoji, the slice may split a grapheme. This is documented in 04 (the patch inherits the same behaviour, with the same limitation). Fixing it (grapheme-safe slicing) is OUT OF SCOPE for this plan; follow-up work.
- Registering the migrated `skill-creator` via the plugin's `ctx.register_skill(...)` is OUT OF SCOPE. `register_skill` does not place a plugin-registered skill in the flat `~/.hermes/skills/` tree and does not surface it in the system prompt `<available_skills>` index. The skill is shipped standalone and installed flat (see PC4).

<!-- end of file: 120 lines (budget 200) -->
