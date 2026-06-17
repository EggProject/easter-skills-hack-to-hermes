<!-- title: Script #1 — opt-in Task E built-in-prompt redirect (7 sites) -->
<!-- scope: Sec 6.E. Composes with 04-script-1-patch.md (default cap-raise site + opt-in Task E sites). -->
<!-- ACs covered: AC-2.8 -->

# 05 — Script #1: Opt-in Task E Built-in-Prompt Redirect

## Goal

Opt-in (via `--task-e-redirect`) replace the 7 prompt strings documented in `docs/maybe-patch-points.md` that currently teach the model to use Anthropic-style skill authoring. The replacement strings make the same teaching pass reference Hermes's `skill_manage`/`skill_view`/`skills_list` flow. **Default mode NEVER touches Task E.**

## Site table (exactly 7; `system_prompt.py` is NOT a patch site)

| site_id | file (relative to `--target`) | line | current_text (8+ char anchor) | replacement_text | line shift |
| --- | --- | --- | --- | --- | --- |
| `E1.skills_guidance` | `agent/prompt_builder.py` | 172 | `SKILLS_GUIDANCE = """` (block continues ~30 lines, replace whole constant) | See anchor block E1 below | +0 (same length block) |
| `E2.memory_guidance` | `agent/prompt_builder.py` | 143 | `MEMORY_GUIDANCE = """` (block continues ~25 lines) | See anchor block E2 below | +0 |
| `E3.build_skills_prompt` | `agent/prompt_builder.py` | 1373 | `return "<available_skills>\n" +` (f-string prefix inside `build_skills_system_prompt`) | See anchor block E3 below | +0 |
| `E4.skill_review_prompt_opt4` | `agent/background_review.py` | 45 | `_SKILL_REVIEW_PROMPT = """` (option-4 line is `4. Use the Skill tool` block, ~inner line 100) | See anchor block E4 below | +0 |
| `E5.combined_review_prompt_opt4` | `agent/background_review.py` | 150 | `_COMBINED_REVIEW_PROMPT = """` (option-4 line, ~inner line 188) | See anchor block E5 below | +0 |
| `E6.skill_manage_schema_desc` | `tools/skill_manager_tool.py` | ~992 | `description="""Create, edit, patch, delete, write_file, or remove_file` (the SKILL_MANAGE_SCHEMA top description; OPTIONAL site) | See anchor block E6 below | +0 |
| `E7.skills_doc_section` | `website/docs/user-guide/features/skills.md` | 378 | `## Agent-Managed Skills` (Markdown heading) | See anchor block E7 below | +0 |

> **OPTIONAL site**: `E6` is marked OPTIONAL in `docs/maybe-patch-points.md`. Script #1 includes it by default under `--task-e-redirect`; if the user passes `--no-schema-redirect` it is skipped. The site table is the spec-of-truth; if a site's `current_text` cannot be located at the cited line on the operator's checkout, Script #1 emits `TEXT_DRIFT` and aborts (no partial application).

## Anchor blocks (replacement payloads)

### E1.skills_guidance (replace whole constant body)

```python
SKILLS_GUIDANCE = """\
Hermes skills are managed with skill_manage (create/edit/patch/delete/write_file/remove_file)
and read with skill_view / skills_list. To author a new skill:
  1. skills_list() to see existing categories and avoid collisions.
  2. skill_view(name='hermes-agent-skill-authoring') to load the authoring rules.
  3. Write the SKILL.md to ~/.hermes/skills/<category>/<name>/SKILL.md via write_file.
  4. skill_manage(action='create', name=..., category=..., body=...) to register it.
  5. Verify in a fresh session (skill cache is session-scoped).
"""
```

### E2.memory_guidance (replace whole constant body)

```python
MEMORY_GUIDANCE = """\
Persistent memory is stored with the memory tool (memory_write / memory_read).
Cross-session search uses session_search. Skills are NOT memory — they are packaged
reusable prompts loaded via skill_view.
"""
```

### E3.build_skills_prompt (replace the f-string prefix to call out Hermes tool names)

```python
return (
    "<available_skills>\n"
    "The following skills are available. Use skills_list() to enumerate them, "
    "skill_view(name=...) to load a skill's full body, and skill_manage(action=...) "
    "to create, edit, patch, or delete skills.\n"
    + "\n".join(index_lines)
    + "\n</available_skills>\n"
)
```

### E4.skill_review_prompt_opt4 (replace option 4 inside `_SKILL_REVIEW_PROMPT`)

Replace the option `4. Use the Skill tool` line and its continuation with:

```
4. Use skill_manage(action='create' | 'edit' | 'patch' | 'delete' | 'write_file' | 'remove_file')
   and skill_view / skills_list to author a skill in ~/.hermes/skills/<cat>/<name>/.
```

### E5.combined_review_prompt_opt4 (same shape as E4 inside `_COMBINED_REVIEW_PROMPT`)

Identical replacement string as E4. Both anchors are unique within their containing string.

### E6.skill_manage_schema_desc (replace the description= argument of `SKILL_MANAGE_SCHEMA`)

```python
description=(
    "Create, edit, patch, delete, write_file, or remove_file a Hermes skill under "
    "~/.hermes/skills/<category>/<name>/. Use skills_list and skill_view to read; "
    "skill_manage to write. Follows the hermes-agent-skill-authoring validator rules."
)
```

### E7.skills_doc_section (replace the `## Agent-Managed Skills` heading + first paragraph)

```markdown
## Agent-Managed Skills

Hermes skills live under `~/.hermes/skills/<category>/<name>/SKILL.md` and are managed
with the `skill_manage` tool. Read skills with `skill_view(name=...)` or `skills_list()`.
The validator at `tools/skill_manager_tool.py:_validate_frontmatter` enforces the
frontmatter rules in `hermes-agent-skill-authoring`.
```

## Composition with the cap-raise site

- `--apply` (no Task E flag) → patches **only** `S1.cap`.
- `--apply --task-e-redirect` → patches `S1.cap` AND all 7 Task E sites. Pre-validation pass covers 8 sites; atomic write per file.
- `--apply --task-e-redirect --no-schema-redirect` → 6 Task E sites (E1–E5, E7). E6 is OPTIONAL.
- `--emit-migration-note` → emits `MIGRATION.hermes-patch.md` listing all 8 sites (or 7 if `--no-schema-redirect`) and a separate `MIGRATION.skill-port.md` is emitted by the migrated skill's own emit path (see `08-migration-note-format.md`).

## TDD test list

### Per-site anchor tests
- `test_e1_anchor_at_line_172` — fixture checkout; assert E1's `current_text` (the 8+ char `SKILLS_GUIDANCE = """` anchor) is at line 172 ± 2.
- `test_e2_anchor_at_line_143` — same for E2.
- `test_e3_anchor_at_line_1373` — same for E3.
- `test_e4_anchor_inside_skill_review_prompt` — locate the `_SKILL_REVIEW_PROMPT = """` opening, then `4. Use the Skill tool` substring at inner line ~100.
- `test_e5_anchor_inside_combined_review_prompt` — same for E5.
- `test_e6_anchor_in_skill_manage_schema` — locate `description="""Create, edit, patch` in `skill_manager_tool.py`.
- `test_e7_anchor_in_skills_md` — locate `## Agent-Managed Skills` heading in `website/docs/user-guide/features/skills.md`.

### Composition
- `test_default_no_task_e_touch` — `--apply` without `--task-e-redirect` leaves all 4 Task E files byte-identical (sha256 snapshot).
- `test_task_e_redirect_all_eight_sites` — `--apply --task-e-redirect` patches S1.cap + 7 Task E sites; `.patch.state.json` has 8 entries.
- `test_no_schema_redirect_skips_e6` — `--apply --task-e-redirect --no-schema-redirect` patches 7 sites (E1–E5, E7) and skips E6.
- `test_e6_optional_default_on` — `--apply --task-e-redirect` includes E6 unless `--no-schema-redirect`.

### Idempotency / drift
- `test_task_e_reapply_is_idempotent` — second `--apply --task-e-redirect` exits 0 with `OK: already patched / OK: már javítva` for all 8 sites.
- `test_task_e_drift_exits_2` — corrupt E4's anchor; run `--apply --task-e-redirect`; exit 2 with `LINE_DRIFT` naming E4.
- `test_task_e_force_only_retries_drifted` — pre-patch 7/8 sites; drift E3; `--force` re-applies only E3.

### Migration note
- `test_emit_migration_note_lists_all_sites` — `--emit-migration-note` produces a `MIGRATION.hermes-patch.md` table with exactly 8 rows (7 with `--no-schema-redirect`); the worktree's `MIGRATION.md` index links to it.

## Out of scope (explicit)

- `system_prompt.py` is NOT a patch site. It imports `MEMORY_GUIDANCE` and `SKILLS_GUIDANCE` from `prompt_builder` (per `agent/system_prompt.py:34, 38`) and is a CONSUMER, not a source. Patching it would be a no-op once `prompt_builder` is patched.
- The 60-char cosmetic preview sites in `tools/skills_tool.py:1509`, `hermes_cli/skills_hub.py:305`, `hermes_cli/mcp_config.py:447`, `hermes_cli/mcp_catalog.py:627`, `tools/browser_tool.py:3795` are NOT in the 7-site spec and are NOT patched. They are operator-TUI previews, not on the agent-injection path.

<!-- end of file: 135 lines (budget 250) -->
