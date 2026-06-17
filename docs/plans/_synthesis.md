# Research Brief — Skill-Creator Migration + Task E Patch Surface

## Truth-anchored Findings

### T1. The 60-char skill-description truncation site (authoritative)

- **Single authoritative site**: `agent/skill_utils.py:647-655` — function `extract_skill_description(frontmatter)` does the cap. Body at lines 653-654: `if len(desc) > 60: return desc[:57] + "..."`. Confirmed via read-only inspection.
- **Single call site**: `agent/prompt_builder.py:1090` inside `_parse_skill_file` (def at line 1070), return tuple `True, frontmatter, extract_skill_description(frontmatter)`. Imported at `prompt_builder.py:20`. Confirmed: only one call in the entire install.
- **Render path**: consumed by `build_snapshot_entry` → `skills_by_category` → `index_lines.append(f"    - {name}: {desc}")` at `prompt_builder.py:1352` → injected into the system prompt as the `<available_skills>` block by `build_skills_system_prompt()` (caller of the lines at `prompt_builder.py:1377-1380`).
- **What "60 chars" means exactly**: output is `len(desc[:57]) + len("...")` = 60 code points. Python `str[:57]` slices on code points, NOT grapheme clusters — ZWJ emoji and combining marks can be split mid-grapheme. This is a **soft prompt-budgeting heuristic, not a security boundary**; the function performs zero sanitization (no newline/control-char strip, no allowlist).
- **Distinct, unrelated 1024-char cap**: `tools/skills_tool.py:95` declares `MAX_DESCRIPTION_LENGTH = 1024`, applied at `skills_tool.py:655-656` and `:810-811`. This is the *validator-and-tools* cap used by `skills_list` / `skill_view` when the LLM invokes them mid-conversation. It is NOT the one that limits the auto-injected system-prompt index. The 60-char `extract_skill_description` is the lower, hidden layer.
- **Cosmetic 60-char slices** exist at `tools/skills_tool.py:1509`, `hermes_cli/skills_hub.py:305`, `hermes_cli/mcp_config.py:447`, `hermes_cli/mcp_catalog.py:627`, `tools/browser_tool.py:3795` — all CLI/operator previews, never on the agent-injection path. Not patch sites for the description-truncation feature.

### T2. Hermes plugin authoring model (official spec, no truncation hook exists)

- **PluginContext surface** (read-only verified, `hermes_cli/plugins.py:290-1090`) exposes only `register_*` methods: `register_tool`, `register_hook`, `register_middleware`, `register_command`, `register_cli_command`, `register_skill`, `register_web_search_provider`, `register_browser_provider`, `register_image_gen_provider`, `register_video_gen_provider`, `register_tts_provider`, `register_transcription_provider`, `register_dashboard_auth_provider`, `register_context_engine`, `register_platform`, `register_slack_action_handler`, `register_auxiliary_task`, plus `llm` (property) and `inject_message`. No `patch_constant`, `mutate_module`, or `transform_skill_index` method exists.
- **Hook reference** (per `website/docs/guides/build-a-hermes-plugin.md`): 8 lifecycle hooks — `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`, `on_session_finalize`, `on_session_end`. None applies to skill-index loading.
- **Required manifest fields** for a general plugin: `name`, `version`, `description` (all required); `provides_tools`, `provides_hooks` (or `hooks`), `requires_env`, `author`, `kind`, plus kind-specific provider lists (`provides_web_providers`, `provides_browser_providers`, etc.). Discovery roots: `~/.hermes/plugins/<name>/`, `<hermes-agent>/plugins/<name>/`, Python entry points under group `hermes_agent.plugins`.
- **Conclusion on patching the 60/1024 char limit from a plugin**: there is no clean plugin hook. The 60-char rule is a documentation hardline (`AGENTS.md:859`, `CONTRIBUTING.md:520`); the 1024-char value is a Python constant in `tools/skills_tool.py:95` and `tools/skill_manager_tool.py:112`. The supported way to change the latter is a controlled source edit (the patch script Script #1 will perform against `~/.hermes/hermes-agent`). A `pre_llm_call` hook can advise the model but does not change the constant.

### T3. Anthropic skill-creator (pinned upstream)

- **Pinned commit**: `2a40fd2e7c52207aa903bd33fc4c65716126966e` on `anthropics/claude-plugins-official`, PR #1523, "skill-creator: sync from anthropics/skills (drop ANTHROPIC_API_KEY requirement)". Verified via GitHub API; vendored copy at `/Users/kiscsicska/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/` is byte-identical to the worktree staging copy at `research/anthropic-skill-creator-original/`. `UPSTREAM_COMMIT.txt` in the worktree records the SHA.
- **File tree** (20 files): 1 root `README.md`, 1 root `LICENSE`, 1 `.claude-plugin/plugin.json`, 1 `skills/skill-creator/SKILL.md`, 1 `skills/skill-creator/LICENSE.txt`, 3 `agents/{analyzer,comparator,grader}.md`, 1 `assets/eval_review.html`, 2 `eval-viewer/{generate_review.py,viewer.html}`, 1 `references/schemas.md`, 9 `scripts/{__init__,aggregate_benchmark,generate_report,improve_description,package_skill,quick_validate,run_eval,run_loop,utils}.py`.
- **Highest-risk Claude bindings** (all in scripts that shell out):
  - `scripts/improve_description.py:26` — `cmd = ["claude", "-p", "--output-format", "text"]`
  - `scripts/improve_description.py:32-33` — `env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` to allow nesting
  - `scripts/run_eval.py:23-46` — `find_project_root()` looks for `.claude/`
  - `scripts/run_eval.py:71` — `cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]`
  - `scripts/run_eval.py:80-82` — strips `CLAUDECODE` env var
  - `scripts/run_eval.py:137,156` — tool-name matches `if tool_name in ("Skill", "Read"):` (PascalCase)
- **Hermes tool-name replacement map** (verified against `tools/registry.py` and `tools/*.py`):
  - `Skill` → `skill_manage` (writes) and `skill_view` / `skills_list` (reads)
  - `Read` → `read_file`
  - `Write` → `write_file`
  - `Edit` → `patch` (mode='replace' default)
  - `Glob` / `Grep` → `search_files` (target='files' or 'content')
  - `Bash` → `terminal` (state mutations) / `read_terminal` (inspection) / `execute_code` (sandbox)
  - `AskUserQuestion` → `clarify`
  - `Task` (subagent) → `delegate_task` / `mixture_of_agents`
  - `WebSearch` → `web_search`; `WebFetch` → `web_extract`
  - `TodoWrite` → `todo`
  - `CronCreate` / `CronDelete` / `CronList` → `cronjob` (action dispatch)
  - `EnterPlanMode` / `ExitPlanMode` (Claude-only) — no Hermes equivalent; use `delegate_task` + prose
- **Frontmatter allowed keys** (Claude): `{name, description, license, allowed-tools, metadata, compatibility}`. Hermes adds `model`, `when_to_use`, `platforms`, `environments`, `prerequisites.{env_vars,commands}`, `required_environment_variables`, `required_credential_files`, `setup.{help,collect_secrets}`, `metadata.hermes.{tags,related_skills,requires_toolsets,fallback_for_toolsets,requires_tools,fallback_for_tools,config}`. Migration validator must allow both sets.
- **Env-var nesting guard**: Claude uses `CLAUDECODE`; Hermes equivalent is TBD (likely `HERMES_SESSION` or `HERMES_AGENT`). Must be confirmed against the Hermes harness before Script #1 lands.

### T4. Hermes profile system

- **Layout**: default profile is `~/.hermes/` (zero-migration compat); named profiles live at `~/.hermes/profiles/<id>/` (full self-contained HERMES_HOME).
- **Bootstrap subdirs** (`hermes_cli/profiles.py:39-53 _PROFILE_DIRS`): `memories, sessions, skills, skins, logs, plans, workspace, cron, home`. **NOTE: there is NO `gateway/` subdir**; gateway artifacts live as flat files in the profile root (e.g. `gateway.pid`).
- **Per-profile metadata file** `~/.hermes/profiles/<id>/profile.yaml` holds `{description: str, description_auto: bool}` (read/written by `profiles.read_profile_meta()` / `write_profile_meta()` at lines 654-709). Separate from the ~5000-line `config.yaml` because profile routing metadata is small and frequently re-read by the kanban decomposer.
- **Bundled-skill opt-out marker**: `~/.hermes/profiles/<id>/.no-bundled-skills` (constant `NO_BUNDLED_SKILLS_MARKER` at `profiles.py:133`).
- **Sticky active profile**: `~/.hermes/active_profile` (single-line text; empty/missing → "default"). Helper at `profiles.py:269-271` (`_get_active_profile_path`).
- **Wrapper alias scripts**: `~/.local/bin/<id>` (POSIX) or `~/.local/bin/<id>.bat` (Windows); POSIX body is `#!/bin/sh\nexec hermes -p <id> "$@"\n`. Created by `profiles.create_wrapper_script` (`profiles.py:394-431`).
- **Resolution precedence** (from `_apply_profile_override` in `hermes_cli/main.py:325-510`, runs BEFORE any module import): (1) explicit `--profile` / `-p` flag validated against `^[a-z0-9][a-z0-9_-]{0,63}$`; (2) `HERMES_HOME` env var only if its parent is `profiles/`; (3) sticky `~/.hermes/active_profile` (S6-supervised children skip this); (4) platform-native `~/.hermes`.
- **Skill enable/disable is a NEGATIVE list** stored under `config["skills"]["disabled"]: List[str]` plus optional `config["skills"]["platform_disabled"][<platform>]: List[str]`. **No per-skill `enable_skill` / `disable_skill` boolean, no `skills_enabled` set, no `hermes skill enable|disable` CLI verb.** A skill is enabled iff its name is not in the union of the global list and the active platform's list. CLI mutator is `hermes skills config` (interactive curses TUI) backed by `skills_config.get_disabled_skills` / `save_disabled_skills`.

### T5. Hermes skill conventions (for the migrated skill-creator)

- **Directory layout**: `~/.hermes/skills/<category>/<skill-name>/SKILL.md` with optional `{references, templates, scripts, assets}/` subdirs. Canonical filename is uppercase `SKILL.md` (case-sensitive).
- **Frontmatter validation** (machine-checked in `tools/skill_manager_tool.py:_validate_frontmatter`):
  - file starts at byte 0 with `---` (no BOM, no leading blank line); closes with `\n---\n`
  - YAML parses cleanly; top-level must be a mapping
  - `name` required, `^[a-z0-9][a-z0-9._-]*$`, `len(name) <= 64`
  - `description` required, `len(description) <= 1024` (this is the validator cap — already 1024)
  - non-empty body after closing `---`
  - total content `<= 100,000` chars; per supporting file `<= 1,048,576` bytes
  - supporting files must be under `{references, templates, scripts, assets}`; no `..` traversal
- **Soft rules** (peer-matched, not enforced): `version`, `author`, `license` at top level; `metadata.hermes.tags` and `metadata.hermes.related_skills` (in-repo only — user-local refs break for fresh clones); description starts with "Use when …"; body sections `# Title → ## Overview → ## When to Use → … → ## Common Pitfalls → ## Verification Checklist`; total file 8–15k chars (split into `references/*.md` if > 20k); choose closest existing top-level category.
- **Skill loader caches** at session start — newly created skills not visible in current session; verify in fresh session or `skill_view` with explicit path. Pinned skills can be patched/edited but not deleted. The `skills.guard_agent_created=true` gate runs `tools.skills_guard.py` and can roll back agent-initiated create/edit/patch/delete/write_file/remove_file.

### T6. Task E patch surface (reconciled)

- **Spec source**: `docs/maybe-patch-points.md` (worktree root).
- **Total patch sites: 7 (not 8).** Files: `agent/prompt_builder.py` (3), `agent/background_review.py` (2), `tools/skill_manager_tool.py` (1, optional), `website/docs/user-guide/features/skills.md` (1). `agent/system_prompt.py` is NOT a patch site — it only imports/re-exports `MEMORY_GUIDANCE` and `SKILLS_GUIDANCE` from `prompt_builder.py`; editing the canonical constants in `prompt_builder.py` propagates automatically.
- **Per-site replacement text** (verbatim from independent sweep ∩ spec):

  1. `agent/prompt_builder.py:172` `SKILLS_GUIDANCE` — insert the new-skill redirect between the existing "save … with skill_manage" line and the "patch it immediately with skill_manage(action='patch')" line. Rule: check the available-skills index; if `skill-creator` is installed, load it with `skill_view(name='skill-creator')` and follow its authoring/validation guidance; then persist with `skill_manage(action='create')`. If absent, fall back to built-in class-level rules; never auto-install or fetch. Do NOT force `skill-creator` for small targeted patches.
  2. `agent/prompt_builder.py:143` `MEMORY_GUIDANCE` — mirror the SKILLS_GUIDANCE redirect at the "save it as a skill with the skill tool" line. Wording must stay semantically synchronized to avoid contradictory cues.
  3. `agent/prompt_builder.py:~1373` `build_skills_system_prompt` result string — co-locate the new-skill redirect next to the existing "After difficult/iterative tasks, offer to save as a skill" line in the rendered skills-index block. This is the third foreground surface (shipped in every system prompt with skills loaded).
  4. `agent/background_review.py:45` `_SKILL_REVIEW_PROMPT` option (4) at line ~100 — insert the redirect immediately before the actual `skill_manage(action='create')` step: call `skills_list`; if `skill-creator` returned, load it with `skill_view(name='skill-creator')` and follow its authoring/validation workflow; then create with `skill_manage(action='create')`. If absent, continue with built-in class-level rules. Do not install, fetch, or network-look-up `skill-creator` during background review — absence must not block creation. Preserve (1)/(2)/(3)/(4) preference order, protected-skills rule, do-not-capture guard rails.
  5. `agent/background_review.py:150` `_COMBINED_REVIEW_PROMPT` option (4) at line ~188 — apply the identical redirect as in `_SKILL_REVIEW_PROMPT`. Combined prompt must behave identically for new-skill creation; prefer extracting one shared string constant for the rule text. Do not alter `spawn_background_review_thread` selection logic (must continue selecting `_COMBINED_REVIEW_PROMPT` / `_MEMORY_REVIEW_PROMPT` / `_SKILL_REVIEW_PROMPT` based on `review_memory` / `review_skills`).
  6. `tools/skill_manager_tool.py:~992` `skill_manage` schema description — **OPTIONAL** clarification: append "skill-creator, when installed, provides authoring guidance only. Use skill_manage to persist all skill files." Do NOT import, install, invoke, or depend on skill-creator from `skill_manage`.
  7. `website/docs/user-guide/features/skills.md` "Agent-Managed Skills" section (~line 378) — clarify: (a) Hermes still creates/updates skills through `skill_manage`; (b) before a new skill is created, prompt guidance may load installed `skill-creator`; (c) `skill-creator` is optional and installable from a hub; (d) absence does not disable automatic skill creation; (e) background review must never auto-install it. Do NOT describe `skill-creator` as bundled or mandatory.
- **Synchronization contract**: the rule text in sites 1, 2, 3, 4, 5 should share wording (preferably a single constant in `prompt_builder.py`); site 6 is documentation, site 7 is user-facing prose.

---

## Disputed Findings (with refuter counter-evidence)

### D1. The 60-char truncation "happens at" both skill_utils.py:647 AND prompt_builder.py:1090
- **Refuter verdict**: PARTIALLY REFUTED.
- **Counter-evidence**: `prompt_builder.py:1090` is a pure delegation call `return True, frontmatter, extract_skill_description(frontmatter)` — no local slicing or length check. Truncation logic lives only at `skill_utils.py:653-654`. Listing `prompt_builder.py:1090` as a "co-location of the truncation" is misleading; it is the call site, not the implementation site. The truncation site is `skill_utils.py:647-655` only.
- **Re-research needed**: **no** (file/line citations and arithmetic confirmed end-to-end; the dispute is framing, not fact).

### D2. GitHub issue `NousResearch/hermes-agent#46005` confirms 57+3 truncation as authoritative
- **Refuter verdict**: REFUTED (unverifiable from this read-only environment).
- **Counter-evidence**: The issue number cannot be confirmed via network in the read-only scope. The truncation behaviour itself is independently verified by reading `agent/skill_utils.py:653-654`. The issue title preview ("Skill description YAML bug (15 files) + 57-char truncation too restrictive for CJK") is plausible but not independently confirmed.
- **Re-research needed**: **no** (claim is corroborative, not load-bearing — the truncation fact is verified by source).

### D3. Anthropic skill-creator has "50 Claude-specific invocations"
- **Refuter verdict**: REFUTED.
- **Counter-evidence**: case-insensitive `grep -ci "claude"` across the vendored skill-creator tree yields 52 lines (SKILL.md=19, improve_description.py=16, run_eval.py=13, viewer.html=2, generate_report.py=1, schemas.md=1). The literal "50" appears in SKILL.md only 2 times, both as part of unrelated numbers (e.g. "60% train / 40% test"). A strict "invocation" reading (counting `claude -p` calls + product-handle mentions like Claude Code / Claude.ai) yields ≈6–10 in SKILL.md plus the two Python scripts' CLI calls — substantially fewer than 50. Additionally, the marketplace install is not a git checkout (no `.git/` present) so the SHA pin is recorded only in the worktree's `UPSTREAM_COMMIT.txt`, not in the marketplace manifest.
- **Re-research needed**: **no** (figure is decorative — the migration count should be derived from the explicit list of Claude-specific bindings in the T3 section, not from a number).

### D4. `hermes_cli.config.load_config(path=...)` and `save_config(config, path=...)` accept a `path=` kwarg
- **Refuter verdict**: REFUTED (both signatures).
- **Counter-evidence**:
  - `hermes_cli/config.py:5266` `def load_config() -> Dict[str, Any]:` — no `path=` parameter. Internally calls `get_config_path()` (HERMES_HOME-anchored).
  - `hermes_cli/config.py:5528` `def save_config(config: Dict[str, Any]):` — no `path=` parameter. Writes to `get_config_path()` via `atomic_yaml_write`.
  - The correct path-aware pattern (already used in `profiles.py:472-481` `_migrate_profile_config_if_outdated`) is `hermes_constants.set_hermes_home_override(str(profile_dir))` + `load_config()` / `save_config()` under a context manager, then `reset_hermes_home_override()`.
- **Impact on Script #2 (Task C)**: any code that passes `path=` will raise `TypeError`. Script #2 must use the `set_hermes_home_override` pattern.
- **Re-research needed**: **no** — flagged in T4 (correct pattern) and the Inputs Ready section.

### D5. `agent.skill_utils.get_disabled_skills(config, platform)` exists
- **Refuter verdict**: REFUTED (wrong module + wrong name).
- **Counter-evidence**:
  - `agent/skill_utils.py:318` defines `get_disabled_skill_names(platform: str | None = None) -> Set[str]`. It takes NO config dict and reads from disk via `_load_raw_config()`. **There is NO `get_disabled_skills` in `agent.skill_utils`.**
  - `get_disabled_skills(config, platform)` exists in `hermes_cli/skills_config.py:27-42` — different module.
- **Impact on Script #2**: `agent.skill_utils.get_disabled_skills(config, platform)` will raise `AttributeError`. Use `agent.skill_utils.get_disabled_skill_names(platform)` (the runtime resolver) for the read path, and `hermes_cli.skills_config.get_disabled_skills(config, platform)` (the mutator) under `set_hermes_home_override` for the read-config-then-flip path.
- **Re-research needed**: **no** — corrected in T4 and Inputs Ready.

### D6. Each profile has a `gateway/` subdirectory
- **Refuter verdict**: REFUTED.
- **Counter-evidence**: `hermes_cli/profiles.py:39-53 _PROFILE_DIRS` lists `memories, sessions, skills, skins, logs, plans, workspace, cron, home` — **no `gateway/`**. The docstring at line 5 mentions "gateway" as a loose narrative, but it is not bootstrapped. Gateway artifacts live as flat files (e.g. `gateway.pid`) in the profile root.
- **Impact on Script #2**: an audit that walks `<profile>/gateway/` will silently miss the actual gateway state. Use `<profile>/gateway.pid` (or whatever flat-file shape the runtime uses) as the gateway-state source.
- **Re-research needed**: **no** — corrected in T4.

### D7. `do_install(identifier, name_override=..., skip_confirm=True, force=True, invalidate_cache=True)` — signature works as shown
- **Refuter verdict**: PARTIALLY REFUTED.
- **Counter-evidence**: `hermes_cli/skills_hub.py:478` actual signature: `def do_install(identifier: str, category: str = "", force: bool = False, console=None, skip_confirm: bool = False, invalidate_cache: bool = True, name_override: str = "")`. The kwargs exist but `name_override` is the LAST param, not positionally mixed; **and `do_install` at `skills_hub.py:498` calls `ensure_hub_dirs()` which uses `get_hermes_home()` from hermes_constants** — it does NOT respect a per-profile `set_hermes_home_override` from the caller unless `HERMES_HOME` is also set in `os.environ` BEFORE the call. The "in-process call already respects it" framing is wrong.
- **Impact on Script #2**: when installing into a non-default profile, set `os.environ['HERMES_HOME'] = str(profile_dir)` (or wrap the call in `set_hermes_home_override` AND ensure the env var is mirrored). Otherwise the install lands in the global `~/.hermes` regardless of which profile is targeted.
- **Re-research needed**: **no** — corrected in Inputs Ready (Script #2 audit/flip spec).

### D8. Task E final candidate set is "8 sites across 5 files including `agent/system_prompt.py`"
- **Refuter verdict**: REFUTED.
- **Counter-evidence**: spec `docs/maybe-patch-points.md` enumerates **7 sites across 4 files**: prompt_builder.py (3), background_review.py (2), skill_manager_tool.py (1, optional), website/docs/user-guide/features/skills.md (1). `agent/system_prompt.py` is a downstream consumer — it imports `MEMORY_GUIDANCE` and `SKILLS_GUIDANCE` from `prompt_builder.py` at lines 34 and 38 and re-appends them to `tool_guidance` at lines 117/121/207; it contains no canonical definition and no spec-anchored edit point. Adding the rule to system_prompt.py would duplicate site 3 (build_skills_system_prompt) and violate the spec's "avoid contradictory duplicate wording" instruction.
- **Re-research needed**: **no** — reconciled count is 7 sites across 4 files (T6).

### D9. `agent.prompt_builder.clear_skills_system_prompt_cache(clear_snapshot=True)` snapshot path is `~/.skills_prompt_snapshot.json`
- **Refuter verdict**: VERIFIED (no dispute).
- **Counter-evidence**: `agent/prompt_builder.py:971-981` confirms the path `_skills_prompt_snapshot_path = get_hermes_home() / ".skills_prompt_snapshot.json"` (HERMES_HOME-relative, so per-profile) and the cache invalidator signature.
- **Re-research needed**: **no**.

### D10. Truncation site performs "sanitization"
- **Refuter verdict**: REFUTED (security lens).
- **Counter-evidence**: `agent/skill_utils.py:647-655` body shows: `raw_desc = frontmatter.get("description", "")` → `desc = str(raw_desc).strip().strip("'\"")` → if `len(desc) > 60`: return `desc[:57] + "..."` else return `desc`. **No newline strip, no control-character filter, no escape, no allowlist, no length cap beyond 60.** The 57-char prefix flows unfiltered into the LLM system prompt built by `build_skills_system_prompt` at `prompt_builder.py:1127+`. Python `str[:57]` slices on code points, not grapheme clusters — ZWJ-emoji and combining marks can be split mid-grapheme. The function is a soft prompt-budgeting heuristic, not a security boundary.
- **Impact on Script #1**: any description-cap raising must remain a budget heuristic; no claim should be made that raising the cap "fixes" prompt-injection risk. The patch should keep the `strip().strip("'\"")` hygiene and the `[:N-3] + "..."` pattern (matching the existing `tools/skills_tool.py:655-656` shape).
- **Re-research needed**: **no** — incorporated into T1 and the Inputs Ready section.

---

## Open Questions for the HITL gate

1. **Should Script #1 raise the 60-char `extract_skill_description` cap, and to what value?** Options: (a) leave at 60 (style guideline only; rely on the existing 1024-char validator cap), (b) raise to 1024 to match `tools/skills_tool.py:95` `MAX_DESCRIPTION_LENGTH`, (c) raise to a smaller interim value (e.g. 200). The spec `docs/maybe-patch-points.md` implies a raising is desired; the exact target value is the design decision. **Note**: editing `agent/skill_utils.py:647-655` is the read-only-documented change site, but the project safety rule forbids modifying `~/.hermes/hermes-agent` — so this script must be staged as a controlled source edit in the user's own checkout, not as an in-place Hermes patch.

2. **What is the exact Hermes env-var name for the nesting guard?** The migration replaces `os.environ` filter `{"CLAUDECODE"}` with `{"CLAUDECODE", "<HERMES_NAME>"}`. Candidates: `HERMES_SESSION`, `HERMES_AGENT`, `HERMES_PARENT_PID`. **Must be confirmed by reading the Hermes harness** (`hermes_cli/main.py` or `hermes_constants.py`) before Script #1 lands.

3. **What is the exact Hermes CLI flag for `--include-partial-messages` / `--verbose`?** The `run_eval.py` migration replaces the `claude -p --output-format stream-json --verbose --include-partial-messages` invocation. Need to find the Hermes equivalent flag set (`--include-partial-events`? `--stream-events`?). Must be confirmed against the Hermes CLI's `argparse` parser before Script #1 lands.

4. **Does Script #2's flip phase require a per-profile `HERMES_HOME` mirror in `os.environ`, or is `set_hermes_home_override` sufficient?** The dispute in D7 shows that `do_install` / `save_config` / `get_disabled_skill_names` all anchor to `get_hermes_home()` which reads `os.environ['HERMES_HOME']` first. Confirm whether `set_hermes_home_override` updates the env var or only an in-process cache.

5. **Should the skill-creator SKILL.md description be left untouched (the 60-char cap is a separate problem), or should the migrated skill also be exempted from the cap?** If the cap stays at 60, the migrated skill's `description` frontmatter must be ≤60 chars. The current Claude `description` is well over 60. The T3 spec implies raising the cap; the exact value affects how aggressively the description can be Hermes-flavoured.

6. **Should Script #1 land an idempotent re-runnable `verify` mode, or just a one-shot `apply`?** The patch touches `agent/skill_utils.py:647-655` and the Task E sites across 4 files; a `--check` flag that asserts the expected state without writing is desirable. Confirm with the user.

7. **Should the migration ship a one-time GitHub-issue note that the 60-char cap was raised?** Issues #46005 and #46024 reference this work; an outbound comment in the new patch-script's release notes would be appropriate.

8. **Is the GitHub issue `NousResearch/hermes-agent#46005` real?** Not independently verifiable from the read-only environment. If the user wants to reference it in commit messages or the patch-script's README, confirm against the live GitHub UI.

9. **Does the `Website docs` site at `website/docs/user-guide/features/skills.md:378` actually exist in the v0.16.0 install at the cited line?** Re-read at planning time to confirm exact line offset (it may have shifted between v0.16.0 and the released tag).

10. **Should Script #1 take a `--profile <id>` flag so the patch only applies to one profile's config snapshot (not the global Hermes install)?** Per the project safety rule the script MUST NOT modify `~/.hermes/hermes-agent`; a per-profile dry-run that validates the patch against a config snapshot (e.g. `~/.hermes/profiles/<id>/config.yaml`) would let the user verify the change in one profile before deciding to apply it to the global install.

---

## Inputs Ready for the Plan

### I1. Script #1 — patch + migration spec (read-only verified sites)

- **Primary edit**: `agent/skill_utils.py:647-655` `extract_skill_description`. Replace the `if len(desc) > 60:` block with `if len(desc) > MAX_DESCRIPTION_LENGTH: return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` where `MAX_DESCRIPTION_LENGTH` is imported from `tools.skills_tool` (or `tools.skill_manager_tool`). This is the single source of truth for the agent-injected index.
- **Hermes tool-name translation table** (for the migrated skill-creator):
  - `Skill` → `skill_manage` (writes) / `skill_view` + `skills_list` (reads)
  - `Read` → `read_file`; `Write` → `write_file`; `Edit` → `patch` (mode='replace' default)
  - `Glob` / `Grep` → `search_files` (target='files' / 'content')
  - `Bash` → `terminal` / `read_terminal` / `execute_code`
  - `AskUserQuestion` → `clarify`
  - `Task` → `delegate_task` / `mixture_of_agents`
  - `WebSearch` → `web_search`; `WebFetch` → `web_extract`
  - `TodoWrite` → `todo`
  - `CronCreate` / `CronDelete` / `CronList` → `cronjob` (action dispatch)
  - `EnterPlanMode` / `ExitPlanMode` → no direct equivalent; use `delegate_task` + prose
- **Frontmatter validator changes** (`scripts/quick_validate.py`): extend `ALLOWED_PROPERTIES` to `{'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility', 'model', 'when_to_use'}`; keep the 64-char name cap and the 1024-char description cap; add a Hermes-specific name-collision check against the built-in skill registry.
- **Frontmatter soft-rule changes** (per T5): preserve Claude's `version`, `author`, `license`; add `metadata.hermes.tags` and `metadata.hermes.related_skills` (in-repo only). Use existing top-level categories from the in-repo skill list.
- **Highest-risk replacement sites** (per T3, in scripts):
  - `scripts/improve_description.py:26` — `cmd = ["hermes", "-p", "--output-format", "text"]`
  - `scripts/improve_description.py:32-33` — `env = {k: v for k, v in os.environ.items() if k not in {"CLAUDECODE", "HERMES_SESSION"}}` (HERMES_SESSION is TBD — see Q2)
  - `scripts/run_eval.py:23-46` — `find_project_root()` walks up looking for `.hermes/` (and `.claude/` as legacy)
  - `scripts/run_eval.py:46` — staging dir is `.hermes/commands/` (or `.claude/commands/` legacy)
  - `scripts/run_eval.py:71` — `cmd = ["hermes", "-p", query, "--output-format", "stream-json", "--include-partial-events"]` (flag name TBD — see Q3)
  - `scripts/run_eval.py:80-82` — strip `HERMES_SESSION` from env
  - `scripts/run_eval.py:137,156` — tool-name matches `if tool_name.lower() in ("skill", "read"):` (Hermes tool names are lowercase)
- **Naming**: agent files use `agent.md` (not `Agent.md`); reference is `Hermes` not `Claude`; tool names lowercase.
- **Phase 1 (capture intent) + Phase 3 (write skill) + Phase 4 (run evals)**: host-aware prose changes; preserve the three-tier subagent split (`grader`, `analyzer`, `comparator`) but rename to `subagent` per the Hermes convention.

### I2. Script #2 — Task C audit/flip spec (corrected per D4, D5, D6, D7)

**Recommended Python API path** (path-aware via `set_hermes_home_override`):

```python
from hermes_constants import set_hermes_home_override, reset_hermes_home_override
from hermes_cli.config import load_config, save_config
from hermes_cli.profiles import list_profiles, ProfileInfo
from agent.skill_utils import get_disabled_skill_names, is_excluded_skill_path
from tools.skills_sync import _read_manifest
from tools.skills_hub import HubLockFile
from agent.prompt_builder import clear_skills_system_prompt_cache

for profile in list_profiles():
    profile_dir = Path(profile.path)  # not profile.dir; verify exact field at plan time
    token = set_hermes_home_override(str(profile_dir))
    try:
        # AUDIT
        config = load_config()  # NO path= kwarg
        disabled_global = get_disabled_skill_names(platform=None)  # no config arg
        manifest = _read_manifest()  # reads <HERMES_HOME>/skills/.bundled_manifest
        hub_lock = HubLockFile().list_installed()
        # walk <profile_dir>/skills/**/*.md, parse SKILL.md YAML, cross-ref

        # FLIP
        new_disabled = (disabled_global - to_enable) | to_disable
        save_config(config)  # NO path= kwarg; writes to <profile_dir>/config.yaml because HERMES_HOME is overridden
        clear_skills_system_prompt_cache(clear_snapshot=True)
    finally:
        reset_hermes_home_override(token)
```

**Hard rules**:
- NEVER pass `path=` to `load_config` / `save_config` (D4).
- NEVER call `agent.skill_utils.get_disabled_skills(config, platform)` (D5) — use `agent.skill_utils.get_disabled_skill_names(platform)` for the runtime read or `hermes_cli.skills_config.get_disabled_skills(config, platform)` for the config-object read.
- NEVER walk `<profile>/gateway/` (D6) — gateway state is flat files in the profile root.
- ALWAYS wrap per-profile `do_install` calls in `set_hermes_home_override` AND mirror `os.environ['HERMES_HOME']` (D7).
- Audit must be idempotent and re-runnable: produce a deterministic JSON report keyed by `(profile_name, skill_name)` so flips can be diffed across runs.
- Flip must print bilingual EN+HU diffs and require `--apply` (dry-run by default).

### I3. Task E patch surface (reconciled — 7 sites across 4 files)

- Sites 1, 2, 3: `agent/prompt_builder.py` — `SKILLS_GUIDANCE` (172), `MEMORY_GUIDANCE` (143), `build_skills_system_prompt` result string (~1373).
- Sites 4, 5: `agent/background_review.py` — `_SKILL_REVIEW_PROMPT` (45, option 4 at ~100), `_COMBINED_REVIEW_PROMPT` (150, option 4 at ~188). **Do not** alter `spawn_background_review_thread` selection logic.
- Site 6 (OPTIONAL): `tools/skill_manager_tool.py:~992` `skill_manage` schema description — append a clarification; do NOT import/install/invoke/depend on skill-creator.
- Site 7: `website/docs/user-guide/features/skills.md` "Agent-Managed Skills" section (~378) — user-facing clarification that skill-creator is optional, not bundled.
- **Synchronization**: extract a single shared constant for the rule text in `prompt_builder.py` and import it in `background_review.py` to prevent drift.

### I4. Test plan hooks (TDD mandatory, 100% coverage)

- **Unit tests** for Script #1:
  - `extract_skill_description` returns the same output for any description ≤ N chars; returns the first N-3 chars + "..." for descriptions > N chars; handles empty string, whitespace-only, quoted strings, multi-line strings, ZWJ-emoji sequences (verifies current slicing behaviour is preserved before raising the cap).
  - Migrated scripts import the correct Hermes tool names; `claude` / `claude -p` strings are absent (negative assertion).
  - Frontmatter validator accepts both Claude and Hermes allowed keys.
  - Tool-name matcher is case-insensitive.
- **Unit tests** for Script #2:
  - `set_hermes_home_override` + `load_config` / `save_config` round-trip preserves YAML.
  - `get_disabled_skill_names(platform)` reflects the global list + the platform list.
  - Audit JSON is deterministic across runs.
  - Flip without `--apply` is a no-op.
- **Integration tests** for Task E patches:
  - `SKILLS_GUIDANCE` / `MEMORY_GUIDANCE` / `build_skills_system_prompt` strings contain the new-skill redirect.
  - `_SKILL_REVIEW_PROMPT` and `_COMBINED_REVIEW_PROMPT` option (4) contain the redirect.
  - All five string sites contain identical wording (synchronized).
  - The skill_manage schema description (if updated) does NOT introduce a runtime import of skill-creator.
  - The skills.md Agent-Managed Skills section describes skill-creator as optional, not bundled.
- **Bilingual rule**: every user-facing log message, console output, and audit report string must have an EN+HU pair. Code-level strings (Python identifiers, JSON keys, env-var names) are English-only.

### I5. Project workflow constraints (restate from project context)

- All Python scripts use `uv venv` + `pyproject.toml` + `pre-commit` (ruff + black + mypy + wemake-python-styleguide at strictest standard).
- Bilingual rule: code/skills/prompts in English; user-facing descriptions and console/log messages bilingual EN+HU.
- Worktree+PR workflow mandatory; never modify `~/.hermes/hermes-agent`.
- TDD mandatory; 100% code + logic coverage mandatory.
- Read-only inspection only for the Hermes install; all write operations target the worktree or the user's own checkout.

### I6. Confidence summary

- **High confidence** (independently verified by adversarial cross-read): T1 (truncation site), T4 (profile layout — corrected per D4/D5/D6/D7), T5 (skill conventions), T6 (Task E sites — corrected per D8).
- **Medium confidence** (verified source, with one open TBD): T2 (plugin authoring spec — corrected per D4/D5), T3 (Anthropic skill-creator — refuter contested the "50 invocations" figure, but the file list, SHA, and tool-name map are independently verified).
- **Low confidence / open questions**: the exact Hermes CLI flags (`--include-partial-messages`/`--verbose` equivalents), the exact env-var nesting-guard name, and the GitHub issue #46005 URL. These are surfaced in Open Questions Q2, Q3, Q8.