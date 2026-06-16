# Coding task: make Hermes use `skill-creator` guidance before creating new skills

Repository: `NousResearch/hermes-agent`  
Target: current `main` branch. Locate symbols by name; do not rely on line numbers.

## Goal

Change Hermes Agent's prompt instructions so that **before creating a brand-new skill**, the agent:

1. checks whether an installed skill named `skill-creator` is available;
2. if available, loads it with `skill_view(name="skill-creator")` and follows its skill-authoring/validation guidance;
3. writes the resulting skill with `skill_manage(action="create", ...)`;
4. if `skill-creator` is absent, continues with Hermes' existing built-in class-level skill rules;
5. never auto-installs `skill-creator`, especially from the background review.

`skill-creator` is optional authoring guidance. `skill_manage` remains the only persistence mechanism. Do not replace or bypass `skill_manage`.

## Why

Hermes currently tells agents to create reusable skills directly with `skill_manage`, but it does not require consulting the optional `skill-creator` methodology first. The automatic path is driven mainly by review prompts, not by a mandatory creator skill. The change must improve generated skill quality without creating a hard dependency on an optional hub-installed skill.

## Required edits

### 1. `agent/prompt_builder.py`

#### A. Update `SKILLS_GUIDANCE`

Current anchor:

```python
SKILLS_GUIDANCE = (
    "After completing a complex task (5+ tool calls), fixing a tricky error, "
    "or discovering a non-trivial workflow, save the approach as a "
    "skill with skill_manage so you can reuse it next time.\n"
    ...
)
```

Replace/extend the creation instruction so it explicitly says:

```text
When a new skill is warranted, first check the available skills. If
`skill-creator` is installed, load it with
skill_view(name='skill-creator') and follow its authoring and validation
instructions. Then persist the final skill with
skill_manage(action='create'). If `skill-creator` is unavailable, use the
built-in class-level skill rules and continue; do not install it automatically.
```

Preserve the existing instruction to patch outdated/incomplete existing skills with:

```python
skill_manage(action="patch")
```

Do not force `skill-creator` for small targeted patches. Use it for new skills and optionally for major full rewrites.

#### B. Update the procedural redirect in `MEMORY_GUIDANCE`

Current anchor:

```text
If you've discovered a new way to do something, solved a problem that could be
necessary later, save it as a skill with the skill tool.
```

Make it consistent with `SKILLS_GUIDANCE`: new skill creation should consult installed `skill-creator` first when available, then use `skill_manage`; absence must not block creation.

#### C. Update `build_skills_system_prompt()`

Find the generated skills-index guidance containing anchors similar to:

```text
If a skill has issues, fix it with skill_manage(action='patch').
After difficult/iterative tasks, offer to save as a skill.
```

Add the same new-skill rule here because this block is another foreground-agent prompt surface:

```text
Before creating a new skill, load `skill-creator` if it appears in the
available-skills index. Use it only as authoring guidance; persist with
skill_manage. If it is absent, continue without it and do not install it.
```

Avoid contradictory duplicate wording among `MEMORY_GUIDANCE`, `SKILLS_GUIDANCE`, and the skills-index block.

### 2. `agent/background_review.py`

This is the critical automatic skill-creation path.

#### A. Update `_SKILL_REVIEW_PROMPT`

Find the preference-order item:

```text
4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL when no existing skill covers the class.
```

Immediately before the actual `skill_manage(action="create")` step, require:

```text
Before creating a new skill, call `skills_list`. If an installed skill named
`skill-creator` exists, load it with `skill_view(name='skill-creator')` and
follow its authoring/validation workflow when drafting the new SKILL.md.
Then create the skill with `skill_manage(action='create')`.
If `skill-creator` is not installed or cannot be loaded, continue using the
built-in class-level rules. Do not install or fetch it during background review.
```

Preserve the existing decision order:

1. patch a currently loaded skill;
2. patch an existing class-level umbrella skill;
3. add a support file under an existing umbrella;
4. create a new class-level umbrella only when nothing suitable exists.

Preserve all existing protections and exclusions, including protected skills, transient environment failures, negative tool claims, and one-off task narratives.

#### B. Update `_COMBINED_REVIEW_PROMPT`

Apply the same rule to its item:

```text
4. CREATE A NEW CLASS-LEVEL UMBRELLA when nothing exists.
```

The combined memory+skill review must behave identically to the skill-only review for new-skill creation.

#### C. Do not change prompt selection logic

Do not alter `spawn_background_review_thread()` except if tests require refactoring shared prompt text. It must continue selecting:

```python
_COMBINED_REVIEW_PROMPT
_MEMORY_REVIEW_PROMPT
_SKILL_REVIEW_PROMPT
```

based on `review_memory` / `review_skills`.

Prefer extracting one shared string constant for the `skill-creator` creation rule if that avoids drift between `_SKILL_REVIEW_PROMPT` and `_COMBINED_REVIEW_PROMPT`, but preserve final prompt text and backward-compatible module constants.

### 3. `tools/skill_manager_tool.py`

Do **not** redesign the tool.

Keep these responsibilities unchanged:

- `create`: writes a complete `SKILL.md`;
- `patch`: targeted fix, preferred for existing skills;
- `edit`: full rewrite;
- `write_file`: writes support files;
- successful writes clear the skills prompt cache;
- background-created skills retain their provenance/telemetry behavior.

Optional schema-description clarification:

```text
`skill-creator`, when installed, provides authoring guidance only.
Use `skill_manage` to persist all skill files.
```

Do not make `skill_manage` import, install, invoke, or depend on `skill-creator`. This is a prompt-orchestration change, not a storage-layer change.

### 4. Documentation

Update:

```text
website/docs/user-guide/features/skills.md
```

In **Agent-Managed Skills**, clarify:

- Hermes still creates and updates skills through `skill_manage`;
- before a new skill is created, prompt guidance may load installed `skill-creator`;
- `skill-creator` is optional and can be installed from a hub;
- absence of `skill-creator` does not disable automatic skill creation;
- background review must never auto-install it.

Do not describe `skill-creator` as bundled or mandatory.

## Tests

Locate relevant tests instead of guessing paths:

```bash
rg -n "SKILLS_GUIDANCE|MEMORY_GUIDANCE|build_skills_system_prompt" tests
rg -n "_SKILL_REVIEW_PROMPT|_COMBINED_REVIEW_PROMPT|spawn_background_review_thread" tests
rg -n "skill_manage|SKILL_MANAGE_SCHEMA" tests
```

Add/update tests that assert:

1. foreground prompt guidance mentions:
    - `skill-creator`;
    - `skill_view`;
    - `skill_manage`;
    - fallback when unavailable;
    - no automatic install;

2. both background prompts contain the same creation rule;

3. the background preference order remains patch/update/support-file/create;

4. `spawn_background_review_thread()` still selects the correct prompt;

5. `skill_manage` behavior and action routing are unchanged;

6. existing prompt-builder/background-review/skill-manager tests pass.

Run the narrow tests first, then the repository's standard formatting/lint/test commands discovered from its contributor configuration.

## Acceptance criteria

- New skill creation consults installed `skill-creator` in both foreground and automatic background-review prompts.
- Existing-skill patches remain patch-first and do not unnecessarily invoke `skill-creator`.
- `skill_manage` remains the writer.
- No network lookup or installation occurs automatically.
- Hermes still creates skills when `skill-creator` is absent.
- Both review prompts stay semantically synchronized.
- Existing protected-skill and anti-transient-learning rules remain intact.
- Documentation and tests match the new behavior.
- Return a concise summary containing changed files, exact behavior change, and tests run.
