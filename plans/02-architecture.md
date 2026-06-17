<!-- title: Architecture — component diagram, data flow, sequence, failure modes, safety -->
<!-- scope: Cross-cutting. Replaces runtime monkey-patch with static-AST advisory; introduces hermes_home_scope; shows MIGRATION 3-file split. -->
<!-- ACs covered: AC-1.2, AC-1.3, AC-2.10, AC-3.4, AC-3.6, AC-4.10, AC-5.1, AC-5.2, AC-5.5 -->

# 02 — Architecture, Component Diagram, Data Flow

## Component diagram (logical)

```
                +---------------------------------------------+
                |          ~/.hermes  (READ-ONLY)             |
                |  +----------+    +---------------------+    |
                |  | agent/   |    | tools/skills_tool.py|    |
                |  | skill_   |    | MAX_DESCRIPTION_    |    |
                |  | utils.py |    | LENGTH = 1024       |    |
                |  | [:647-   |    +---------------------+    |
                |  |  655]    |                                |
                |  +----+-----+                                |
                |       |                                      |
                |       v                                      |
                |  agent/prompt_builder.py [:1090 call site]   |
                |  (extract_skill_description, NO mutation)    |
                +-----+---------------------------------------+
                      |
                      |  system-prompt injection (READ)
                      v
                +---------------------------------------------+
                |           LLM session                        |
                |  (sees <available_skills> index block)       |
                +---------------------------------------------+
                                ^  advisory
                                |  (one-time, side-effect-free)
                +---------------------------------------------+
                |  plugin's on_session_start (static AST read) |
                |  detects cap state; never setattr            |
                +---------------------------------------------+

     (this worktree, write target)
     ===================================================
                +---------------------------------------------+
                | hermes-skill-creator-plugin/                 |
                |   plugin.json  (manifest)                    |
                |   hooks.py     (on_session_start advisory)   |
                |   _advisory.py (static-AST cap detection)   |
                |   skill_register.py                          |
                |   installer.py  (interactive, --yes bypass)  |
                |   skills/skill-creator/  (migrated skill)    |
                |     SKILL.md, agents/, scripts/, ...         |
                +---------------------------------------------+
                | scripts/                                     |
                |   script_1_patch.py    (TDD-first)           |
                |   script_2_profiles.py (TDD-first)           |
                +---------------------------------------------+
                | hermes_skill_creator_plugin/                 |
                |   _scope.py     (hermes_home_scope)          |
                |   _subprocess.py (hermes_subprocess_env)     |
                +---------------------------------------------+
                | tests/  (unit, integration, fixtures)        |
                +---------------------------------------------+
                | MIGRATION.md  (top-level index)              |
                | MIGRATION.hermes-patch.md (Script #1)        |
                | MIGRATION.skill-port.md (migrated skill)     |
                | pyproject.toml + .pre-commit-config.yaml     |
                +---------------------------------------------+
```

The runtime monkey-patch path is GONE. The plugin is purely advisory (static AST read, no setattr). The cap-raise is a separate flow (Script #1, atomic write against a user-owned checkout).

## Data flow

### 1. Plugin install path (operator-driven, opt-in, interactive by default)

- Operator runs `uv run python -m hermes_skill_creator_plugin.install`.
- The installer:
  1. Parses `--hermes-home` (default: `$HERMES_HOME` or `~/.hermes`).
  2. Safety check: if resolved target == real `~/.hermes`, requires TTY confirmation OR `--yes`; non-TTY without `--yes` → exit 5.
  3. Enters `hermes_home_scope(target)` (single context manager for ALL writes).
  4. Detects cap state via static AST read (if `HERMES_HERMES_AGENT_TARGET` is set; otherwise the cap check is deferred to the first session).
  5. Validates the migrated skill's description against the active cap; aborts with bilingual error if it exceeds.
  6. Copies the plugin + skill (sha256-based idempotency).
  7. Exits the scope; restores `os.environ['HERMES_HOME']` and the override token.
- On next Hermes session start, the plugin's `on_session_start` hook:
  1. Resolves the Hermes target (env override or live `~/.hermes/hermes-agent`); runs `_advisory.detect_cap_state` (static AST; no I/O beyond read).
  2. If `unpatched`: writes the marker file under `HERMES_HOME` and emits a one-time bilingual log line.
  3. The plugin's `register` entry point calls `ctx.register_skill` with the bundled frontmatter.
- The plugin does NOT modify Hermes source. The actual cap-raise is performed by Script #1 against a user-owned Hermes checkout (separate flow, see below).

### 2. Patch path (Script #1)

- Operator runs `uv run hermes-skill-creator-patch --check --target <hermes-checkout-dir>`.
- `--target` is REQUIRED. If unset, the script exits 4 with `[en] --target is required. Refusing to run. / [hu] A --target kötelező. A szkript megtagadja a futtatást.`
- Safety check: `Path.resolve()(--target) == Path.resolve()(~/.hermes/hermes-agent)` → exit 4 with the exact resolved paths in both languages.
- Safety check: `--target/agent/skill_utils.py` must exist; otherwise exit 4.
- The script enumerates all patch sites (the cap-raise site in `agent/skill_utils.py`, plus the 7 Task E sites in `agent/prompt_builder.py`, `agent/background_review.py`, `tools/skill_manager_tool.py`, `website/docs/user-guide/features/skills.md`).
- For each site, it locates the file by path, then verifies BOTH the expected current text AND the expected line number. Mismatch → diagnostic; the script aborts.
- On `--apply`, writes the patch atomically (write to `<file>.patch.tmp` + `os.replace`; restore on exception). A `.patch.rejected` report is written on any pre-validation failure.
- `--force` retries only sites with `LINE_DRIFT`; requires `--i-accept-line-drift` second flag; pauses for TTY confirmation; appends to `~/.hermes/patch-audit.log`.
- On `--emit-migration-note`, regenerates `MIGRATION.hermes-patch.md` and `MIGRATION.md` in the WORKTREE (NOT the target). `MIGRATION.skill-port.md` is emitted by the migrated skill's own emit path (see flow 4).

### 3. Profile-manager path (Script #2)

- Operator runs `uv run hermes-skill-creator-profiles` (dry-run by default) or `--apply`.
- The script lists every profile via `hermes_cli.profiles.list_profiles()`; the default profile is always included.
- For each profile, the script enters `hermes_home_scope(path)` (single context manager; sets BOTH `set_hermes_home_override(path)` AND `os.environ['HERMES_HOME']=str(path)`, restoring both on exit):
  1. Reads the disabled-skill set via `agent.skill_utils.get_disabled_skill_names(platform=None)` — takes a `platform: str`, NOT a `config` dict.
  2. Reads the installed skill set by walking the per-profile `skills/**/*.md` and parsing frontmatter with `python-frontmatter`.
  3. Walks the `_PROFILE_DIRS` set: `{memories, sessions, skills, skins, logs, plans, workspace, cron, home}`. `gateway.pid` is a flat file in the profile root (read stat-only).
  4. Computes the desired state: `{openai: disabled, skills: disabled-if-present, skill-creator: installed-or-updated}`.
  5. In `--apply`, writes the new disabled set via `hermes_cli.skills_config.save_disabled_skills(config, platform=None, names=sorted(desired_disabled))`; calls `do_install("skill-creator", name_override="", force=True, skip_confirm=True, invalidate_cache=True)` from `hermes_cli.skills_hub`.
  6. Calls `clear_skills_system_prompt_cache(clear_snapshot=True)` (or, as a fallback if the function does not exist, deletes `~/.hermes/.skills_prompt_snapshot.json` directly).
- Emits a deterministic JSON report per profile; exits 0 on success.

### 4. Migrated skill runtime path (after install)

- Hermes loads `~/.hermes/skills/<cat>/skill-creator/SKILL.md` at session start.
- The skill's body instructs the agent to (a) call `skills_list`, (b) call `skill_view(name='hermes-agent-skill-authoring')` to load the validator rules, (c) follow the migrated authoring workflow, (d) persist with `skill_manage(action='create')`.
- The `scripts/run_eval.py` and `scripts/improve_description.py` shell out to `hermes` (NOT `claude`) under `hermes_subprocess_env()` (the helper that strips `HERMES_SESSION` from the subprocess env only).
- The migrated skill's installer emits `MIGRATION.skill-port.md` (the T3 inventory table) at install time.

### 5. Migration note path (3-file split)

- `MIGRATION.md` — top-level index. Generated by Script #1's `--emit-migration-note` (covers `MIGRATION.hermes-patch.md` link + the top-level how-to-apply). Source-controlled.
- `MIGRATION.hermes-patch.md` — generated by Script #1. Covers ONLY Script #1's patch sites (cap-raise + 7 Task E sites). Source-controlled.
- `MIGRATION.skill-port.md` — generated by the migrated skill's installer. Covers the T3 inventory (per-binding Claude→Hermes replacements). Source-controlled.

## Sequence — operator installs the plugin + runs the two scripts

```
Operator
  |  uv venv + uv pip install -e ".[dev]"
  |  uv run pre-commit install
  |  uv run hermes-skill-creator-patch --check --task-e-redirect --target ~/hermes-checkout
  |  uv run hermes-skill-creator-patch --apply --task-e-redirect --target ~/hermes-checkout
  |  uv run hermes-skill-creator-patch --emit-migration-note --target ~/hermes-checkout
  |  uv run hermes-skill-creator-profiles --apply
  |  uv run python -m hermes_skill_creator_plugin.install
  v
Hermes next session
  |  plugin on_session_start: static AST read of target; one-time advisory if unpatched
  |  plugin register: ctx.register_skill('skill-creator', ...)
  |  LLM sees <available_skills> index with up-to-1024-char descriptions (patched cap)
  v
LLM authoring a new skill
  |  calls skills_list, then skill_view(name='hermes-agent-skill-authoring')
  |  follows migrated authoring guidance
  |  persists with skill_manage(action='create')
  v
Hermes persists the new skill; plugin re-validates on next session.
```

## Sequence — graceful degradation when the patch is NOT applied

- The 60-char cap remains. The plugin's `on_session_start` static-AST read detects `unpatched` and emits a ONE-TIME bilingual advisory (persisted in `<HERMES_HOME>/.hermes_skill_creator_advisory_seen`; subsequent sessions are silent until the marker is deleted).
- The migrated skill ships TWO frontmatter variants: `SKILL.md` (description <= 1024 chars, used when cap is patched) and `SKILL.md.short` (description <= 60 chars, used when cap is unpatched). The installer selects the right one based on the detected cap state (or refuses if neither fits).
- The active cap is AUTHORITATIVE for the install: if cap=60 and the bundled description is 1024 chars, the installer refuses and instructs the operator to apply Script #1 first. This is AC-4.10.

## Failure modes

- **Patch drift** → `LINE_DRIFT` diagnostic; operator runs `--force --i-accept-line-drift` to retry line-only.
- **Hub install fails** → Script #2 emits a per-profile error block; operator can re-run `--apply` (idempotent).
- **Plugin manifest rejects** → `hermes-skill-creator-plugin install` exits non-zero; no files written.
- **Cache stale** → Script #2 calls `clear_skills_system_prompt_cache(clear_snapshot=True)` after every successful flip; falls back to direct delete if the function does not exist.
- **Active cap guard fails** → installer exits 1 with bilingual error; the operator runs Script #1 and re-runs the installer.
- **`os.environ['HERMES_HOME']` leak** → `hermes_home_scope` uses `try/finally` to restore both the override token and the env var; tested by `test_scope_restores_on_exception`.

## Safety recap (HARD)

- `~/.hermes/hermes-agent` is NEVER the target of a write. Reads are allowed ONLY for the static AST cap-state scan (and only when `HERMES_HERMES_AGENT_TARGET` is not set, in which case the resolver falls back to the live path for inspection).
- The plugin's `on_session_start` performs ZERO setattr on any Hermes module. ZERO file mutation of `~/.hermes/hermes-agent`.
- Script #1's `--target` is REQUIRED. It refuses the resolved `~/.hermes/hermes-agent` path. It refuses a target that lacks `agent/skill_utils.py`.
- Script #1's `--force` requires `--i-accept-line-drift`. It pauses for TTY confirmation. It appends to `~/.hermes/patch-audit.log`.
- The installer is interactive by default; refuses the real `~/.hermes` without `--yes` (or TTY confirmation).
- All file writes (installer + Script #2) go through `hermes_home_scope` which restores both `set_hermes_home_override` and `os.environ['HERMES_HOME']` on exit.

## Fix ledger

- Fixes [refuted claim 1] runtime monkey-patch — DELETED; replaced with static-AST advisory.
- Fixes [refuted claim 3] `load_config(path=...)` / `save_config(path=...)` — replaced with `hermes_home_scope` + no-path-arg calls.
- Fixes [refuted claim 4] `get_disabled_skills(config, platform)` — corrected to `agent.skill_utils.get_disabled_skill_names(platform=None)` and `hermes_cli.skills_config.save_disabled_skills` for the writer.
- Fixes [refuted claim 9] `do_install` signature — corrected to `do_install(identifier, category="", force=False, console=None, skip_confirm=False, invalidate_cache=True, name_override="")`; uses `force=True, skip_confirm=True` for idempotent re-install.
- Fixes [refuted claim 5] `gateway/` subdir — REMOVED; walks `_PROFILE_DIRS` and treats `gateway.pid` as a flat file.
- Fixes [refuted claim 10] MIGRATION single file — split into 3 files with pinned locations.

<!-- end of file: 184 lines (budget 200) -->
