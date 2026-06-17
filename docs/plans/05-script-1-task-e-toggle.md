<!-- title: Script #1 — opt-in Task E built-in-prompt redirect (7 sites) -->
<!-- scope: Sec 6.E. Composes with 04-script-1-patch.md (default cap-raise site + opt-in Task E sites). -->
<!-- ACs covered: AC-2.8 -->

# 05 — Script #1: Opt-in Task E Built-in-Prompt Redirect

## Goal

Opt-in (via `--task-e-redirect`) INSERT a small additional instruction at each of the 7 prompt surfaces documented in `docs/maybe-patch-points.md` so that, before creating a NEW skill (or substantially editing/validating one), the agent consults the optional `skill-creator` skill for authoring/validation guidance and then persists with `skill_manage`. **The original Hermes prompt text is preserved verbatim at every site; the redirect is strictly additive.** Default mode NEVER touches Task E.

## B1.0 ADDITIVE-ONLY RULE (load-bearing)

At every one of the 7 sites below, Script #1 MUST NOT rewrite or replace the original Hermes prompt text. The original wording is kept verbatim, and the ONLY delta is a single inserted line (the `SKILL_CREATOR_CONSULT_RULE` constant defined below) placed immediately next to the existing creation instruction. Concretely:

- DO NOT replace whole constants. For `SKILLS_GUIDANCE` and `MEMORY_GUIDANCE` (parenthesized `(...)` strings), DO NOT replace the opening/closing parens or any line inside the body; only APPEND the consult rule to the existing creation line.
- DO NOT replace whole f-strings inside `build_skills_system_prompt`. Only INSERT a new line next to the existing "If a skill has issues, fix it with skill_manage(action='patch')." / "After difficult/iterative tasks, offer to save as a skill." anchors.
- DO NOT replace the option-4 paragraph in `_SKILL_REVIEW_PROMPT` or `_COMBINED_REVIEW_PROMPT`. The original "CREATE A NEW CLASS-LEVEL UMBRELLA ..." text is preserved; the consult rule is inserted AFTER the option-4 paragraph closes (i.e. after the closing `(1), (2), or (3)` line, NOT between L100–L105 / L188–L192, which would split the sentence).
- DO NOT redesign `SKILL_MANAGE_SCHEMA`. Only ADD a short clarifier to its `description=...` argument.
- DO NOT replace the `## Agent-Managed Skills` heading or its first paragraph in the doc site. Only INSERT the maybe-patch-points clarifications after the existing text.
- PRESERVE the existing `skill_manage(action='patch')` guidance and all surrounding text at every site.
- PRESERVE `spawn_background_review_thread` selection logic and the decision order `patch -> update-umbrella -> support-file -> create` plus all existing protections (protected skills, transient env failures, negative tool claims, one-off task narratives).

If a site's existing text cannot be located, Script #1 emits `TEXT_DRIFT` and aborts (no partial application), exactly as for the cap-raise site.

## B1.1 OBJECTIVE — the inserted rule

The inserted rule (extracted as ONE shared constant `SKILL_CREATOR_CONSULT_RULE` defined once and reused at E1, E2, E3, E4, E5) MUST say, in plain text, that before creating / substantially editing / validating a skill the agent must:

1. check installed skills (e.g. via the available-skills index / `skills_list`);
2. if `skill-creator` is installed, call `skill_view(name='skill-creator')` and follow its authoring and validation guidance when drafting the new SKILL.md;
3. persist the final skill with `skill_manage(action='create', ...)` (or `patch` for small targeted fixes);
4. if `skill-creator` is absent (or cannot be loaded), continue with the built-in class-level rules and persist with `skill_manage`; do NOT block creation;
5. NEVER auto-install `skill-creator`, especially not from the background review thread.

The shared constant (canonical form to be embedded verbatim in `agent/prompt_builder.py` at Phase 5 implementation time; **imported** into `agent/background_review.py` so E4 and E5 cannot drift):

```python
SKILL_CREATOR_CONSULT_RULE = (
    "When creating a new skill — or substantially editing or validating one — first check installed "
    "skills; if `skill-creator` is installed, load it via skill_view(name='skill-creator') and follow its "
    "authoring/validation guidance, then persist with skill_manage. Small targeted fixes stay patch-first. "
    "If `skill-creator` is absent, use the built-in skill rules and never auto-install it (especially not "
    "from the background review)."
)
```

E1, E2, E3, E4, and E5 each INSERT this exact text (re-emitted from the constant at patch time) immediately next to the existing creation instruction. The plan deliberately does not duplicate the wording across sites; Script #1 imports the constant from `agent.prompt_builder` at run time so the two background prompts cannot drift.

## B1.2 Site table (exactly 7; `system_prompt.py` is NOT a patch site)

Anchors are described by byte-exact line + locator text (copied from the pinned `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` source via `cat -A`). Each `current_text` is a SINGLE physical source line; `insertion` is the verbatim new line (with explicit indent + `+ SKILL_CREATOR_CONSULT_RULE` concatenation) that Script #1 appends (ADDITIVE ONLY — no replacement of the surrounding text).

| site_id | file (relative to `--target`) | locator (file : line — byte-exact) | insertion (verbatim new line) | placement |
| --- | --- | --- | --- | --- |
| `E1.skills_guidance` | `agent/prompt_builder.py` | L179: `    "Skills that aren't maintained become liabilities."` (single physical line; 4-space indent; closed by `)` on L180) | `    " " + SKILL_CREATOR_CONSULT_RULE` | AFTER L179, before the `)` on L180 (4-space indent, no trailing `\n` — the closing `)` lives on L180) |
| `E2.memory_guidance` | `agent/prompt_builder.py` | L158: `    "necessary later, save it as a skill with the skill tool.\n"` (single physical line; 4-space indent; ends with `\n`) | `    " " + SKILL_CREATOR_CONSULT_RULE + "\n"` | new line immediately AFTER L158 (inside the parenthesized `MEMORY_GUIDANCE` constant; 4-space indent) |
| `E3.build_skills_prompt` | `agent/prompt_builder.py` (inside `build_skills_system_prompt`) | L1421: `            "After difficult/iterative tasks, offer to save as a skill. "` (single physical line; 12-space indent; do NOT touch the `<available_skills>` join at L1425-L1426) | `            SKILL_CREATOR_CONSULT_RULE + "\n"` | new line AFTER L1421, before L1422 (12-space indent) |
| `E4.skill_review_prompt_opt4` | `agent/background_review.py` (`_SKILL_REVIEW_PROMPT`) | L105: `    "today's task, it's wrong — fall back to (1), (2), or (3).\n\n"` (single physical line; 4-space indent; ends with `\n\n`; this line CLOSES the option-4 paragraph) | `    SKILL_CREATOR_CONSULT_RULE + "\n\n"` | AFTER L105 (i.e. after the option-4 paragraph closes). Do NOT insert between L100-L105 (splits the sentence). Import the constant. |
| `E5.combined_review_prompt_opt4` | `agent/background_review.py` (`_COMBINED_REVIEW_PROMPT`) | L192: `    "(2), or (3).\n\n"` (single physical line; 4-space indent; ends with `\n\n`; this line CLOSES the option-4 paragraph) | `    SKILL_CREATOR_CONSULT_RULE + "\n\n"` | AFTER L192 (after option-4 closes). Do NOT insert between L188-L192. |
| `E6.skill_manage_schema_desc` | `tools/skill_manager_tool.py` (`SKILL_MANAGE_SCHEMA`) | L1129: `        "pitfalls come up; pin only guards against irrecoverable loss."` (single physical line; 8-space indent; UNIQUE in the file; append at end of the top-level `description` value, before the `),` on L1130) | `        " skill-creator, when installed, supplies authoring/validation guidance only (skill_view(name='skill-creator')); skill_manage remains the writer and never auto-installs it."` | new line AFTER L1129, before the `),` on L1130 (8-space). Do NOT change actions/required/properties. Compound symbol locator (used to disambiguate from the 7 property sub-schemas whose `"description": (` is non-unique): L1099 `SKILL_MANAGE_SCHEMA = {` / L1100 `    "name": "skill_manage",` / L1101 `    "description": (`. |
| `E7.skills_doc_section` | `website/docs/user-guide/features/skills.md` | L380: existing first paragraph under the `## Agent-Managed Skills (skill_manage tool)` heading | `> Note: \`skill-creator\` is an optional, hub-installed authoring/validation skill — NOT bundled, NOT required. \`skill_manage\` remains the only writer; the agent may \`skill_view(name='skill-creator')\` for guidance before creating/editing a skill, falls back to built-in rules if it is absent (auto-creation stays enabled), and the background review never auto-installs it.` | new line AFTER L380, before the blank line preceding `### When the Agent Creates Skills`. Do NOT rename the heading. |

> **OPTIONAL site**: `E6` is marked OPTIONAL in `docs/maybe-patch-points.md`. Script #1 includes it by default under `--task-e-redirect`; if the user passes `--no-schema-redirect` it is skipped. The site table is the spec-of-truth; if a site's locator cannot be matched, Script #1 emits `TEXT_DRIFT` and aborts (no partial application).

## B1.2.1 Why single-line anchors (not joined strings)

Python adjacent-string-literal concatenation means a logical sentence can be split across two physical lines with zero characters between them. A naive substring match against the joined logical sentence (e.g. the original `current_text` "Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types. ") returns 0 hits because that joined form does not appear as a contiguous byte sequence in the file. The locators above are each a SINGLE physical line copied byte-for-byte from the pinned source (`cat -A`-verified). Script #1 matches each locator as a literal substring against the target file's raw bytes — no implicit-concat normalization — and TEXT_DRIFTs + aborts if the match count is != 1.

## E7 doc clarifier payload (additive only)

The verbatim clarifier paragraph Script #1 appends under `## Agent-Managed Skills (skill_manage tool)`:

```markdown
> Note: `skill-creator` is an optional, hub-installed authoring/validation skill — NOT bundled, NOT required. `skill_manage` remains the only writer; the agent may `skill_view(name='skill-creator')` for guidance before creating/editing a skill, falls back to built-in rules if it is absent (auto-creation stays enabled), and the background review never auto-installs it.
```

## E6 schema description payload (additive only)

The verbatim new line Script #1 appends immediately AFTER `tools/skill_manager_tool.py:1129` (the unique closing sentence of the top-level `description` value) and BEFORE the `),` on L1130:

```text
        " skill-creator, when installed, supplies authoring/validation guidance only (skill_view(name='skill-creator')); skill_manage remains the writer and never auto-installs it."
```

The appended sentence starts with a single leading space (concatenates to the previous line's trailing `recoverable loss."`), preserving the implicit-concat flow of the multi-line description. The compound 3-line symbol locator (`SKILL_MANAGE_SCHEMA = {` / `    "name": "skill_manage",` / `    "description": (`) is used to disambiguate from the 7 property sub-schemas whose bare `"description": (` token is non-unique.

## Composition with the cap-raise site

- `--apply` (no Task E flag) → patches **only** `S1.cap` (see `04-script-1-patch.md`).
- `--apply --task-e-redirect` → patches `S1.cap` AND all 7 Task E sites. Pre-validation pass covers 8 sites; atomic write per file. Per site, Script #1 locates the byte-exact single-line anchor, then APPENDS the `SKILL_CREATOR_CONSULT_RULE` (or schema clarifier) line in the prescribed insertion slot. No site replaces original text.
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
- `test_e1_appends_only` — fixture checkout; locate the byte-exact single-line anchor `    "Skills that aren't maintained become liabilities."` (agent/prompt_builder.py L179); assert it is still present verbatim after patch, AND the appended `    " " + SKILL_CREATOR_CONSULT_RULE` line sits between L179 and the `)` on L180. Verify the consult-rule markers (`skill_view(name='skill-creator')`, `skill_manage`, "never auto-install") are reachable in the constant.
- `test_e2_appends_only` — same shape for `MEMORY_GUIDANCE`: the byte-exact L158 anchor `    "necessary later, save it as a skill with the skill tool.\n"` is preserved and the appended `    " " + SKILL_CREATOR_CONSULT_RULE + "\n"` line follows it.
- `test_e3_appends_only` — locate `build_skills_system_prompt`; assert both the "If a skill has issues, fix it with skill_manage(action='patch')." line and the byte-exact L1421 anchor `            "After difficult/iterative tasks, offer to save as a skill. "` are present verbatim, and the consult-rule line sits immediately after L1421 (12-space indent). Do NOT touch the `<available_skills>` join.
- `test_e4_appends_only` — locate `_SKILL_REVIEW_PROMPT = (` and the byte-exact L105 anchor `    "today's task, it's wrong — fall back to (1), (2), or (3).\n\n"`; assert L100-L105 are preserved verbatim (sentence is NOT split), and the consult-rule line sits AFTER L105. Verify the consult rule does NOT appear between L100-L105.
- `test_e5_appends_only` — same shape for `_COMBINED_REVIEW_PROMPT` with the byte-exact L192 anchor `    "(2), or (3).\n\n"`; assert L188-L192 are preserved verbatim, consult rule sits AFTER L192.
- `test_e4_e5_share_constant` — import `SKILL_CREATOR_CONSULT_RULE` from `agent.prompt_builder`; assert it appears verbatim inside both `_SKILL_REVIEW_PROMPT` and `_COMBINED_REVIEW_PROMPT` (no drift). Assert `agent/background_review.py` imports the constant from `agent.prompt_builder` rather than redefining it.
- `test_e6_appends_only` — locate the byte-exact L1129 anchor `        "pitfalls come up; pin only guards against irrecoverable loss."` (unique; 1 hit in `tools/skill_manager_tool.py`). Assert the L1099-L1101 3-line compound symbol locator resolves to exactly one location. Assert the appended sentence (with the exact payload above) sits between L1129 and the `),` on L1130. Assert no other field of the schema changed (action enum, required fields, etc.). The bare `"description": (` token has 8 occurrences and must NOT be used as the sole anchor; this test must therefore match the L1129 single-line locator AND the 3-line compound sequence, not the bare token.
- `test_e7_appends_only` — locate `## Agent-Managed Skills (skill_manage tool)` heading and the byte-exact L380 anchor (existing first paragraph); assert the heading and L380 are unchanged and the new clarifier paragraph (with the exact payload above) is present immediately after, before the blank line preceding `### When the Agent Creates Skills`.

### Anchor-hygiene tests
- `test_task_e_current_text_is_unique_in_source` — for each of E1, E2, E3, E4, E5, E6, E7, run a literal-substring grep against the pinned checkout source: each `current_text` above MUST yield exactly 1 hit in its named file, AND the matched line MUST be byte-identical to the locator (no whitespace normalization, no implicit-concat joining). Failure exits 2 with `TEXT_DRIFT` naming the offending site.
- `test_no_implicit_concat_normalization` — assert Script #1's locator matcher does NOT collapse adjacent string literals (no `.replace('\n', '')` or AST-join preprocessing); the match is raw-bytes against the file as-read.

### Composition
- `test_default_no_task_e_touch` — `--apply` without `--task-e-redirect` leaves all 4 Task E files byte-identical (sha256 snapshot) AND does not import / emit `SKILL_CREATOR_CONSULT_RULE`.
- `test_task_e_redirect_eight_sites` — `--apply --task-e-redirect` patches `S1.cap` + 7 Task E sites; `.patch.state.json` has 8 entries; for each Task E entry, `before` and `after` differ only by the inserted line(s) (diff is the inserted line plus surrounding whitespace).
- `test_no_schema_redirect_skips_e6` — `--apply --task-e-redirect --no-schema-redirect` patches 7 sites (E1–E5, E7) and skips E6.
- `test_e6_optional_default_on` — `--apply --task-e-redirect` includes E6 unless `--no-schema-redirect`.

### Idempotency / drift
- `test_task_e_reapply_is_idempotent` — second `--apply --task-e-redirect` exits 0 with `OK: already patched / OK: már javítva` for all 8 sites. Anchors are re-located against the post-patch file (the appended text is part of the matched block, so the anchor still resolves).
- `test_task_e_drift_exits_2` — corrupt the E4 L105 anchor; run `--apply --task-e-redirect`; exit 2 with `TEXT_DRIFT` naming E4.
- `test_task_e_force_only_retries_drifted` — pre-patch 7/8 sites; drift E3 (replace L1421); `--force` re-applies only E3 (additive insertion re-runs without disturbing the other appended inserts).

### Migration note
- `test_emit_migration_note_lists_all_sites` — `--emit-migration-note` produces a `MIGRATION.hermes-patch.md` table with exactly 8 rows (7 with `--no-schema-redirect`); the worktree's `MIGRATION.md` index links to it. The Task E surface is described as "additive insertion" (not "replace"), and the row count note matches (M4).

### Preserved invariants
- `test_spawn_background_review_thread_selection_unchanged` — assert the dispatcher still resolves to one of the three prompt constants based on `review_memory` / `review_skills`; no new branches introduced.
- `test_background_decision_order_preserved` — assert the patched option-4 paragraph still contains the patch -> update-umbrella -> support-file -> create order (or the combined-prompt's equivalent ordering), with the consult rule slotted in AFTER the closing `(1), (2), or (3)` line only.

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

### D3. E6 anchor is the L1129 single-line locator + 3-line compound symbol locator (RR1 fix)
- **Decision**: E6 is located primarily by the single physical line `        "pitfalls come up; pin only guards against irrecoverable loss."` at `tools/skill_manager_tool.py:1129` (UNIQUE — 1 hit in the file). For the description-value boundary, Script #1 also matches the compound 3-line sequence at L1099-L1101 (`SKILL_MANAGE_SCHEMA = {` / `    "name": "skill_manage",` / `    "description": (`) to disambiguate from the 7 property sub-schemas whose bare `"description": (` token is non-unique (8 occurrences).
- **Rationale**: the round-1/2 `current_text` "Manage skills (create, update, delete). Skills are your procedural memory — reusable approaches for recurring task types." has 0 single-line hits in the source (it is split across L1102/L1103 by Python implicit-concat) and causes `TEXT_DRIFT` + abort on a default-on E6 patch. L1129 is byte-exact, unique, and sits at the END of the top-level description value — appending the new sentence there is unambiguously additive and lands before the closing `),` on L1130.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skill_manager_tool.py:1099-1101` (compound) and `tools/skill_manager_tool.py:1129` (L1129 locator); `docs/review/TASK_E_PROMPT_EDITS.md`; V7 RR1; `test_e6_appends_only` + `test_task_e_current_text_is_unique_in_source` + `test_no_implicit_concat_normalization` in 09. Confidence: verified-from-source.

### D4. E6 `description` value opens at line 1101, first string literal at line 1102 (RR1 fix)
- **Decision**: the top-level `description` value of `SKILL_MANAGE_SCHEMA` is opened by `    "description": (` at `tools/skill_manager_tool.py:1101`. Line 1102 is the FIRST STRING LITERAL of the implicit-concat multi-line string (not the opener). Prior D4 prose that said "description opened at 1102" is off by one — the opener is L1101.
- **Rationale**: distinguishing the opener (L1101) from the first literal (L1102) is required for accurate citation; the original quoted number was the first-literal line, not the opener.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `tools/skill_manager_tool.py:1101` is `    "description": (`, `tools/skill_manager_tool.py:1102` is the first string literal `"...your procedural "`. Confidence: verified-from-source.

### D5. E1/E2/E4/E6 use single-physical-line locators, not joined strings (RR1 fix)
- **Decision**: the locators for E1 (L179), E2 (L158), E4 (L105), and E6 (L1129) are each a SINGLE contiguous physical line copied byte-for-byte from the pinned source. The previous joined-logical-sentence `current_text` strings (which span 2 physical lines via Python implicit-concat and have 0 raw-byte hits) are REMOVED from the site table.
- **Rationale**: Script #1 matches `current_text` as a literal substring with NO implicit-concat normalization specified — a joined string would TEXT_DRIFT + ABORT on a default-on run. A single-line locator is the only way to guarantee exactly-1 raw-byte hit.
- **Evidence**: `docs/review/TASK_E_PROMPT_EDITS.md` (byte-verified via `cat -A`); `test_task_e_current_text_is_unique_in_source` + `test_no_implicit_concat_normalization` in 09. Confidence: verified-from-source.

### D6. E6 is OPTIONAL, default-on under `--task-e-redirect`; `--no-schema-redirect` skips it
- **Decision**: of the 7 Task E sites, only E6 is OPTIONAL. Script #1 includes E6 by default under `--task-e-redirect`; `--no-schema-redirect` skips E6 and patches the other 6 sites.
- **Rationale**: `docs/maybe-patch-points.md` marks E6 OPTIONAL. The flag gives operators an escape hatch (e.g., for forks that already expose `skill-creator` semantics) without losing the 6 additive prompt sites.
- **Evidence**: `docs/maybe-patch-points.md` (HITL Q1/Q4/Q5/Q9 confirmed); 05 §B1.2 Site table note. Confidence: verified-from-source.

### D7. 7 sites total; `system_prompt.py` is NOT a patch site
- **Decision**: the Task E spec is exactly 7 sites (E1..E7). `agent/system_prompt.py` is NOT in the table; it is a CONSUMER of `MEMORY_GUIDANCE` / `SKILLS_GUIDANCE` and would be a no-op after `prompt_builder` is patched.
- **Rationale**: including `system_prompt.py` would inflate the migration row count past the 7-site spec without changing behavior.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `agent/system_prompt.py:34, 38` (anchors `from .prompt_builder import MEMORY_GUIDANCE` / `from .prompt_builder import SKILLS_GUIDANCE`); 05 §Out of scope. Confidence: verified-from-source.

### D8. Preserved invariants: dispatcher logic + decision order unchanged
- **Decision**: `spawn_background_review_thread()` selection logic and the `patch -> update-umbrella -> support-file -> create` decision order are preserved verbatim. `skill_manage` action routing is unchanged.
- **Rationale**: round-1/2 review rejected any "rewrite" of the dispatcher or the action surface; only an optional consult hook is inserted.
- **Evidence**: 05 §B1.3 preserved invariants; `test_spawn_background_review_thread_selection_unchanged` + `test_background_decision_order_preserved` in this file. Confidence: verified-from-source.

<!-- end of file: 183 lines (budget 250) -->