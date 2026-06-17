<!-- title: Hermes plugin spec (Section 5.1) — no runtime monkey-patch; static-AST advisory; interactive installer -->
<!-- scope: Sec 5.1. Plugin owns skill re-registration + cap-state advisory. The cap-raise is Script #1's job. -->
<!-- ACs covered: AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-4.10 -->

# 03 — Hermes Plugin Spec (§5.1)

## Goal

Ship a Hermes plugin named `hermes-skill-creator-plugin` that:
1. Re-publishes the migrated `skill-creator` skill via `PluginContext.register_skill`.
2. Emits a ONE-TIME bilingual advisory at session start if the cap is detected (via static AST read of the operator's Hermes checkout) as still 60. NO runtime setattr on `agent.skill_utils`. NO file mutation. NO monkey-patch.
3. Conforms to `hermes-agent-skill-authoring` (the validator at `tools/skill_manager_tool.py:_validate_frontmatter`).

> **Hard rule (HARD)**: the plugin NEVER modifies `~/.hermes/hermes-agent` (neither by file write NOR by in-process module mutation). The cap-raise is performed ONLY by Script #1 against a user-owned Hermes checkout (see `04-script-1-patch.md`).

## Plugin layout

```
src/hermes_skill_creator_plugin/
  __init__.py
  plugin.json                   # manifest (required)
  hooks.py                      # on_session_start, register (advisory only)
  _advisory.py                  # static-AST cap detection (NO setattr)
  _scope.py                     # hermes_home_scope context manager
  _subprocess.py                # hermes_subprocess_env() helper
  skill_register.py             # register_skill('skill-creator', ...)
  installer.py                  # python -m hermes_skill_creator_plugin.install
  skills/
    skill-creator/
      SKILL.md                  # migrated skill body
      ... (agents/, scripts/, eval-viewer/, references/, assets/)
  i18n/
    messages_en.py
    messages_hu.py
  tests/  (under tests/, not in the package)
```

There is NO `patch_runtime.py` and NO `resources/extract_skill_description_patched.py`. The runtime monkey-patch is DELETED.

## plugin.json (manifest)

```json
{
  "name": "hermes-skill-creator-plugin",
  "version": "0.1.0",
  "description": "Re-publishes a Hermes-native port of Anthropic's skill-creator and emits a one-time bilingual advisory if the 60-char skill-description cap is un-raised. The cap is raised by Script #1 against a user-owned checkout; this plugin performs NO cap mutation.",
  "author": "kiscsicska",
  "provides_tools": [],
  "provides_hooks": ["on_session_start"],
  "requires_env": [],
  "entry_points": {
    "hooks": "hermes_skill_creator_plugin.hooks:register",
    "register": "hermes_skill_creator_plugin.skill_register:register"
  }
}
```

`requires_env` is intentionally empty. The plugin has NO mandatory env vars. The cap-raise state is detected, not gated.

## Cap-raise mechanism (static-AST, NOT runtime)

`_advisory.py`:

```python
"""Static AST-based cap-state detection. NO runtime mutation."""
from __future__ import annotations
import ast
import os
from pathlib import Path

# Pin: the cap value in the unpatched agent/skill_utils.py.
UNPATCHED_CAP = 60
# Pin: the constant the patched function uses.
PATCHED_CAP_REFERENCE = "MAX_DESCRIPTION_LENGTH"

def detect_cap_state(target_dir: Path) -> str:
    """Return one of: "patched", "unpatched", "unknown".

    target_dir: a USER-OWNED Hermes checkout (NOT ~/.hermes/hermes-agent).
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
```

`hooks.py` (sketch — full impl at Phase 5 / B-plugin):

```python
def register(ctx) -> None:
    target = _resolve_target_dir()  # honors HERMES_HERMES_AGENT_TARGET
    state = detect_cap_state(target)  # static AST, no setattr
    if state != "unpatched": return
    marker = HERMES_HOME / ".hermes_skill_creator_advisory_seen"
    if marker.exists(): return  # one-time semantics
    ctx.log("[en] Skill descriptions capped at 60. Run Script #1. / [hu] ...")
    marker.write_text("advisory shown\n", encoding="utf-8")  # best-effort
```

NO `setattr(skill_utils, ...)`. NO rebind of `prompt_builder.extract_skill_description`. NO in-process mutation of any Hermes module. The hook NEVER imports `agent.skill_utils`.

## Skill registration (no precedence ambiguity)

`skill_register.py` (sketch — full impl at Phase 5 / B-plugin):

```python
def register(ctx) -> None:
    skill_md = PACKAGE_ROOT / "skills" / "skill-creator" / "SKILL.md"
    if not skill_md.exists(): return _log_missing(ctx)
    try:
        post = frontmatter.load(skill_md)  # python-frontmatter; robust to ---, BOM
    except Exception as exc:
        return _log_parse_error(ctx, exc)
    description = str(post.metadata.get("description", "")).strip()
    if not description: return _log_no_description(ctx)
    body = skill_md.read_text(encoding="utf-8")
    category = post.metadata.get("metadata", {}).get("hermes", {}).get("category", "authoring")
    ctx.register_skill(name="skill-creator", description=description, body=body, category=category)
    ctx.log(ADVISORY_SKILL_PRESENT_EN + " / " + ADVISORY_SKILL_PRESENT_HU)
```

The plugin ALWAYS registers from its BUNDLED copy. If the user has a `~/.hermes/skills/<cat>/skill-creator/` of their own, that file is the authoritative one for `skill_view` (the runtime skill loader), but the system-prompt index block uses the plugin's bundled description. This is documented in 12-risks-and-open-questions.md (R5).

## Installer (interactive by default)

`installer.py` (sketch — full impl at Phase 5 / B-plugin):

```python
def main() -> None:
    args = parse_args()  # --hermes-home, --yes, --no-install-skill, --with-extended-description
    target = args.hermes_home or Path(os.environ.get("HERMES_HOME", str(REAL_HERMES_HOME)))
    safety_check(target, args.yes)  # TTY confirm OR exit 5
    with hermes_home_scope(target):
        install_plugin(target)       # sha256-based idempotency; OK: már telepítve
        if not args.no_install_skill:
            install_skill(target, args.with_extended_description)  # active-cap guard
    print("[en] OK: install complete / [hu] OK: telepítés kész")

def safety_check(target, yes):
    if target.resolve() == REAL_HERMES_HOME.resolve() and not yes:
        if not sys.stdin.isatty(): sys.exit(5)  # non-TTY, no --yes -> abort
        ans = input("[en] Install to {target}? [y/N] / [hu] ...? [i/N] ")
        if ans.lower() not in {"y","i","yes"}: sys.exit(5)

def install_skill(target_home, with_extended):
    cap_state = detect_cap_state(Path(os.environ.get("HERMES_HERMES_AGENT_TARGET", "~/.hermes/hermes-agent")))
    skill_md = SKILL_BUNDLE / ("SKILL.md.short" if with_extended and cap_state != "patched" else "SKILL.md")
    description = frontmatter.load(skill_md).metadata.get("description", "")
    active_cap = 1024 if cap_state == "patched" else 60
    if len(description) > active_cap:
        print(f"[en] description {len(description)} > active cap {active_cap}; refusing / [hu] ...",
              file=sys.stderr)
        sys.exit(1)  # AC-4.10
    # Atomic copy (write to .tmp + os.replace); on exception, rollback.
```

The installer uses `hermes_home_scope` for ALL file writes. It refuses the real `~/.hermes` without `--yes` (or interactive TTY confirmation).

## TDD test list

### _advisory
- `test_detect_cap_state_patched` — fixture checkout with `MAX_DESCRIPTION_LENGTH` in the comparator; returns `"patched"`.
- `test_detect_cap_state_unpatched` — fixture checkout with literal `60`; returns `"unpatched"`.
- `test_detect_cap_state_unknown_no_file` — missing `agent/skill_utils.py`; returns `"unknown"`.
- `test_detect_cap_state_unknown_syntax_error` — corrupted file; returns `"unknown"`.
- `test_advisory_no_setattr_on_skill_utils` — assert the `_advisory` module does NOT import or setattr on `agent.skill_utils`.
- `test_advisory_does_not_read_hermes_agent_unless_env_set` — without `HERMES_HERMES_AGENT_TARGET`, the resolver returns the live path; the test asserts the resolver is invoked with the env var to avoid the live read in CI.
- `test_emit_advisory_idempotent` — first call emits; marker file written; second call does NOT emit.
- `test_emit_advisory_re_emits_when_marker_deleted` — delete marker; next call emits.

### plugin.json manifest (validator acceptance)
- `test_plugin_manifest_passes_hermes_parser` — invokes `hermes_cli.plugins._parse_manifest(bundled_plugin_json)` (in-process import, no subprocess) and asserts the parsed `PluginManifest` is well-formed (name matches `^[a-z0-9][a-z0-9._-]*$`, description len <= 1024, entry_points is a mapping with both `hooks` and `register` keys). This is the AC-1.1 + AC-1.5 acceptance gate that the bundled manifest passes the live validator.
- `test_plugin_manifest_has_no_kind_field` — asserts the bundled `plugin.json` does NOT carry a `kind` field (the only known valid value per `pluginAuthoring.json` is `backend`; per Q-TBD-confirmed the safest default is no `kind` at all).
- `test_plugin_manifest_entry_points_resolve` — asserts the `entry_points.hooks` and `entry_points.register` import paths resolve to a callable `register(ctx)` in the package.

### skill_register
- `test_register_calls_ctx_register_skill` — happy path.
- `test_register_loads_frontmatter_with_python_frontmatter` — uses python-frontmatter; handles embedded `---` in description, BOM, multi-doc.
- `test_register_missing_skill_md_is_noop` — bundled SKILL.md missing → log + return; no `register_skill` call.
- `test_register_missing_frontmatter_logs_and_returns` — no `description` key; log + return.
- `test_register_invalid_frontmatter_logs_and_returns` — python-frontmatter raises; log + return.
- `test_register_uses_bundled_not_user_local` — assertion: even when `~/.hermes/skills/skill-creator/` exists, the register call uses the bundled frontmatter (R5).

### installer
- `test_install_respects_hermes_home_override` — `HERMES_HOME=tmp_path`; all writes under `tmp_path`.
- `test_install_aborts_without_yes_on_real_home` — `HERMES_HOME=~/.hermes`, no `--yes`, no TTY → exit 5.
- `test_install_yes_bypasses_prompt_on_real_home` — `--yes` → proceeds.
- `test_install_idempotent_second_run_exits_0` — second run with sha256 match; `OK: already installed / OK: már telepítve`.
- `test_install_collision_detected` — pre-existing target with different sha256 → log advisory, do not overwrite.
- `test_install_partial_state_rollback` — interrupt mid-copy; assert no partial directory.
- `test_install_refuses_when_description_exceeds_active_cap` — cap_state=unpatched, description>60 → exit 1 with bilingual error.
- `test_install_with_extended_description_uses_short_when_cap_unpatched` — `--with-extended-description` + cap_state=unpatched → uses `SKILL.md.short` (the <=60-char variant).
- `test_install_with_extended_description_uses_full_when_cap_patched` — `--with-extended-description` + cap_state=patched → uses `SKILL.md` (the <=1024-char variant).
- `test_install_uses_hermes_home_scope` — assert all file writes happen inside `hermes_home_scope`; if the scope exits early, no writes.

### hooks
- `test_hooks_does_not_setattr_on_skill_utils` — assert the hooks module has NO import-time mutation of `agent.skill_utils`.
- `test_hooks_emits_advisory_when_cap_unpatched` — fixture: target_dir has unpatched agent/skill_utils.py; `HERMES_HERMES_AGENT_TARGET` set; first call emits, marker written; second call does not.
- `test_hooks_silent_when_cap_patched` — fixture: target_dir has patched agent/skill_utils.py; no advisory.

### Bilingual
- `test_register_log_is_bilingual` — log contains both `[en]` and `[hu]` markers.
- `test_advisory_message_contains_en_and_hu` — the cap-state advisory contains both.
- `test_installer_help_is_bilingual` — `--help` has both "Usage (English)" and "Használat (magyar)" sections.

### Coverage
- 100% line + branch on `_advisory.py`, `hooks.py`, `skill_register.py`, `installer.py`, `_scope.py`, `_subprocess.py`. Every `argparse` choice exercised. Every error path covered. The TTY confirmation branch is exercised by mocking `sys.stdin.isatty` and `input`.

## Fix ledger

- Fixes [blocker from safety lens] 03-plugin-spec.md runtime monkey-patch — DELETED.
- Fixes [blocker from safety lens] 03-plugin-spec.md plugin installer no TTY gate — added.
- Fixes [blocker from overview lens] AC 4.10 active-cap detection — added.
- Fixes [major] skill_register split("---")[1]) naive parser — replaced with python-frontmatter.
- Fixes [major] install does not respect HERMES_HOME — added.
- Fixes [minor] manifest kind=skill_authoring — pinned (TBD confirmation deferred to 12-Q-TBD; integration test runs the actual validator).

<!-- end of file: 235 lines (budget 220) -->
