<!-- title: Migrated skill-creator — Hermes-native standalone skill -->
<!-- scope: Sec 5.4 + Sec 6.D. Frontmatter, tool-name mapping, T3 inventory, nesting-guard helper, eval pipeline. -->
<!-- ACs covered: AC-4.1 .. AC-4.10 -->

# 07 — Migrated Skill-Creator (Hermes-native)

## Goal

Ship a Hermes-native port of the Anthropic `skill-creator` (pinned 2a40fd2e7c52207aa903bd33fc4c65716126966e) as a standalone skill under `src/hermes_skill_creator_plugin/skills/skill-creator/`. Every Claude-specific invocation is replaced per the T3 inventory below. Claude strengths (subagent split, eval pipeline, eval viewer) are preserved with documented Hermes equivalents.

## Frontmatter (the proposed block)

```yaml
---
name: skill-creator
description: |
  Use when authoring, validating, evaluating, or migrating a Hermes skill under
  ~/.hermes/skills/<category>/<name>/. Reads the hermes-agent-skill-authoring
  validator rules and applies them to the skill body, frontmatter, and supporting
  files. Runs the eval pipeline (run_eval -> aggregate_benchmark ->
  generate_report) and produces an HTML viewer for side-by-side review.
version: 0.1.0
author: kiscsicska
license: MIT
metadata:
  hermes:
    tags: [authoring, validation, eval, migration]
    related_skills: [hermes-agent-skill-authoring]  # in-repo only
---
```

Hard rules satisfied (per `tools/skill_manager_tool.py:_validate_frontmatter`):
- Name matches `^[a-z0-9][a-z0-9._-]*$`, len 13, <= 64.
- Description string-coerced, ~330 chars, <= 1024.
- Starts with `Use when …` (peer convention).
- File size target 8–15k chars; references/* for overflow.
- Body sections: `# Title → ## Overview → ## When to Use → body → ## Common Pitfalls → ## Verification Checklist`.

## Tool-name mapping (Anthropic → Hermes, lowercase)

Source of truth: `plans/_research/hermesSkillConventions.json` → `allowedAndForbiddenInvocations` (registry walk over `tools/registry.py` + grep of every `registry.register(name=...)` call in `tools/*.py`). The table below mirrors that list.

| Anthropic | Hermes | Source |
| --- | --- | --- |
| Skill (skill_manage) | `skill_manage` | `tools/skill_manager_tool.py:1109` |
| Skill (skill_view) | `skill_view` | `tools/skills_tool.py:1574,1609` |
| Skill (skills_list) | `skills_list` | `tools/skills_tool.py:1540+` |
| Read | `read_file` (auto-extracts .ipynb/.docx/.xlsx) | `tools/file_tools.py:1514` |
| Write | `write_file` | `tools/file_tools.py:1528` |
| Edit | `patch` (mode='replace' default with old_string/new_string; mode='patch' for V4A multi-file) | `tools/file_tools.py:1545` |
| Glob | `search_files` (target='files') | `tools/file_tools.py:1596` |
| Grep | `search_files` (target='content', ripgrep-backed) | `tools/file_tools.py:1596` |
| Bash (state mutations) | `terminal` | `tools/terminal_tool.py` |
| Bash (read-only inspection) | `read_terminal` | `tools/read_terminal_tool.py:83` |
| Bash (sandboxed Python) | `execute_code` | `tools/code_execution_tool.py:1838` |
| AskUserQuestion | `clarify` (also: `cronjob` for one-shot reminders, `todo` for multi-step todos) | `tools/clarify_tool.py` |
| Task / subagent | `delegate_task` (subagent dispatch); `mixture_of_agents` (MoA routing) | `tools/delegate_tool.py`; `tools/mixture_of_agents_tool.py` |
| MoA | `mixture_of_agents` | `tools/mixture_of_agents_tool.py` |
| WebSearch | `web_search` | `tools/web_tools.py:1367` |
| WebFetch | `web_extract` | `tools/web_tools.py` |
| TodoWrite | `todo` | `tools/todo_tool.py:301` |
| CronCreate / Delete / List | `cronjob` (action=add/del/list) | `tools/cronjob_tools.py:869` |
| NotebookEdit | `patch` (mode='patch') on the notebook file | `tools/file_tools.py:1545` |
| Excel / Word reading (Claude Read variants) | `read_file` (auto-extracts .xlsx/.docx) | `tools/file_tools.py:1515` |
| Image content in prompt (vision) | `vision_analyze` | `tools/vision_tools.py` |
| Memory / persistent notes (no Claude equiv) | `memory` | `tools/memory_tool.py:796` |
| Process management (no Claude equiv) | `process` | `tools/process_registry.py:1667` |
| Long-running output readback | `read_terminal` | `tools/read_terminal_tool.py:83` |
| Image generation (no Claude equiv) | `image_generate` | `tools/image_generation_tool.py:1172` |
| Video generation / analysis | `video_generate`, `video_analyze` | `tools/video_generation_tool.py:553` |
| Speech synthesis / transcription | `text_to_speech`, `voice_mode` | (respective `tts` / `voice` tools) |
| Browser automation (browser_* family) | `browser_navigate`, `browser_click`, `browser_type`, `browser_snapshot`, `browser_console`, `browser_back`, `browser_scroll`, `browser_press`, `browser_vision`, `browser_get_images`, `browser_dialog`, `browser_cdp` | `tools/browser_tool.py`, `tools/browser_dialog_tool.py`, `tools/browser_cdp_tool.py` |
| Kanban workflow | `kanban_create`, `kanban_list`, `kanban_show`, `kanban_comment`, `kanban_link`, `kanban_block`, `kanban_unblock`, `kanban_complete`, `kanban_heartbeat` | `tools/kanban_tools.py` |
| Cross-session search | `session_search` | `tools/session_search_tool.py` |
| Cross-user messaging | `send_message` (also: `discord`, `discord_admin`, `x_search`, `yuanbao_*`, `feishu_*`, `homeassistant ha_*`, `computer_use`) | `tools/send_message_tool.py:1905`; respective `*_tool.py` |
| EnterPlanMode / ExitPlanMode | (forbidden; use prose + `delegate_task` for dispatch) | n/a |

**Selection rules** (when one Anthropic tool maps to multiple Hermes tools, pick by intent):
- `Bash` → state mutations: `terminal`; read-only inspection: `read_terminal`; code execution: `execute_code`.
- `Task` (one-off subagent) → `delegate_task`; multi-agent ensemble: `mixture_of_agents`.
- `AskUserQuestion` → live clarification: `clarify`; deferred: `cronjob`; multi-step: `todo`.
- `WebSearch` / `WebFetch` → `web_search` for query-driven discovery; `web_extract` for fetching+extracting a known URL.

The migrated skill's body teaches the agent the lowercase names and uses `tool_name.lower() in (...)` matching.

The migrated skill's body teaches the agent the lowercase names and uses `tool_name.lower() in (...)` matching.

## T3 inventory (per-binding replacement table)

| path:line | claude-binding | hermes-binding | test-id | migration-note-line |
| --- | --- | --- | --- | --- |
| `scripts/improve_description.py:26` | `subprocess.run(["claude", "-p", "--output-format", "text", ...])` | `subprocess.run(["hermes", "-p", "--output-format", "text", ...])` | `T3.001` | MN.skill-port.1 |
| `scripts/improve_description.py:33` | `env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` | `env = hermes_subprocess_env()` (helper) | `T3.002` | MN.skill-port.2 |
| `scripts/run_eval.py:71-87` | `claude -p --output-format stream-json --verbose ...` | `hermes -p --output-format stream-json --verbose ...` | `T3.003` | MN.skill-port.3 |
| `scripts/run_eval.py:82` | `env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` | `env = hermes_subprocess_env()` returns env minus the guard vars | `T3.004` | MN.skill-port.4 |
| `scripts/run_eval.py:46` | Fabricates `.claude/commands/<target>.md` to register eval target | Writes `~/.hermes/skills/<cat>/<target>/SKILL.md` to register eval target (Hermes-native; legacy `.claude/commands/` mirrored for back-compat) | `T3.005` | MN.skill-port.5 |
| `scripts/run_eval.py:137,156` | Tool-name matching: `if tool_name in ("Skill", "Read"):` | `if tool_name.lower() in ("skill", "read"):` (Hermes names are lowercase) | `T3.011` | MN.skill-port.11 |
| `SKILL.md:455` | `claude.ai` URL reference | `nousresearch.com/hermes` (or remove the URL) | `T3.007` | MN.skill-port.7 |
| `SKILL.md:388` | `## Cowork-Specific Instructions` section header | Removed (Hermes has no Cowork surface; replaced with a Hermes-headless section) | `T3.008` | MN.skill-port.8 |
| `SKILL.md:483` | `If you're in Cowork, please specifically put "Create evals JSON..."` (TodoList fallback) | Removed | `T3.009` | MN.skill-port.9 |
| `SKILL.md:247` | `if not webbrowser.open(...)` (Cowork browser auto-open) | Removed (Hermes serves the HTML viewer via `file://` only) | `T3.010` | MN.skill-port.10 |
| `agents/grader.md:1` | `# Grader Agent` (Anthropic subagent YAML) | `# Grader Subagent` + `agent_name` registration in Hermes's subagent dispatch | `T3.012` | MN.skill-port.12 |
| `agents/analyzer.md:1` | `# Post-hoc Analyzer Agent` | `# Post-hoc Analyzer Subagent` | `T3.013` | MN.skill-port.13 |
| `agents/comparator.md:1` | `# Blind Comparator Agent` | `# Blind Comparator Subagent` | `T3.014` | MN.skill-port.14 |
| `eval-viewer/generate_review.py` | (host-agnostic per JSON evidence; no Claude binding) | preserved unchanged (stdlib HTTP server) | `T3.015` | MN.skill-port.15 |
| `scripts/run_loop.py:252` | `--model claude-...` flag (Anthropic model id) | `--model hermes-...` (Hermes model id; or omit, model selection is a session config) | `T3.006` | MN.skill-port.6 |
| `scripts/run_loop.py:1` | module docstring references `claude -p` (orchestrator) | module docstring rewritten to reference `hermes -p` (Hermes orchestrator) | `T3.016` | MN.skill-port.16 |
| `scripts/run_loop.py:TBD` | any other `claude`/`CLAUDECODE` invocations in the loop body | replaced per Hermes equivalent (Phase 5 re-derive from vendored source) | `T3.017` | MN.skill-port.17 |
| `scripts/improve_description.py:44,162` | `RuntimeError(f"claude -p exited {rc}\n…")` + comment-only `claude -p` rename | `RuntimeError(f"hermes -p exited {rc}\n…")` + comment-only `hermes -p` rename | `T3.018` | MN.skill-port.18 |

> **Sorszám-re-derive lábjegyzet**: every `path:line` in this table is the line that matches the Claude-specific binding in the pinned vendored source at `research/anthropic-skill-creator-original/skills/skill-creator/` (pinned 2a40fd2e7c52207aa903bd33fc4c65716126966e). At Phase 5 / Task D implementation time, Script #1's `--check` + a one-shot `grep -nE "claude|CLAUDECODE" <file>` re-derives every row's anchor line from the vendored source; rows that drift are flagged in `.patch.rejected` with `LINE_DRIFT` and a `migration-note-line` rewrite. The `:TBD` rows are reserved for bindings surfaced by the Phase 5 re-derive but not yet enumerated (T3.017 placeholder row covers any new findings). The mapping of T3.001–T3.018 to the `claudeSpecificInvocations[]` entries in `plans/_research/anthropicCreator.json` (50 rows) is the single source of truth for the binding set; this table is the Hermes-side manifest, not the upstream enumeration.

## hermes_subprocess_env() helper (single source of truth)

```python
# src/hermes_skill_creator_plugin/_subprocess.py
import os

# Pin: the Hermes nesting-guard env var name. See 12-risks-and-open-questions Q1.
NESTING_GUARD_VAR = "HERMES_SESSION"
# Pin: the legacy Anthropic nesting-guard env var. Must also be stripped
# so a migrated `hermes -p` subprocess can run cleanly when the parent
# process is itself a Claude/Anthropic session (e.g. during Phase 5 eval).
_LEGACY_GUARD_VARS: frozenset[str] = frozenset({NESTING_GUARD_VAR, "CLAUDECODE"})

def hermes_subprocess_env() -> dict[str, str]:
    """Return os.environ minus the nesting-guard vars (Hermes + legacy Claude).

    Strips BOTH the current Hermes guard (`HERMES_SESSION`) and the legacy
    Anthropic guard (`CLAUDECODE`) so a migrated `hermes -p` subprocess can
    run cleanly even when the parent process is itself a Claude/Anthropic
    session (e.g. during the Phase 5 eval pipeline). Stripped ONLY for the
    subprocess; the parent process keeps the vars set so Hermes's own
    nesting guard sees the parent and refuses the inner call unless the
    child explicitly un-nests via this helper.
    """
    return {k: v for k, v in os.environ.items() if k not in _LEGACY_GUARD_VARS}
```

The migrated `scripts/run_eval.py` and `scripts/improve_description.py` import this helper and use it as `env=hermes_subprocess_env()`. They NEVER `os.environ.pop` the var in the parent process.

## Eval pipeline (Claude strength preserved)

- `scripts/run_eval.py` — invokes `hermes -p` per eval case; collects NDJSON events.
- `scripts/aggregate_benchmark.py` — folds events into per-case metrics.
- `scripts/generate_report.py` — writes `report.md` + `feedback.json` (the viewer's data file).
- `scripts/improve_description.py` — invokes `hermes -p` to propose a new SKILL.md description.
- `scripts/quick_validate.py` — re-runs `_validate_frontmatter` from `tools/skill_manager_tool.py` (imported; no shelling out).
- `scripts/package_skill.py` — tars up the skill dir for hub install.
- `scripts/utils.py` — shared helpers.

The Hermes event-shape translator (T3.011) is the load-bearing piece. Until Q3 is resolved, the translator is implemented as an adapter that reads the Hermes NDJSON event and emits an Anthropic-shaped dict to the rest of the pipeline, so the rest of the pipeline needs no change. Once Q3 is confirmed by reading `~/.hermes/hermes-agent/hermes_cli/streaming/`, the adapter is either (a) confirmed correct, or (b) updated to the new shape.

## Strength-preservation matrix

| Strength | Anthropic artifact | Hermes equivalent | Acceptance criterion |
| --- | --- | --- | --- |
| Subagent split | `agents/{grader,analyzer,comparator}.md` (YAML frontmatter defining subagent roles) | `agent_name` registration with Hermes's `delegate_task` | `test_subagent_registration_matches_anthropic_roles` — for each agent, the registered `description` and `toolset` match the Anthropic agent's role. |
| Eval pipeline | `scripts/{run_eval, aggregate_benchmark, generate_report, ...}.py` (Anthropic-shaped NDJSON) | same scripts, Hermes-CLI invocation, adapter for event shape | `test_eval_pipeline_end_to_end` — run a 2-case eval against a fixture skill; assert `report.md` and `feedback.json` are produced with the expected schema. |
| Eval viewer | `eval-viewer/{generate_review.py, viewer.html}` (static HTML+JS, `webbrowser.open`) | `generate_review.py` writes `feedback.json` next to `viewer.html`; opened via `file://` URL emitted in the report | `test_eval_viewer_static_open` — `generate_review.py --static` writes both files; `viewer.html` references `feedback.json` via relative path; integration test loads the HTML in a headless browser (or a HTML parser) and asserts the JS reads `feedback.json` correctly. |

## TDD test list

### Frontmatter
- `test_frontmatter_passes_hermes_validator` — run `_validate_frontmatter` from `tools/skill_manager_tool.py` against the migrated SKILL.md; assert exit 0 / no errors.
- `test_description_under_active_cap` — if cap is 60, description len <= 60; if cap is 1024, description len <= 1024. Detected via the same static-AST read the plugin uses (see 03-plugin-spec.md).
- `test_description_starts_with_use_when` — peer convention.
- `test_metadata_hermes_tags_present` — `metadata.hermes.tags == [authoring, validation, eval, migration]`.
- `test_metadata_hermes_related_skills_in_repo` — every entry resolves to an in-repo skill under the worktree.

### Tool-name compliance
- `test_no_uppercase_tool_names_in_body_outside_fences` — strip code-fence blocks from SKILL.md; assert no matches for `\b(Read|Write|Edit|Glob|Grep|Bash|Task|Skill|AskUserQuestion|WebSearch|WebFetch|TodoWrite)\b`.
- `test_lowercase_tool_names_present` — assert at least one occurrence each of `skill_manage`, `skill_view`, `skills_list`, `read_file`, `write_file`, `patch`, `search_files`, `terminal`, `delegate_task`, `clarify`, `web_search`, `web_extract`, `todo`, `cronjob`.
- `test_no_claude_invocations_remain` — `grep -rE "\bclaude\b"` over the migrated skill tree; zero hits in code/commands, allowed mentions only in `MIGRATION.skill-port.md` (provenance) and bilingual advisories that name Anthropic by purpose ("Anthropic skill-creator" is allowed in the description).

### T3 inventory: per-binding tests (one test per row)
- `test_T3_001_to_T3_015` — for each row, the migrated file (a) does NOT contain the forbidden binding string, (b) DOES contain the Hermes equivalent.

### Nesting-guard helper
- `test_hermes_subprocess_env_strips_guard` — set `HERMES_SESSION=foo`; assert `hermes_subprocess_env()` does not include the key.
- `test_hermes_subprocess_env_preserves_other_vars` — assert PATH, HOME, etc. are preserved.
- `test_run_eval_unnests_hermes_guard` — pre-set `HERMES_SESSION`; run a dry-run of `run_eval.py`; assert the subprocess env passed to `subprocess.run` does NOT include `HERMES_SESSION`.
- `test_run_eval_restores_hermes_guard_on_exit` — assert `os.environ['HERMES_SESSION']` is unchanged in the parent after the script exits.
- `test_run_eval_no_op_when_guard_unset` — `HERMES_SESSION` unset; the helper is a no-op copy; exit 0.
- `test_improve_description_unnests_hermes_guard` — same matrix for `improve_description.py`.
- `test_helper_is_single_source_of_truth` — `grep -rE "HERMES_SESSION" src/hermes_skill_creator_plugin/` returns exactly one match (the constant in `_subprocess.py`).

### Eval pipeline + viewer
- `test_eval_pipeline_end_to_end` — 2-case eval; assert `report.md` + `feedback.json` produced.
- `test_event_shape_adapter_handles_known_shapes` — parametrize over the candidate Hermes event shapes; assert the adapter normalizes each into the Anthropic-shaped dict.
- `test_aggregate_benchmark_parses_hermes_stream_json` — feed a fixture Hermes NDJSON; assert the aggregator produces the same metrics as the Anthropic version.
- `test_eval_viewer_static_open` — `generate_review.py --static` writes both files; assert the HTML's JS reads `feedback.json` via a relative path that resolves under the same dir.

### Strength preservation
- `test_subagent_registration_matches_anthropic_roles` — for each `agents/*.md`, the registered `agent_name`, `description`, and `toolset` match the Anthropic file's role.
- `test_subagent_dispatch_via_delegate_task` — call `delegate_task(agent_name="grader", ...)` in a fixture; assert the dispatcher routes to the grader agent.

### Bilingual + CLI
- `test_help_is_bilingual` — the eval scripts' `--help` is bilingual.
- `test_console_log_lines_match_bilingual_regex` — AST-grep every `print`/`logger.*` in `scripts/`; assert format string matches `^\[en\] .+ / \[hu\] .+$`.

<!-- end of file: 165 lines (budget 450) -->
