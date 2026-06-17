<!-- title: Architecture — component diagram, data flow, sequence, failure modes, safety -->
<!-- scope: Cross-cutting. Replaces runtime monkey-patch with static-AST advisory; introduces hermes_home_scope; shows MIGRATION 3-file split; adds Script #3 (reporter). -->
<!-- ACs covered: AC-1.2, AC-1.3, AC-2.10, AC-3.4, AC-3.6, AC-4.10, AC-5.1, AC-5.2, AC-5.5 -->

# 02 — Architecture, Component Diagram, Data Flow

## Component diagram (logical)

```
                +---------------------------------------------+
                |          ~/.hermes  (READ-ONLY)             |
                |  +-----------------------------+            |
                |  | agent/skill_utils.py        |            |
                |  |   extract_skill_description  |            |
                |  +-----------------------------+            |
                |  +-----------------------------+            |
                |  | agent/prompt_builder.py     |            |
                |  |   build_available_skills_   |            |
                |  |   block + clear_skills_     |            |
                |  |   system_prompt_cache       |            |
                |  +-----------------------------+            |
                |  +-----------------------------+            |
                |  | tools/skills_tool.py        |            |
                |  | MAX_DESCRIPTION_LENGTH=1024 |            |
                |  +-----------------------------+            |
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
                |   plugin.yaml  (manifest)                    |
                |   __init__.py  (single register(ctx))        |
                |   hooks.py     (on_session_start advisory)   |
                |   _advisory.py (static-AST cap detection)   |
                |   _scope.py    (hermes_home_scope)          |
                |   i18n/        (en + hu message bundles)     |
                +---------------------------------------------+
                | scripts/                                     |
                |   script_1_patch.py    (TDD-first)           |
                |   script_2_profiles.py (TDD-first)           |
                |   script_3_report.py   (TDD-first, READ-ONLY)|
                +---------------------------------------------+
                | hermes_skill_creator_plugin/                 |
                |   _enabled_detection.py                      |
                |     (get_enabled_skills — shared by #2 + #3)|
                +---------------------------------------------+
                | tests/  (unit, integration, fixtures)        |
                +---------------------------------------------+
                | MIGRATION.md  (top-level index)              |
                | MIGRATION.hermes-patch.md (Script #1)        |
                | MIGRATION.skill-port.md (migrated skill)     |
                | pyproject.toml + .pre-commit-config.yaml     |
                +---------------------------------------------+

     +---------------------------------------------+
     | skills/skill-creator/   (STANDALONE —       |
     |   NOT inside the plugin box; sibling of     |
     |   hermes-skill-creator-plugin/ at the       |
     |   worktree root)                            |
     |   SKILL.md, agents/, scripts/, _subprocess  |
     +---------------------------------------------+
```

The runtime monkey-patch path is GONE. The plugin is purely advisory (static AST read, no setattr). The cap-raise is a separate flow (Script #1, atomic write against a user-owned checkout). The migrated skill is a SEPARATE worktree-root deliverable, NOT bundled inside the plugin package — the plugin never owns or registers it. Script #3 is a third, READ-ONLY script that reuses `_enabled_detection` from the plugin module.

## Data flow

### 1. Plugin install + advisory path

- The plugin is installed via the standard Hermes plugin loader (drops `plugin.yaml` + Python modules into the user-discovered plugin path). There is NO `python -m hermes_skill_creator_plugin.install` subcommand. The plugin does NOT bundle, own, or register the migrated skill.
- On next Hermes session start, the plugin's `on_session_start` hook:
  1. Resolves the Hermes target (env override or live `~/.hermes/hermes-agent`); runs `_advisory.detect_cap_state` (static AST; no I/O beyond read).
  2. If `unpatched`: writes the marker file under `HERMES_HOME` and emits a one-time bilingual log line.
- The plugin's `__init__.py` `register(ctx)` is the ONLY entry point; it does NOT call `ctx.register_skill('skill-creator', ...)` — that registration is performed at install time by Script #2's `do_install` into `~/.hermes/skills/skill-creator/`.
- The plugin does NOT modify Hermes source. The actual cap-raise is performed by Script #1 against a user-owned Hermes checkout (separate flow, see below).

### 2. Patch path (Script #1)

- Operator runs `uv run hermes-skill-creator-patch --check --target <hermes-checkout-dir>`.
- `--target` is REQUIRED. If unset, the script exits 4 with `[en] --target is required. Refusing to run. / [hu] A --target kötelező. A szkript megtagadja a futtatását.`
- Safety check: `Path.resolve()(--target) == Path.resolve()(~/.hermes/hermes-agent)` → exit 4 with the exact resolved paths in both languages.
- Safety check: `--target/agent/skill_utils.py` must exist; otherwise exit 4.
- The script enumerates all patch sites (the cap-raise site at symbol `agent.skill_utils.extract_skill_description`, plus the 7 Task E sites in `agent/prompt_builder.py`, `agent/background_review.py`, `tools/skill_manager_tool.py`, `website/docs/user-guide/features/skills.md`).
- For each site, it locates the file by path, then verifies BOTH the expected current text AND the expected line number. Mismatch → diagnostic; the script aborts.
- On `--apply`, writes the patch atomically (write to `<file>.patch.tmp` + `os.replace`; restore on exception). A `.patch.rejected` report is written on any pre-validation failure.
- `--force` retries only sites with `LINE_DRIFT`; requires `--i-accept-line-drift` second flag; pauses for TTY confirmation; appends to `~/.hermes/patch-audit.log`.
- On `--emit-migration-note`, regenerates `MIGRATION.hermes-patch.md` and `MIGRATION.md` in the WORKTREE (NOT the target). `MIGRATION.skill-port.md` is emitted by the migrated skill's own emit path (see flow 4).

### 3. Profile-manager path (Script #2)

- Operator runs `uv run hermes-skill-creator-profiles` (dry-run by default) or `--apply`.
- The script lists every profile via `hermes_cli.profiles.list_profiles()`; the default profile is always included.
- For each profile, the script enters `hermes_home_scope(path)` (single context manager; sets BOTH `set_hermes_home_override(path)` AND `os.environ['HERMES_HOME']=str(path)`, restoring both on exit):
  1. Reads the enabled-skill set via `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills(profile_path, platform=None)` — the CANONICAL helper shared with Script #3. Returns a `frozenset[str]`.
  2. Reads the disabled-skill set via `agent.skill_utils.get_disabled_skill_names(platform=None)` — takes a `platform: str`, NOT a `config` dict.
  3. Walks the `_PROFILE_DIRS` set: `{memories, sessions, skills, skins, logs, plans, workspace, cron, home}`. `gateway.pid` is a flat file in the profile root (read stat-only).
  4. Computes the desired state: `{skill-creator: replaced-in-place}` (the factory skill-creator, installed from `openai/skills/skill-creator`, is REPLACED IN-PLACE by the migrated skill-creator via `do_install(force=True, skip_confirm=True, invalidate_cache=True, name_override="")` into `~/.hermes/skills/skill-creator/` — same dir/name as the factory). There is NO separate disable step for `openai` (no skill is named `openai`; disabling is keyed by skill NAME per `tools/skills_tool.py:597`). The factory skill is effectively replaced because `do_install` overwrites the directory. The plan must reason about the name collision (the `skill-creator` name is shared between factory and migrated).
  5. In `--apply`, writes the new disabled set via `hermes_cli.skills_config.save_disabled_skills(config, disabled, platform=None)` (positional); calls `do_install("skill-creator", name_override="", force=True, skip_confirm=True, invalidate_cache=True)` from `hermes_cli.skills_hub`.
  6. Calls `clear_skills_system_prompt_cache(clear_snapshot=True)` — the function lives at symbol `agent.prompt_builder.clear_skills_system_prompt_cache` with sig `(*, clear_snapshot=False)`. It EXISTS; there is no fallback.
- Emits a deterministic JSON report per profile; exits 0 on success.

### 4. Migrated skill runtime path (after install)

- Hermes loads `~/.hermes/skills/skill-creator/SKILL.md` at session start.
- The skill's body instructs the agent to (a) call `skills_list`, (b) call `skill_view(name='hermes-agent-skill-authoring')` to load the validator rules, (c) follow the migrated authoring workflow, (d) persist with `skill_manage(action='create')`.
- The `scripts/run_eval.py` and `scripts/improve_description.py` shell out to `hermes` (NOT `claude`) under `hermes_subprocess_env()` (the helper at `skills/skill-creator/_subprocess.py` that strips `HERMES_SESSION` from the subprocess env only).
- The migrated skill's installer emits `MIGRATION.skill-port.md` (the T3 inventory table) at install time.

### 5. Migration note path (3-file split)

- `MIGRATION.md` — top-level index. Generated by Script #1's `--emit-migration-note` (covers `MIGRATION.hermes-patch.md` link + the top-level how-to-apply). Source-controlled.
- `MIGRATION.hermes-patch.md` — generated by Script #1. Covers ONLY Script #1's patch sites (cap-raise + 7 Task E sites). Source-controlled.
- `MIGRATION.skill-port.md` — generated by the migrated skill's installer. Covers the T3 inventory (per-binding Claude→Hermes replacements). Source-controlled.

### 6. Report path (Script #3, READ-ONLY)

- Operator runs `uv run hermes-skill-creator-report [--profile PATH] [--json PATH]`.
- Script #3 is READ-ONLY. It NEVER writes to `~/.hermes`, NEVER modifies Hermes source, NEVER installs or removes a skill.
- For each requested profile, it calls `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills(profile_path, platform=None)` — the SAME canonical helper used by Script #2 — to enumerate the enabled-skill set.
- It cross-references the enabled set with `tools/skill_usage` usage counters (`last_used_at`, `last_viewed_at`, `last_patched_at`, `use_count`, `view_count`, `patch_count`) and emits:
  - a human-readable report to STDOUT (table of profile, skill, status, last-used, counts), and
  - a deterministic JSON document to `--json PATH` if provided.
- Script #3 exits 0 on success, non-zero only on resolution/IO error (never on empty results).

## Sequence — operator installs the plugin + runs the three scripts

```
Operator
  |  uv venv + uv pip install -e ".[dev]"
  |  uv run pre-commit install
  |  uv run hermes-skill-creator-patch --check --target ~/hermes-checkout
  |  uv run hermes-skill-creator-patch --apply --target ~/hermes-checkout
  |  uv run hermes-skill-creator-patch --emit-migration-note --target ~/hermes-checkout
  |  uv run hermes-skill-creator-profiles --apply
  |  uv run hermes-skill-creator-report --json ~/reports/skills.json
  v
Hermes next session
  |  plugin on_session_start: static AST read of target; one-time advisory if unpatched
  |  script_2 do_install wrote ~/.hermes/skills/skill-creator/ flat path (replacement-in-place)
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
- **Plugin manifest rejects** → plugin loader exits non-zero; no files written.
- **Cache stale** → Script #2 calls `clear_skills_system_prompt_cache(clear_snapshot=True)` after every successful flip.
- **Active cap guard fails** → installer exits 1 with bilingual error; the operator runs Script #1 and re-runs Script #2's `--apply`.
- **`os.environ['HERMES_HOME']` leak** → `hermes_home_scope` uses `try/finally` to restore both the override token and the env var; tested by `test_scope_restores_on_exception`.
- **Script #3 source-read fail** → Script #3 exits non-zero with a bilingual diagnostic; STDOUT/JSON are NOT emitted.

## Safety recap (HARD)

- `~/.hermes/hermes-agent` is NEVER the target of a write. Reads are allowed ONLY for the static AST cap-state scan (and only when `HERMES_HERMES_AGENT_TARGET` is not set, in which case the resolver falls back to the live path for inspection).
- The plugin's `on_session_start` performs ZERO setattr on any Hermes module. ZERO file mutation of `~/.hermes/hermes-agent`.
- Script #1's `--target` is REQUIRED. It refuses the resolved `~/.hermes/hermes-agent` path. It refuses a target that lacks `agent/skill_utils.py`.
- Script #1's `--force` requires `--i-accept-line-drift`. It pauses for TTY confirmation. It appends to `~/.hermes/patch-audit.log`.
- Script #2 is non-interactive (`skip_confirm=True`); refuses the resolved `~/.hermes` write target by going through `hermes_home_scope`, which restores both `set_hermes_home_override` and `os.environ['HERMES_HOME']` on exit.
- Script #3 is READ-ONLY end-to-end: no writes, no installs, no setattr, no env mutations beyond the same `hermes_home_scope` read-scope used by Script #2.
- All file writes (Script #2 only — Script #1 writes to the user-owned `--target` checkout, NOT `~/.hermes`) go through `hermes_home_scope` which restores both `set_hermes_home_override` and `os.environ['HERMES_HOME']` on exit.
- Script #2's disable-set is name-keyed (`tools/skills_tool.py:597`): a name like `"openai"` matches no skill and is therefore a no-op. The factory→migrated swap is REPLACEMENT-IN-PLACE via `do_install(force=True, ...)` — no separate disable step is performed for the factory skill, because both copies share the same NAME and the migrated copy overwrites the factory at the same flat path.

## Fix ledger

- Fixes [refuted claim 1] runtime monkey-patch — DELETED; replaced with static-AST advisory.
- Fixes [refuted claim 3] `load_config(path=...)` / `save_config(path=...)` — replaced with `hermes_home_scope` + no-path-arg calls.
- Fixes [refuted claim 4] `get_disabled_skills(config, platform)` — corrected to `agent.skill_utils.get_disabled_skill_names(platform=None)` for reads and `hermes_cli.skills_config.save_disabled_skills(config, disabled, platform=None)` for writes; enabled-detection routed through the canonical `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills(profile_path, platform=None)`.
- Fixes [refuted claim 9] `do_install` signature — corrected to `do_install(identifier, category="", force=False, console=None, skip_confirm=False, invalidate_cache=True, name_override="")`; uses `force=True, skip_confirm=True` for idempotent re-install.
- Fixes [refuted claim 5] `gateway/` subdir — REMOVED; walks `_PROFILE_DIRS` and treats `gateway.pid` as a flat file.
- Fixes [refuted claim 10] MIGRATION single file — split into 3 files with pinned locations.
- Fixes [V4-R1] `plugin.json` → `plugin.yaml`; the migrated skill is STANDALONE at worktree-root `skills/skill-creator/`, NOT bundled inside the plugin package; the plugin does NOT call `ctx.register_skill('skill-creator', ...)`; `installer.py` and the `python -m hermes_skill_creator_plugin.install` subcommand are REMOVED.
- Fixes [V4-R1] `clear_skills_system_prompt_cache` source-of-truth is `agent.prompt_builder`; the "if the function does not exist" fallback is DROPPED.
- Fixes [V4-R4] ONE canonical enabled-detection name: `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills` — shared by Script #2 (writes) and Script #3 (reads).
- Fixes [V4-R11] Script #3 has NO `--emit-migration-note`, NO `MIGRATION.report.md`. It is STDOUT + `--json PATH` only.
- Fixes [V4-R5] desired-state model is REPLACEMENT-IN-PLACE — there is NO `"openai": disabled` step (no skill is named `openai`; name-keyed disable is a no-op). The factory `skill-creator` is overwritten by the migrated `skill-creator` at the same flat path via `do_install(force=True, ...)`. The disable set is rewritten to the current disabled set (plus any name-keyed additions), never unioned with `"openai"`.

## Decisions & evidence

### D1. `plugin.yaml` is the manifest format (M2)
- **Decision**: the plugin ships `src/hermes_skill_creator_plugin/plugin.yaml` (YAML). `plugin.json` is REMOVED. The manifest has NO `entry_points` map and NO `kind` field.
- **Rationale**: `hermes_cli/plugins.py` requires a `plugin.yaml` manifest at the plugin root (per V3 review M2). The single `register(ctx)` in `__init__.py` is the load model; an `entry_points` map would create a second wiring path.
- **Evidence**: V3 [major M2]; `hermes_cli/plugins.py` (anchor "Each directory plugin must contain a `plugin.yaml` manifest"); AC-1.1 in 01; 03 §plugin.yaml. Confidence: verified-from-source.

### D2. Migrated skill is STANDALONE at worktree root (B4)
- **Decision**: `skills/skill-creator/` is a sibling of `src/`, `tests/`, `docs/` at the worktree root — NOT inside `src/hermes_skill_creator_plugin/`. The plugin does NOT bundle, contain, or own the skill files.
- **Rationale**: a skill bundled inside the plugin package cannot be installed at the flat `~/.hermes/skills/<name>/` path, and `register_skill` cannot achieve `<available_skills>` index visibility.
- **Evidence**: V3 [blocker B4]; 03 §Plugin layout; AC-1.4 + AC-4.1 in 01. Confidence: verified-from-source.

### D3. Plugin does NOT register_skill (B3)
- **Decision**: the plugin's `register(ctx)` calls `ctx.register_hook('on_session_start', cb)` ONLY. It does NOT call `ctx.register_skill('skill-creator', ...)`. There is NO `skill_register.py` module.
- **Rationale**: `register_skill` resolves a plugin-registered skill as `<plugin_name>:<name>` via explicit `skill_view()`; it is NOT placed in the flat tree and is NOT listed in `<available_skills>`. Surfacing the skill via the plugin does NOT satisfy AC-1.4 / AC-4.1.
- **Evidence**: V3 [blocker B3]; 03 §Load model; AC-1.4 in 01. Confidence: verified-from-source.

### D4. ONE canonical enabled-detection helper (R4 fix)
- **Decision**: `hermes_skill_creator_plugin._enabled_detection.get_enabled_skills(profile_path, *, platform=None) -> frozenset[str]` is the SINGLE source of truth, shared by Script #2 (writes) and Script #3 (reads). No duplicates, no fallback to a local re-implementation.
- **Rationale**: round-2 review found the reporter was about to re-derive the enabled set locally; sharing prevents drift between audit (Script #2) and report (Script #3).
- **Evidence**: V5 R4 + R10 fix; 06 §Shared enabled-detection module; 13 §Enabled-set detection; AC-7.3 in 01. Confidence: verified-from-source.

### D5. `hermes_home_scope` mirrors BOTH override token AND env var
- **Decision**: `hermes_home_scope(path)` sets BOTH `set_hermes_home_override(str(path))` AND `os.environ['HERMES_HOME']=str(path)`, restoring both on exit (try/finally).
- **Rationale**: `hermes_cli.config.load_config()` and `save_config()` anchor on the override token (via `get_config_path()`); `hermes_cli.skills_hub.do_install` reads `os.environ['HERMES_HOME']` in some sub-paths. Mirroring both is the only way to ensure config writes and hub installs resolve to the scoped HERMES_HOME.
- **Evidence**: V3 [refuted claim 3]; 06 §hermes_home_scope; AC-3.4 / AC-3.6 in 01. Confidence: verified-from-source.

### D6. `clear_skills_system_prompt_cache` is from `agent.prompt_builder` (V4-R1)
- **Decision**: Script #2 calls `agent.prompt_builder.clear_skills_system_prompt_cache(clear_snapshot=True)`; the "if the function does not exist" fallback is DROPPED.
- **Rationale**: the function EXISTS in the installed Hermes at `agent/prompt_builder.py:~1022` (sig `(*, clear_snapshot: bool = False)`); a literal-path fallback to `~/.hermes/...` violates the "never touch the real install" rule.
- **Evidence**: V4-R1; 06 §Apply path step 6c; AC-3.8 in 01. Confidence: verified-from-source.

### D7. Desired-state is REPLACEMENT-IN-PLACE, not name-keyed disable of `"openai"` (V4-R5 S5)
- **Decision**: Script #2's desired state contains exactly one swap: `skill-creator` REPLACED IN-PLACE at the flat path `~/.hermes/skills/skill-creator/` via `do_install("skill-creator", name_override="", force=True, skip_confirm=True, invalidate_cache=True)`. The disabled set is rewritten to the current disabled set (with no union of `"openai"`).
- **Rationale**: disabling is keyed by skill NAME (`tools/skills_tool.py:597` `return name in global_disabled`; `:644` `name = frontmatter.get("name", skill_dir.name)`). There is no skill named `"openai"` — `openai` is only the upstream HUB INSTALL PATH (`hermes_cli/skills_hub.py:1671`), not a skill name. Unioning `"openai"` to the disabled set is a no-op that would mislead operators. The factory `skill-creator` and the migrated `skill-creator` share the same NAME (`skill-creator`); disabling by that name would break the migrated skill's own `<available_skills>` index entry — the exact opposite of intent. The correct swap is byte-for-byte overwrite at the same flat path.
- **Evidence**: 06 §S5 (V4 RR2/REC-3 fix); AC-3.2 in 01. Confidence: verified-from-source.

<!-- end of file: 234 lines (budget 210) -->
