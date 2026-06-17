<!-- title: Script #1 — opt-in Task E built-in-prompt redirect (7 sites) -->
<!-- scope: Sec 6.E. Composes with 04-script-1-patch.md (default cap-raise site + opt-in Task E sites). -->
<!-- ACs covered: AC-2.8 -->

# 05 — Script #1: Opt-in Task E Built-in-Prompt Redirect

## Goal

Opt-in (via `--task-e-redirect`) INSERT a small additional instruction at each of the 7 prompt surfaces documented in `docs/maybe-patch-points.md` so that, before creating a NEW skill, the agent consults the optional `skill-creator` skill for authoring/validation guidance and then persists with `skill_manage`. **The original Hermes prompt text is preserved verbatim at every site; the redirect is strictly additive.** Default mode NEVER touches Task E.

## B1.0 ADDITIVE-ONLY RULE (load-bearing)

At every one of the 7 sites below, Script #1 MUST NOT rewrite or replace the original Hermes prompt text. The original wording is kept verbatim, and the ONLY delta is a single inserted paragraph / clause (the `SKILL_CREATOR_CONSULT_RULE` constant defined below) placed immediately next to the existing creation instruction. Concretely:

- DO NOT replace whole constants. For `SKILLS_GUIDANCE` and `MEMORY_GUIDANCE` (parenthesized `(...)` strings), DO NOT replace the opening/closing parens or any line inside the body; only APPEND the consult rule to the existing creation line.
- DO NOT replace whole f-strings inside `build_skills_system_prompt`. Only INSERT a new line next to the existing "If a skill has issues, fix it with skill_manage(action='patch')." / "After difficult/iterative tasks, offer to save as a skill." anchors.
- DO NOT replace the option-4 line in `_SKILL_REVIEW_PROMPT` or `_COMBINED_REVIEW_PROMPT`. The original "CREATE A NEW CLASS-LEVEL UMBRELLA ..." text is preserved; the consult rule is inserted IMMEDIATELY BEFORE the existing `skill_manage(action='create')` step.
- DO NOT redesign `SKILL_MANAGE_SCHEMA`. Only ADD a short clarifier to its `description=...` argument.
- DO NOT replace the `## Agent-Managed Skills` heading or its first paragraph in the doc site. Only INSERT the maybe-patch-points clarifications after the existing text.
- PRESERVE the existing `skill_manage(action='patch')` guidance and all surrounding text at every site.
- PRESERVE `spawn_background_review_thread` selection logic and the decision order `patch -> update-umbrella -> support-file -> create` plus all existing protections (protected skills, transient env failures, negative tool claims, one-off task narratives).

If a site's existing text cannot be located, Script #1 emits `TEXT_DRIFT` and aborts (no partial application), exactly as for the cap-raise site.

## B1.1 OBJECTIVE — the inserted rule

The inserted rule (extracted as ONE shared constant `SKILL_CREATOR_CONSULT_RULE` defined once and reused at E1, E2, E3, E4, E5) MUST say, in plain text, that before creating a new skill the agent must:

1. check installed skills (e.g. via the available-skills index / `skills_list`);
2. if `skill-creator` is installed, call `skill_view(name='skill-creator')` and follow its authoring and validation guidance when drafting the new SKILL.md;
3. persist the final skill with `skill_manage(action='create', ...)`;
4. if `skill-creator` is absent (or cannot be loaded), continue with the built-in class-level rules and persist with `skill_manage`; do NOT block creation;
5. NEVER auto-install `skill-creator`, especially not from the background review thread.

The shared constant (canonical form to be embedded verbatim in `agent/prompt_builder.py` at Phase 5 implementation time):

```python
SKILL_CREATOR_CONSULT_RULE = (
    "Before creating a new skill, check installed skills. If `skill-creator` "
    "is installed, call skill_view(name='skill-creator') and follow its "
    "authoring and validation guidance when drafting the SKILL.md; then "
    "persist with skill_manage(action='create'). If `skill-creator` is "
    "absent, continue with the built-in class-level skill rules and do not "
    "install it automatically (especially not from the background review)."
)
```

E1, E2, E3, E4, and E5 each INSERT this exact text (or a tight paraphrase that Script #1 re-emits from the constant at patch time) immediately next to the existing creation instruction. The plan deliberately does not duplicate the wording across sites; Script #1 imports the constant from `agent.prompt_builder` at run time so the two background prompts cannot drift.

## B1.2 Site table (exactly 7; `system_prompt.py` is NOT a patch site)

Anchors are described by symbol + anchor text. No line numbers (M3). Each `current_text` is the verbatim Hermes text that Script #1 locates; `insertion` is where the `SKILL_CREATOR_CONSULT_RULE` text is appended (ADDITIVE ONLY — no replacement of the surrounding text).

| site_id | file (relative to `--target`) | symbol / anchor | current_text (verbatim, 8+ char) | insertion | line shift |
| --- | --- | --- | --- | --- | --- |
| `E1.skills_guidance` | `agent/prompt_builder.py` | `SKILLS_GUIDANCE = (` | "After completing a complex task (5+ tool calls), fixing a tricky error, or discovering a non-trivial workflow, save the approach as a skill with skill_manage so you can reuse it next time." (followed by the rest of the parenthesized constant) | Append one new paragraph at the end of the constant containing `SKILL_CREATOR_CONSULT_RULE`. Preserve the existing instruction and the existing patch guidance. | +0 (additive only) |
| `E2.memory_guidance` | `agent/prompt_builder.py` | `MEMORY_GUIDANCE = (` | "If you've discovered a new way to do something, solved a problem that could be necessary later, save it as a skill with the skill tool." | Append `SKILL_CREATOR_CONSULT_RULE` to the same line (or insert a new line immediately after it inside the constant). All other lines inside `MEMORY_GUIDANCE` are preserved. | +0 (additive only) |
| `E3.build_skills_prompt` | `agent/prompt_builder.py` | `build_skills_system_prompt(...)` | "If a skill has issues, fix it with skill_manage(action='patch')." and "After difficult/iterative tasks, offer to save as a skill." (these two anchors sit next to each other in the generated index footer) | Insert `SKILL_CREATOR_CONSULT_RULE` as a new line right after the "After difficult/iterative tasks, offer to save as a skill." line. Do NOT change any of the existing lines, the f-string prefix, or the index join. | +0 (additive only) |
| `E4.skill_review_prompt_opt4` | `agent/background_review.py` | `_SKILL_REVIEW_PROMPT = (` | "4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL when no existing skill covers the class." (option 4 of the preference order, inside the parenthesized constant) | Insert `SKILL_CREATOR_CONSULT_RULE` IMMEDIATELY BEFORE the existing `skill_manage(action='create')` step in the same option 4 paragraph. Keep the option 4 heading text and the decision order `patch -> update-umbrella -> support-file -> create` untouched. | +0 (additive only) |
| `E5.combined_review_prompt_opt4` | `agent/background_review.py` | `_COMBINED_REVIEW_PROMPT = (` | "4. CREATE A NEW CLASS-LEVEL UMBRELLA when nothing exists." (DIFFERENT wording from E4 — the umbrella word is unqualified) | Insert the SAME `SKILL_CREATOR_CONSULT_RULE` text immediately before the existing `skill_manage(action='create')` step. The constant is imported from `agent.prompt_builder` so E4 and E5 cannot drift. Keep the option 4 heading and the decision order untouched. | +0 (additive only) |
| `E6.skill_manage_schema_desc` | `tools/skill_manager_tool.py` | COMPOUND anchor — 3-line sequence at `tools/skill_manager_tool.py:1099-1101` (unique as a sequence; bare `"description": (` has 8 occurrences and is NOT unique):<br>line 1099: `SKILL_MANAGE_SCHEMA = {`<br>line 1100: `    "name": "skill_manage",`<br>line 1101: `    "description": (` | "Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types. " (verbatim first line of the multi-line string opened at `tools/skill_manager_tool.py:1101`; OPTIONAL site) | APPEND a new sentence to the existing description value: "skill-creator, when installed, provides authoring guidance only. Use skill_manage to persist all skill files." Do NOT modify the tool's actions, signature, or any non-description field. | +0 (additive only) |
| `E7.skills_doc_section` | `website/docs/user-guide/features/skills.md` | `## Agent-Managed Skills (skill_manage tool)` heading | The existing first paragraph under that heading | APPEND a clarifier paragraph after the existing text covering: skill_manage stays the writer; skill-creator is optional, hub-installed, NOT bundled, NOT mandatory; absence does not disable auto-creation; background review never auto-installs it. Do NOT rename the heading or rewrite the existing paragraph. | +0 (additive only) |

> **OPTIONAL site**: `E6` is marked OPTIONAL in `docs/maybe-patch-points.md`. Script #1 includes it by default under `--task-e-redirect`; if the user passes `--no-schema-redirect` it is skipped. The site table is the spec-of-truth; if a site's `current_text` cannot be located, Script #1 emits `TEXT_DRIFT` and aborts (no partial application).

## E7 doc clarifier payload (additive only)

The verbatim clarifier paragraph Script #1 appends under `## Agent-Managed Skills (skill_manage tool)`:

```markdown
> Note: `skill-creator` is an optional, hub-installed authoring skill. It is
> NOT bundled with Hermes and is NOT required for skill creation or
> patching. `skill_manage` remains the only writer; `skill-creator` only
> supplies authoring guidance, which the agent may load with
> `skill_view(name='skill-creator')` before creating a new skill. If it
> is not installed, the agent falls back to the built-in class-level
> rules and continues; absence does not disable automatic skill
> creation. The background review thread must never auto-install it.
```

## E6 schema description payload (additive only)

The verbatim sentence Script #1 appends to the `SKILL_MANAGE_SCHEMA` main `"description"` value. The value is the multi-line string whose first line (at `tools/skill_manager_tool.py:1102`) reads verbatim:

```text
Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types.
```

The string is opened on `tools/skill_manager_tool.py:1101` by the line `    "description": (`, located immediately below `SKILL_MANAGE_SCHEMA = {` (line 1099) and `    "name": "skill_manage",` (line 1100). The 3-line sequence `SKILL_MANAGE_SCHEMA = {` / `    "name": "skill_manage",` / `    "description": (` is unique in `tools/skill_manager_tool.py` and is the compound anchor Script #1 must match. The bare `"description": (` token is NOT unique (8 occurrences: 1 top-level + 7 property sub-schemas) and must not be used as the sole anchor.

```text
skill-creator, when installed, provides authoring guidance only. Use skill_manage to persist all skill files.
```

## Composition with the cap-raise site

- `--apply` (no Task E flag) → patches **only** `S1.cap` (see `04-script-1-patch.md`).
- `--apply --task-e-redirect` → patches `S1.cap` AND all 7 Task E sites. Pre-validation pass covers 8 sites; atomic write per file. Per site, Script #1 locates the verbatim anchor, then APPENDS the `SKILL_CREATOR_CONSULT_RULE` text in the prescribed insertion slot. No site replaces original text.
- `--apply --task-e-redirect --no-schema-redirect` → 6 Task E sites (E1–E5, E7). E6 is OPTIONAL.
- `--emit-migration-note` → emits `MIGRATION.hermes-patch.md` listing all 8 sites (or 7 if `--no-schema-redirect`). The migration row count for the Task E surface is therefore 7 (or 6 with `--no-schema-redirect`) (M4). A separate `MIGRATION.skill-port.md` is emitted by the migrated skill's own emit path (see `08-migration-note-format.md`).

## B1.3 — preserved invariants

- `spawn_background_review_thread()` selection logic is unchanged: it continues to pick among `_COMBINED_REVIEW_PROMPT`, `_MEMORY_REVIEW_PROMPT`, and `_SKILL_REVIEW_PROMPT` based on `review_memory` / `review_skills`. Script #1 does not refactor the dispatcher.
- Background decision order is preserved verbatim: `patch -> update-umbrella -> support-file -> create`.
- All existing protections remain intact: protected skills, transient environment failures, negative tool claims, one-off task narratives.
- The single source of truth for the new-skill rule is the shared `SKILL_CREATOR_CONSULT_RULE` constant in `agent/prompt_builder.py` (Phase 5). Script #1 imports it at run time so E4 and E5 cannot drift.
- `skill_manage` is not redesigned. Its action routing, `create` / `patch` / `edit` / `write_file` / `remove_file` semantics, prompt-cache clearing, and background-provenance behavior are untouched.

## TDD test list

### Per-site additive-only tests
- `test_e1_appends_only` — fixture checkout; locate `SKILLS_GUIDANCE = (` and assert the original "After completing a complex task (5+ tool calls)..." text is still present verbatim after patch, AND the appended text contains the consult-rule markers (`skill_view(name='skill-creator')`, `skill_manage(action='create')`, "do not install it automatically").
- `test_e2_appends_only` — same shape for `MEMORY_GUIDANCE`: the "If you've discovered a new way to do something..." line is preserved and the appended text contains the consult-rule markers.
- `test_e3_appends_only` — locate `build_skills_system_prompt`; assert both the "If a skill has issues, fix it with skill_manage(action='patch')." line and the "After difficult/iterative tasks, offer to save as a skill." line are present verbatim, and the consult rule sits immediately after them.
- `test_e4_appends_only` — locate `_SKILL_REVIEW_PROMPT = (` and the option-4 anchor "4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL ..."; assert the option-4 text is preserved, the consult rule is present, and the consult rule precedes the existing `skill_manage(action='create')` step.
- `test_e5_appends_only` — same shape for `_COMBINED_REVIEW_PROMPT` with the differently-worded "4. CREATE A NEW CLASS-LEVEL UMBRELLA when nothing exists." anchor.
- `test_e4_e5_share_constant` — import `SKILL_CREATOR_CONSULT_RULE` from `agent.prompt_builder`; assert it appears verbatim inside both `_SKILL_REVIEW_PROMPT` and `_COMBINED_REVIEW_PROMPT` (no drift).
- `test_e6_appends_only` — locate the COMPOUND 3-line anchor in `tools/skill_manager_tool.py` (line 1099 `SKILL_MANAGE_SCHEMA = {`, line 1100 `    "name": "skill_manage",`, line 1101 `    "description": (`). Assert the verbatim first-line `"Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types. "` is still present, that the appended sentence ends the same description value, and that the compound-anchor uniqueness invariant holds (the 3-line sequence has exactly 1 hit in `tools/skill_manager_tool.py`). Assert no other field of the schema changed (action enum, required fields, etc.). The bare `"description": (` token has 8 occurrences and must NOT be used as the sole anchor; this test must therefore match the compound 3-line sequence, not the bare token.
- `test_e7_appends_only` — locate `## Agent-Managed Skills (skill_manage tool)` heading; assert the heading and the existing first paragraph are unchanged and the new clarifier paragraph (with the exact payload above) is present immediately after.

### Composition
- `test_default_no_task_e_touch` — `--apply` without `--task-e-redirect` leaves all 4 Task E files byte-identical (sha256 snapshot) AND does not import / emit `SKILL_CREATOR_CONSULT_RULE`.
- `test_task_e_redirect_eight_sites` — `--apply --task-e-redirect` patches `S1.cap` + 7 Task E sites; `.patch.state.json` has 8 entries; for each Task E entry, `before` and `after` differ only by the inserted consult rule (diff is the inserted block plus surrounding whitespace).
- `test_no_schema_redirect_skips_e6` — `--apply --task-e-redirect --no-schema-redirect` patches 7 sites (E1–E5, E7) and skips E6.
- `test_e6_optional_default_on` — `--apply --task-e-redirect` includes E6 unless `--no-schema-redirect`.

### Idempotency / drift
- `test_task_e_reapply_is_idempotent` — second `--apply --task-e-redirect` exits 0 with `OK: already patched / OK: már javítva` for all 8 sites. Anchors are re-located against the post-patch file (the appended text is part of the matched block, so the anchor still resolves).
- `test_task_e_drift_exits_2` — corrupt the E4 option-4 anchor; run `--apply --task-e-redirect`; exit 2 with `TEXT_DRIFT` naming E4.
- `test_task_e_force_only_retries_drifted` — pre-patch 7/8 sites; drift E3; `--force` re-applies only E3 (additive insertion re-runs without disturbing the other appended inserts).

### Migration note
- `test_emit_migration_note_lists_all_sites` — `--emit-migration-note` produces a `MIGRATION.hermes-patch.md` table with exactly 8 rows (7 with `--no-schema-redirect`); the worktree's `MIGRATION.md` index links to it. The Task E surface is described as "additive insertion" (not "replace"), and the row count note matches (M4).

### Preserved invariants
- `test_spawn_background_review_thread_selection_unchanged` — assert the dispatcher still resolves to one of the three prompt constants based on `review_memory` / `review_skills`; no new branches introduced.
- `test_background_decision_order_preserved` — assert the patched option-4 paragraph still contains the patch -> update-umbrella -> support-file -> create order (or the combined-prompt's equivalent ordering), with the consult rule slotted in BEFORE the create step only.

## Out of scope (explicit)

- `system_prompt.py` is NOT a patch site. It imports `MEMORY_GUIDANCE` and `SKILLS_GUIDANCE` from `prompt_builder` (per `agent/system_prompt.py:34, 38` — symbol anchors `from .prompt_builder import MEMORY_GUIDANCE` and `from .prompt_builder import SKILLS_GUIDANCE`) and is a CONSUMER, not a source. Patching it would be a no-op once `prompt_builder` is patched.
- The 60-char cosmetic preview sites in `tools/skills_tool.py`, `hermes_cli/skills_hub.py`, `hermes_cli/mcp_config.py`, `hermes_cli/mcp_catalog.py`, and `tools/browser_tool.py` are NOT in the 7-site spec and are NOT patched. They are operator-TUI previews, not on the agent-injection path.
- `skill_manage` is not redesigned; `skill-creator` is not bundled, installed, fetched, or imported by the redirect; no network call is added.

## Decisions & evidence

### D1. Task E is ADDITIVE ONLY (B1.0)
- **Decision**: every one of the 7 Task E sites inserts the `SKILL_CREATOR_CONSULT_RULE` next to the existing creation instruction. The original Hermes prompt text is preserved verbatim at every site; `Script #1` never replaces existing wording.
- **Rationale**: HITL feedback in round 1/2 rejected "replace" semantics — Hermes-side prompts are out of scope for behavioral change; only an optional consult hook is being inserted.
- **Evidence**: HITL-confirmed Q1/Q4/Q5/Q9 (memory: `hermes-skills-hitl-decisions.md`); 05 §B1.0 ADDITIVE-ONLY RULE; V6 RR1 reaffirmation. Confidence: verified-from-source.

### D2. Shared constant `SKILL_CREATOR_CONSULT_RULE` is imported, not duplicated (B1)
- **Decision**: the inserted rule lives as ONE Python constant in `agent/prompt_builder.py` and is imported by `agent/background_review.py` so E4 and E5 cannot drift.
- **Rationale**: B1.1 + B1.2 require identical wording at E4 and E5. A Python-level import is the only reliable way to prevent silent drift between two background-prompt constants.
- **Evidence**: 05 §B1.1 OBJECTIVE; `test_e4_e5_share_constant` in this file. Module path is ASSUMED consistent with 02/03/04 plan references; the implementer MUST pin the exact file:line at Phase 5. Confidence: assumed (module path); verified-from-source (E4/E5 anchor locations).

### D3. E6 anchor is the COMPOUND 3-line sequence (RR1 fix)
- **Decision**: E6 is located by the COMPOUND 3-line sequence at `tools/skill_manager_tool.py:1099-1101`:
  - line 1099: `SKILL_MANAGE_SCHEMA = {`
  - line 1100: `    "name": "skill_manage",`
  - line 1101: `    "description": (`
  The bare `"description": (` token is NOT used as a sole anchor (it has 8 occurrences: 1 top-level + 7 property sub-schemas).
- **Rationale**: matching the bare token would be ambiguous and could `TEXT_DRIFT` on the wrong sub-schema. The 3-line sequence is unique (1 hit) and reliably identifies the top-level `SKILL_MANAGE_SCHEMA` description.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skill_manager_tool.py:1099-1101`; V6 RR1; `test_e6_appends_only` + `test_task_e_current_text_is_unique_in_source` in 09. Confidence: verified-from-source.

### D4. E6 `current_text` first-line is byte-for-byte from line 1102 (RR1 fix)
- **Decision**: the E6 `current_text` is the verbatim first line of the multi-line string opened at `tools/skill_manager_tool.py:1102`: `"Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types. "`.
- **Rationale**: the round-1/2 `current_text` `"Create, edit, patch, delete, write_file, or remove_file"` has 0 hits in the real source and causes `TEXT_DRIFT` + abort on a default-on E6 patch. The real first line MUST be copied byte-for-byte so the locator matches.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skill_manager_tool.py:1102`; V6 RR1. Confidence: verified-from-source.

### D5. E6 is OPTIONAL, default-on under `--task-e-redirect`; `--no-schema-redirect` skips it
- **Decision**: of the 7 Task E sites, only E6 is OPTIONAL. Script #1 includes E6 by default under `--task-e-redirect`; `--no-schema-redirect` skips E6 and patches the other 6 sites.
- **Rationale**: `docs/maybe-patch-points.md` marks E6 OPTIONAL. The flag gives operators an escape hatch (e.g., for forks that already expose `skill-creator` semantics) without losing the 6 additive prompt sites.
- **Evidence**: `docs/maybe-patch-points.md` (HITL Q1/Q4/Q5/Q9 confirmed); 05 §B1.2 Site table note. Confidence: verified-from-source.

### D6. 7 sites total; `system_prompt.py` is NOT a patch site
- **Decision**: the Task E spec is exactly 7 sites (E1..E7). `agent/system_prompt.py` is NOT in the table; it is a CONSUMER of `MEMORY_GUIDANCE` / `SKILLS_GUIDANCE` and would be a no-op after `prompt_builder` is patched.
- **Rationale**: including `system_prompt.py` would inflate the migration row count past the 7-site spec without changing behavior.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `agent/system_prompt.py:34, 38` (anchors `from .prompt_builder import MEMORY_GUIDANCE` / `from .prompt_builder import SKILLS_GUIDANCE`); 05 §Out of scope. Confidence: verified-from-source.

### D7. Preserved invariants: dispatcher logic + decision order unchanged
- **Decision**: `spawn_background_review_thread()` selection logic and the `patch -> update-umbrella -> support-file -> create` decision order are preserved verbatim. `skill_manage` action routing is unchanged.
- **Rationale**: round-1/2 review rejected any "rewrite" of the dispatcher or the action surface; only an optional consult hook is inserted.
- **Evidence**: 05 §B1.3 preserved invariants; `test_spawn_background_review_thread_selection_unchanged` + `test_background_decision_order_preserved` in this file. Confidence: verified-from-source.

<!-- end of file: 187 lines (budget 250) -->
