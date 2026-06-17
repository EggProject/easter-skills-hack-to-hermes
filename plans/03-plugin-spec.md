<!-- title: Hermes plugin spec (Section 5.1) — advisory-only; static-AST cap detection; one-time bilingual log -->
<!-- scope: Sec 5.1. Plugin is purely advisory. The cap-raise is Script #1's job. The migrated skill-creator is a STANDALONE deliverable shipped via the hub, NOT bundled in the plugin. -->
<!-- ACs covered: AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-4.10 -->

# 03 — Hermes Plugin Spec (§5.1)

## Goal

Ship a Hermes plugin named `hermes-skill-creator-plugin` that:

1. Emits a ONE-TIME bilingual advisory at session start if the 60-char skill-description cap is detected (via static AST read of the operator's Hermes checkout) as still 60. NO runtime setattr on `agent.skill_utils`. NO file mutation. NO monkey-patch.
2. Conforms to `hermes-agent-skill-authoring` (the validator at `tools/skill_manager_tool.py:_validate_frontmatter`).
3. Does NOT register, bundle, contain, or own the migrated `skill-creator` skill. The skill is a standalone deliverable at `skills/skill-creator/` (worktree root) and is shipped via the hub / Script #2's `do_install` into the flat `~/.hermes/skills/skill-creator/` tree.

> **Hard rule (HARD)**: the plugin NEVER modifies `~/.hermes/hermes-agent` (neither by file write NOR by in-process module mutation). The cap-raise is performed ONLY by Script #1 against a user-owned Hermes checkout (see `04-script-1-patch.md`).

> **Hard rule (HARD)**: the plugin NEVER registers `skill-creator` via `ctx.register_skill`. A plugin-registered skill resolves ONLY as `<plugin_name>:<name>` via explicit `skill_view()`; it is NOT placed in the flat `~/.hermes/skills/` tree and is NOT listed in the system-prompt `<available_skills>` index. Registering the skill via the plugin would NOT make it appear as `skill-creator` in the index, which is what Task E and the brief depend on.

## Plugin layout

```
src/hermes_skill_creator_plugin/
  __init__.py                 # contains the single register(ctx) that wires the on_session_start hook
  plugin.yaml                 # manifest (required; YAML, not JSON)
  _advisory.py                # static-AST cap detection (NO setattr, NO mutation)
  _scope.py                   # hermes_home_scope context manager
  _subprocess.py              # hermes_subprocess_env() helper
  i18n/
    messages_en.py
    messages_hu.py
  tests/  (under tests/, not in the package)
```

There is NO `skill_register.py` (the plugin does NOT register the skill). There is NO `installer.py` (no `python -m ... install` subcommand). There is NO bundled `skills/skill-creator/` subdirectory. There is NO `patch_runtime.py` and NO `resources/extract_skill_description_patched.py`. The runtime monkey-patch is DELETED.

The migrated skill lives at the WORKTREE ROOT, separate from the plugin package:

```
skills/
  skill-creator/
    SKILL.md                  # migrated skill body
    ... (agents/, scripts/, eval-viewer/, references/, assets/)
```

This directory is a STANDALONE deliverable. It is shipped/installed by Script #2's `do_install` (see `06-script-2-profiles.md`) into the flat path `~/.hermes/skills/skill-creator/`, which is what makes it appear as `skill-creator` in the `<available_skills>` index.

## plugin.yaml (manifest)

```yaml
name: hermes-skill-creator-plugin
version: 0.1.0
description: >-
  Emits a one-time bilingual advisory if the 60-char skill-description cap is
  un-raised in the operator's Hermes checkout. The cap is raised by Script #1
  against a user-owned checkout; this plugin performs NO cap mutation and does
  NOT register, bundle, or own the migrated skill-creator skill.
author: kiscsicska
provides_hooks:
  - on_session_start
```

The manifest is `plugin.yaml` (YAML), per the load model in `hermes_cli/plugins.py` which requires a `plugin.yaml` manifest at the plugin root. There is NO `entry_points` map. There is NO `kind` field (the only known valid value per `pluginAuthoring.json` is `backend`; per Q-confirmed the safest default is no `kind` at all). The plugin declares its capability via `provides_hooks` only.

The plugin has no `requires_env`. The cap-raise state is detected, not gated.

## Load model: one `register(ctx)` in `__init__.py`

Per `hermes_cli/plugins.py`, the load model is a single `register(ctx)` callable in the package `__init__.py` (or a pip entry point in the group `hermes_agent.plugins`). The plugin uses the in-package form. Inside that one `register(ctx)`, the plugin calls `ctx.register_hook('on_session_start', advisory_callback)`. There is NO split `hooks:register` and `skill_register:register` pair.

`src/hermes_skill_creator_plugin/__init__.py` (sketch):

```python
"""hermes-skill-creator-plugin: advisory-only cap-state detector."""
from ._advisory import (
    detect_cap_state,
    resolve_target_dir,
    should_emit_advisory,
    emit_advisory,
)
from .i18n.messages_en import ADVISORY_CAP_EN
from .i18n.messages_hu import ADVISORY_CAP_HU
from pathlib import Path
import os

def register(ctx) -> None:
    """Single entry point invoked by hermes_cli.plugins at plugin load."""
    target = resolve_target_dir()
    state = detect_cap_state(target)  # static AST, no setattr
    if state != "unpatched":
        return
    advisory_marker = Path(os.environ["HERMES_HOME"]) / ".hermes_skill_creator_advisory_seen"
    if not should_emit_advisory(advisory_marker):
        return  # one-time semantics
    ctx.log(f"{ADVISORY_CAP_EN} / {ADVISORY_CAP_HU}")
    emit_advisory(advisory_marker)  # best-effort marker write
```

The plugin NEVER calls `ctx.register_skill(...)`. The plugin NEVER imports `agent.skill_utils` at import time. The plugin NEVER performs `setattr` on any Hermes module.

## Cap-raise mechanism (static-AST, NOT runtime)

`_advisory.py`:

```python
"""Static AST-based cap-state detection. NO runtime mutation. NO setattr.

The actual cap-raise is performed by Script #1 against a user-owned Hermes
checkout. This module only DETECTS the cap state; it NEVER mutates the target.
"""
from __future__ import annotations
import ast
import os
from pathlib import Path

# Pin: the cap value in the unpatched agent/skill_utils.py.
UNPATCHED_CAP = 60
# Pin: the constant the patched function uses.
PATCHED_CAP_REFERENCE = "MAX_DESCRIPTION_LENGTH"

def resolve_target_dir() -> Path:
    """Return the Hermes checkout to inspect.

    Honors HERMES_HERMES_AGENT_TARGET (set by Script #1 + CI). Falls back to
    ~/.hermes/hermes-agent ONLY in interactive operator use; CI must always
    set the env var to avoid the live read.
    """
    env = os.environ.get("HERMES_HERMES_AGENT_TARGET")
    if env:
        return Path(env)
    return Path(os.path.expanduser("~/.hermes/hermes-agent"))

def detect_cap_state(target_dir: Path) -> str:
    """Return one of: "patched", "unpatched", "unknown".

    target_dir: a USER-OWNED Hermes checkout (NOT ~/.hermes/hermes-agent in CI).
    Reads agent/skill_utils.py with ast.parse; inspects the
    extract_skill_description function for the literal "60" or the
    MAX_DESCRIPTION_LENGTH reference.
    """
    skill_utils = target_dir / "agent" / "skill_utils.py"
    if not skill_utils.exists():
        return "unknown"
    try:
        tree = ast.parse(skill_utils.read_text())
    except SyntaxError:
        return "unknown"
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_skill_description":
            for sub in ast.walk(node):
                # Look for the comparison: if len(desc) > 60: ...
                if isinstance(sub, ast.Compare):
                    for comparator in sub.comparators:
                        if isinstance(comparator, ast.Constant) and comparator.value == UNPATCHED_CAP:
                            return "unpatched"
                        if isinstance(comparator, ast.Name) and comparator.id == PATCHED_CAP_REFERENCE:
                            return "patched"
    return "unknown"

def should_emit_advisory(advisory_marker: Path) -> bool:
    """Return True iff the advisory marker file is absent (one-time semantics)."""
    return not advisory_marker.exists()

def emit_advisory(advisory_marker: Path) -> None:
    """Best-effort write of the one-time marker. Never raises."""
    try:
        advisory_marker.write_text("advisory shown\n", encoding="utf-8")
    except OSError:
        pass  # best-effort
```

NO `setattr(skill_utils, ...)`. NO rebind of `prompt_builder.extract_skill_description`. NO in-process mutation of any Hermes module. The hook NEVER imports `agent.skill_utils`. The static-AST detection NEVER mutates the target. The actual cap-raise is Script #1's job.

## TDD test list

### _advisory
- `test_detect_cap_state_patched` — fixture checkout with `MAX_DESCRIPTION_LENGTH` in the comparator; returns `"patched"`.
- `test_detect_cap_state_unpatched` — fixture checkout with literal `60`; returns `"unpatched"`.
- `test_detect_cap_state_unknown_no_file` — missing `agent/skill_utils.py`; returns `"unknown"`.
- `test_detect_cap_state_unknown_syntax_error` — corrupted file; returns `"unknown"`.
- `test_advisory_no_setattr_on_skill_utils` — assert the `_advisory` module does NOT import or setattr on `agent.skill_utils`.
- `test_advisory_does_not_read_hermes_agent_unless_env_set` — without `HERMES_HERMES_AGENT_TARGET`, the resolver returns the live path; the test asserts the resolver is invoked with the env var to avoid the live read in CI.
- `test_resolve_target_dir_prefers_env_var` — `HERMES_HERMES_AGENT_TARGET=/tmp/x` → resolver returns `/tmp/x`.
- `test_emit_advisory_idempotent` — first call emits; marker file written; second call does NOT emit.
- `test_emit_advisory_re_emits_when_marker_deleted` — delete marker; next call emits.
- `test_emit_advisory_swallows_oserror` — unwritable marker path → no exception raised.
- `test_advisory_module_does_not_register_skill` — assert the `_advisory` module has no `ctx.register_skill` call site (the plugin is advisory only).

### plugin.yaml manifest (validator acceptance)
- `test_plugin_manifest_is_yaml_not_json` — the bundled manifest at `src/hermes_skill_creator_plugin/plugin.yaml` exists; `plugin.json` does NOT exist at the plugin root. Parses as YAML, not JSON.
- `test_plugin_manifest_passes_hermes_parser` — invokes `hermes_cli.plugins._parse_manifest(bundled_plugin_yaml_path)` (in-process import, no subprocess) and asserts the parsed `PluginManifest` is well-formed (name matches `^[a-z0-9][a-z0-9._-]*$`, description len <= 1024, `provides_hooks` is a list containing `on_session_start`). This is the AC-1.1 + AC-1.5 acceptance gate that the bundled manifest passes the live validator.
- `test_plugin_manifest_has_no_kind_field` — asserts the bundled `plugin.yaml` does NOT carry a `kind` field.
- `test_plugin_manifest_has_no_entry_points` — asserts the bundled `plugin.yaml` does NOT carry an `entry_points` map (the load model is one `register(ctx)` in `__init__.py`, not an entry-point map).
- `test_register_callable_in_package_init` — `from hermes_skill_creator_plugin import register` resolves to a callable taking a single `ctx` arg.

### register(ctx) wiring
- `test_register_calls_ctx_register_hook_once` — single `ctx.register_hook('on_session_start', cb)` call; no other `ctx.*` methods invoked.
- `test_register_does_not_call_ctx_register_skill` — assert the registered plugin NEVER calls `ctx.register_skill` (the skill is shipped standalone via Script #2).
- `test_register_silent_when_cap_patched` — fixture: target_dir has patched agent/skill_utils.py; no advisory log, no marker write.
- `test_register_emits_advisory_when_cap_unpatched` — fixture: target_dir has unpatched agent/skill_utils.py; `HERMES_HERMES_AGENT_TARGET` set; first call emits, marker written; second call does not.
- `test_register_silent_when_target_unknown` — missing target_dir; no advisory, no marker write.

### Bilingual
- `test_advisory_log_contains_en_and_hu` — the cap-state advisory contains both `[en]` and `[hu]` markers.

### Coverage
- 100% line + branch on `_advisory.py`, `__init__.py`, `_scope.py`, `_subprocess.py`. Every error path covered. The one-time-marker branches and the `unknown`/`patched`/`unpatched` tri-state are all exercised.

## Fix ledger

- Fixes [blocker B3] manifest format — switched from `plugin.json` to `plugin.yaml`; removed `entry_points` map; removed `kind` field; uses single `register(ctx)` in `__init__.py`.
- Fixes [blocker B3] removed `skill_register.py` entirely; the plugin no longer calls `ctx.register_skill` (registration does not achieve index visibility; the skill is shipped standalone via Script #2's flat-path `do_install`).
- Fixes [blocker B4] removed `skills/skill-creator/` subdirectory from the plugin layout; the skill is a STANDALONE deliverable at the worktree root, shipped/installed via the hub, and is NOT bundled, contained, or owned by the plugin.
- Fixes [blocker B4] AC-1.4 — plugin is advisory-only (static-AST cap-state detection + one-time bilingual log); the skill is installed via Script #2's flat-path `do_install` into `~/.hermes/skills/skill-creator/`.
- Fixes [blocker B1.2] cap-raise mechanism — the static-AST detection NEVER mutates the target; the actual cap-raise is Script #1's job.
- Fixes [blocker from safety lens] 03-plugin-spec.md runtime monkey-patch — DELETED.
- Fixes [blocker from overview lens] AC 4.10 active-cap detection — Script #1 owns the actual cap mutation; the plugin only detects.

## Cross-references

- `04-script-1-patch.md` — Script #1 performs the actual cap-raise (AST rewrite of `agent/skill_utils.py`).
- `05-script-1-task-e-toggle.md` — Script #1 also patches the Task E site in Hermes.
- `06-script-2-profiles.md` — Script #2 ships the standalone `skill-creator` skill into `~/.hermes/skills/skill-creator/` via `do_install`. The plugin does NOT own the skill.
- `07-skill-creator-migration.md` — the migrated skill body (lives at `skills/skill-creator/` at the worktree root).
- `10-toolchain-and-conventions.md` — `[project.scripts]` does NOT include an installer entry point for the plugin; the plugin has no `python -m ... install` subcommand. The plugin is installable via the standard Hermes plugin loader (pip-installed, `plugin.yaml` discovered).

## Decisions & evidence

### D1. Plugin manifest is `plugin.yaml`; NO `plugin.json`, NO `entry_points` map, NO `kind` field (B3)
- **Decision**: the plugin ships ONE manifest file at `src/hermes_skill_creator_plugin/plugin.yaml` with fields `name`, `version`, `description`, `author`, `provides_hooks`. No `kind` field (the only known valid value per `pluginAuthoring.json` is `backend`, which is wrong for a hook+skill plugin). No `entry_points` map.
- **Rationale**: `hermes_cli/plugins.py` requires `plugin.yaml`; an `entry_points` map would create a second wiring path; `kind: backend` would mis-declare the plugin.
- **Evidence**: V3 [blocker B3 / major M2]; `hermes_cli/plugins.py` (anchor: directory plugin must contain `plugin.yaml`); AC-1.1 + AC-1.5 in 01. Confidence: verified-from-source.

### D2. `skill_register.py` is REMOVED (B3)
- **Decision**: there is NO `skill_register.py` in the plugin package. The plugin's `register(ctx)` does NOT call `ctx.register_skill`.
- **Rationale**: `register_skill` does not place the skill in `<available_skills>`. The migrated skill is shipped standalone via Script #2's flat-path install.
- **Evidence**: V3 [blocker B3]; 03 §Plugin layout; AC-1.4 in 01. Confidence: verified-from-source.

### D3. Plugin does NOT own skill files; `skills/skill-creator/` is standalone at the worktree root (B4)
- **Decision**: `src/hermes_skill_creator_plugin/` does NOT contain a `skills/` subdirectory. The migrated skill lives at `<worktree>/skills/skill-creator/` (sibling of `src/`), and is shipped flat into `~/.hermes/skills/skill-creator/` via Script #2's `do_install`.
- **Rationale**: a plugin-owned skill cannot be installed at the flat path that achieves `<available_skills>` visibility, and embedding the skill in the plugin violates Brief §5.4 + §6.D.6 + AC-4.1.
- **Evidence**: V3 [blocker B4]; AC-1.4 + AC-4.1 in 01; PC4 in 12. Confidence: verified-from-source.

### D4. Cap-state detection is static-AST, advisory only
- **Decision**: `_advisory.detect_cap_state(target_dir)` runs `ast.parse` over `agent/skill_utils.py` and inspects `extract_skill_description`'s comparator. It NEVER imports `agent.skill_utils` at module level and NEVER performs `setattr` on any Hermes module.
- **Rationale**: a runtime `setattr(agent.skill_utils, "MAX_DESCRIPTION_LENGTH", 1024)` would mutate the installed Hermes (forbidden by the HARD safety rule); static-AST detection is side-effect-free.
- **Evidence**: V3 [refuted claim 1] (runtime monkey-patch rejected); 03 §Cap-raise mechanism; AC-1.3 in 01; `test_advisory_no_setattr_on_skill_utils` in this file. Confidence: verified-from-source.

### D5. Pin values for the unpatched vs patched comparator
- **Decision**: `UNPATCHED_CAP = 60` (literal `60` in the comparator) and `PATCHED_CAP_REFERENCE = "MAX_DESCRIPTION_LENGTH"` (the patched constant name) are pinned in `_advisory.py`.
- **Rationale**: the AST must distinguish "patched" from "unpatched" by matching either the literal `60` or the `MAX_DESCRIPTION_LENGTH` reference in the `Compare` node's comparators.
- **Evidence**: `~/.hermes/hermes-agent @ 36ae958473b8530ffb1a395c4944b8cdbcae82fe` — `agent/skill_utils.py:653` (unpatched) and `tools/skills_tool.py:98` (the patched-cap constant). Confidence: verified-from-source.

<!-- end of file: 253 lines (budget 260) -->
