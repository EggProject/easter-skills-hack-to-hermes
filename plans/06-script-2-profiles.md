<!-- title: Script #2 — per-profile audit/flip, install migrated skill-creator -->
<!-- scope: Sec 5.3 + Sec 6.C. Run per-profile with hermes_home_scope context manager. -->
<!-- ACs covered: AC-3.1 .. AC-3.9 -->

# 06 — Script #2: Profile Audit / Flip

## Goal

For the `hermes` (default) profile AND every named profile returned by `hermes_cli.profiles.list_profiles()`:
1. Disable `openai` and (if present as a global plugin) `skills`.
2. Install the migrated `skill-creator` via the hub (idempotent: reinstall/upgrade if present).
3. Call `clear_skills_system_prompt_cache(clear_snapshot=True)` after every successful flip.
4. Emit a deterministic JSON report per profile.

Default mode is dry-run. `--apply` performs the writes inside a `hermes_home_scope(path)` context manager that mirrors both the `hermes_home_override` token AND `os.environ['HERMES_HOME']`.

## Flat-install path (why the hub, not the plugin)

`ctx.register_skill` on the plugin context is a namespaced resolver: a plugin-registered skill is reachable ONLY as `'<plugin_name>:<name>'` via an explicit `skill_view()` call. It is NOT written to the flat `~/.hermes/skills/` tree and is NOT listed in the system prompt's `<available_skills>` index. The migration brief + Task E rely on the skill appearing as plain `skill-creator` in the index.

=> Script #2's `do_install` MUST install the skill at the FLAT path `~/.hermes/skills/skill-creator/` (under the scoped HERMES_HOME). The plugin does NOT do this; the plugin is advisory only (see 03).

## Per-profile directory set (source of truth)

`hermes_cli/profiles.py:39-53` defines `_PROFILE_DIRS = {memories, sessions, skills, skins, logs, plans, workspace, cron, home}`. The script walks THIS set per profile. `gateway/` is NOT a subdir — `gateway.pid` is a flat file in the profile root and is read but not listed in the audit.

The audit reads (per profile):
- `config.yaml` (via `hermes_cli.config.load_config()` — NO `path=` arg; called inside `hermes_home_scope`).
- `skills/` tree (walked for `SKILL.md` files; frontmatter parsed with `agent.skill_utils.parse_frontmatter`).
- `gateway.pid` (flat file; stat-only, not parsed).
- The disabled-skill set via `agent.skill_utils.get_disabled_skill_names(platform=None)` — **takes a `platform: str`, NOT a `config` dict** (this is `agent/skill_utils.py:318`, distinct from `hermes_cli.skills_config.get_disabled_skills(config, platform)` at line 27, which is the CLI-side mutator).

## CLI surface

```
Usage (English):
  uv run hermes-skill-creator-profiles [--apply] [--json PATH] [--help]

Használat (magyar):
  uv run hermes-skill-creator-profiles [--apply] [--json PATH] [--help]

Options:
  --apply              Perform the writes; default is dry-run.
  --json PATH          Write the audit report to PATH (default: ./profile-audit.json).
  --yes                Suppress interactive TTY confirmation (default: prompt on TTY).
  --skip-install       Audit only; do not call hub_install_or_update.
  --help               Show this help.
```

## hermes_home_scope context manager (single source of truth)

Defined in `hermes_skill_creator_plugin._scope` and re-used by the installer (file 03) and the integration tests:

```python
@contextmanager
def hermes_home_scope(path: Path):
    """Mirror HERMES_HOME in both the override token AND os.environ.

    Restores BOTH on exit, even on exception.
    """
    from hermes_constants import (
        get_hermes_home_override,
        set_hermes_home_override,
        reset_hermes_home_override,
    )
    prev_override = get_hermes_home_override()  # str | None; None when no override is set
    prev_env = os.environ.get("HERMES_HOME")
    token = set_hermes_home_override(str(path))
    os.environ["HERMES_HOME"] = str(path)
    try:
        yield
    finally:
        # Restore env first (cheap), then the override token.
        if prev_env is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = prev_env
        reset_hermes_home_override(token)
```

Rationale: `hermes_cli.config.load_config()` and `save_config()` anchor on `get_config_path()` which reads the override token, NOT `os.environ['HERMES_HOME']`. `hermes_cli.skills_hub.do_install` (line 478) calls `ensure_hub_dirs()` which writes under the override but `do_install` itself also reads `os.environ['HERMES_HOME']` in some sub-paths (D7 dispute). Both must be mirrored.

## Desired state per profile

```python
@dataclass(frozen=True)
class DesiredState:
    desired_disabled: frozenset[str]   # {"openai"} (or + "skills" if present)
    desired_installed: frozenset[str]  # {"skill-creator"} always
```

`openai` is ALWAYS disabled (it's the upstream source of the original Anthropic skill-creator). `skills` is disabled iff a global `plugins/skills/` artifact exists in the profile. `skill-creator` is installed iff absent under `~/.hermes/profiles/<id>/skills/...` or the default `~/.hermes/skills/...`.

## Shared enabled-detection module (used by Script #2 AND Script #3 reporter)

The reporter (Script #3) and the apply path (Script #2) MUST agree on what "enabled" means for a profile — otherwise Script #3's view of the world drifts from Script #2's flips. The detection logic lives in a small module under the plugin package and is exported as a single function:

```python
# hermes_skill_creator_plugin.enabled_detection

from pathlib import Path
from typing import Optional

def get_enabled_skills(
    profile_path: Path,
    *,
    platform: Optional[str] = None,
) -> frozenset[str]:
    """Return the ENABLED skill names for `profile_path`, honoring:

    1. `config[toggle]` per-skill on/off (the `disabled` list).
    2. Profile- AND platform-scoped conditional exclusions.
    3. `platforms:` frontmatter `disable_if_platform_present` lists.

    Args:
        profile_path: The profile root. `config.yaml` is read from here.
        platform:     Optional platform tag (e.g. "darwin"); `None` means
                      "the current host" (mirrors `hermes_cli.skills_config`).

    Returns:
        Frozen set of skill NAMES (not paths) that are currently ENABLED.
    """
```

Script #2 calls this to compute `installed_now` and the diff between current and desired state. Script #3 (the read-only reporter) calls this to render the per-profile enabled list. Script #2's test suite covers the function; Script #3 re-uses the same fixtures and adds only tokenization + Curator lookup tests.

## Per-profile apply sequence (inside `hermes_home_scope(path)`)

1. `load_config()` → `config: dict`.
2. `disabled_now = get_disabled_skill_names(platform=None)` (from `agent.skill_utils`, NOT `hermes_cli.skills_config`).
3. `installed_now = walk_skills_dir(path / "skills")`.
4. Compute `desired_disabled = disabled_now | {"openai"}` (and union `"skills"` if globally present).
5. Compute `desired_installed = installed_now`; ensure `"skill-creator"` in it.
6. If `--apply`:
   a. `save_disabled_skills(config, sorted(desired_disabled), platform=None)` — POSITIONAL args, real sig `save_disabled_skills(config: dict, disabled: Set[str], platform: Optional[str] = None)` at `hermes_cli/skills_config.py:45`. Returns updated `config`; call `save_config(config)` (no `path=`).
   b. If `"skill-creator"` not in `installed_now` (or version drift detected): `do_install("skill-creator", name_override="", force=True, skip_confirm=True, invalidate_cache=True)` from `hermes_cli.skills_hub`. This writes the skill to `<scoped HERMES_HOME>/skills/skill-creator/` (the FLAT path; see "Flat-install path" above).
   c. `clear_skills_system_prompt_cache(clear_snapshot=True)` — imported from `agent.prompt_builder`:
      ```python
      from agent.prompt_builder import clear_skills_system_prompt_cache
      clear_skills_system_prompt_cache(clear_snapshot=True)
      ```
      Real signature: `clear_skills_system_prompt_cache(*, clear_snapshot: bool = False)` at `agent/prompt_builder.py:1022`. The function EXISTS in the installed Hermes; no fallback path is required. AC-3.8 reflects this (no fallback clause).
7. Append per-profile row to the JSON report.

## Deterministic JSON report

```json
{
  "tool": "hermes-skill-creator-profiles",
  "version": "0.1.0",
  "generated_at": "2026-06-17T00:00:00Z",  // stable ISO 8601 UTC
  "profiles": [
    {
      "profile_name": "hermes",
      "current_disabled": [],
      "current_installed": ["some-other-skill"],
      "desired_disabled": ["openai"],
      "desired_installed": ["skill-creator", "some-other-skill"],
      "diff": {"added_disabled": ["openai"], "removed_disabled": [], "added_installed": ["skill-creator"], "removed_installed": []},
      "actions_taken": [],  // populated when --apply
      "errors": []
    }
  ]
}
```

`generated_at` is stable across runs (the script reads a frozen timestamp from the env or `--frozen-time` flag in tests; in production it is the actual time, but the report is byte-identical ONLY when the input is identical AND `--frozen-time` is set).

## Failure modes

- Hub install fails → per-profile error block in the report; the script CONTINUES to the next profile (idempotent re-run picks up the slack).
- `clear_skills_system_prompt_cache` raises → per-profile warning; the persisted state is left intact; the script logs the cache-clear failure and continues. Exit code 0 if all profiles' desired state is reached; 1 otherwise.
- `set_hermes_home_override` raises → abort the current profile, log, continue to next.

## TDD test list

### hermes_home_scope (three tests for the dual-mirror)
- `test_set_hermes_home_override_called` — enter scope; assert the override token matches the path.
- `test_env_var_mirrored_into_os_environ` — enter scope; assert `os.environ['HERMES_HOME']` equals the path.
- `test_hub_install_reads_mirrored_env` — fake hub reads `os.environ['HERMES_HOME']` and asserts it matches the override (covers D7).
- `test_scope_restores_on_normal_exit` — exit scope; assert override token reset AND `os.environ['HERMES_HOME']` restored.
- `test_scope_restores_on_exception` — raise inside scope; exit; assert both are restored.
- `test_scope_restores_when_env_was_unset_before` — pre-condition: `os.environ` has no `HERMES_HOME`; enter scope; exit; assert `os.environ` STILL has no `HERMES_HOME`.

### Per-profile audit
- `test_audit_default_profile` — fixture with default profile only; assert exactly one row in `profiles[]`.
- `test_audit_named_profiles` — fixture with 3 named profiles; assert 3 rows in stable sorted order.
- `test_audit_empty_profile` — fixture with a profile that has no `skills/` dir; `current_installed == []`; `desired_installed == ["skill-creator"]`.
- `test_audit_drift_detection` — fixture where `openai` is already disabled; assert `added_disabled == []`.
- `test_audit_skills_global_present` — fixture with `plugins/skills/`; assert `desired_disabled` includes `"skills"`.
- `test_audit_skills_global_absent` — fixture without; assert `desired_disabled` does NOT include `"skills"`.
- `test_audit_json_deterministic` — run twice on the same fixture with `--frozen-time`; sha256 of output is byte-identical.
- `test_audit_keys_sorted` — JSON keys are in sorted order (sorted dict insertion).

### Apply path
- `test_apply_disables_openai` — `--apply`; assert `config["skills"]["disabled"]` includes `"openai"` after the run.
- `test_apply_does_not_disable_skills_when_global_absent` — assert `desired_disabled` does NOT include `"skills"`.
- `test_apply_installs_skill_creator_when_absent` — assert `<scoped HERMES_HOME>/skills/skill-creator/SKILL.md` exists after run (FLAT path, not plugin-namespaced).
- `test_apply_idempotent_reinstall` — second `--apply`; assert no re-install (do_install spy called 0 times).
- `test_apply_force_reinstall_on_version_drift` — fixture with old `skill-creator` version; `--apply`; assert do_install called once with `force=True`.
- `test_apply_calls_clear_skills_system_prompt_cache` — spy on `agent.prompt_builder.clear_skills_system_prompt_cache`; assert called once per profile with `clear_snapshot=True`.
- `test_apply_cache_clear_raises_continues_with_warning` — mock cache-clear to raise; assert flip persists; warning logged; script continues to next profile.
- `test_apply_hub_install_fails_continues` — mock `do_install` to raise; assert per-profile error; next profile is processed.
- `test_apply_writes_inside_hermes_home_scope` — assert the entire apply block runs under the context manager; if the manager exits early the apply must abort.
- `test_apply_save_disabled_skills_positional_args` — spy on `save_disabled_skills`; assert it is called with `(config, sorted_set, platform=None)` positionally — NOT with `names=` kwarg.

### Disabled-skill API correctness
- `test_get_disabled_skill_names_uses_agent_skill_utils` — assert the function comes from `agent.skill_utils`, NOT `hermes_cli.skills_config`.
- `test_get_disabled_skill_names_takes_platform_str` — call with `platform=None`; assert it does NOT take a `config=` kwarg.
- `test_save_disabled_skills_uses_hermes_cli_skills_config` — assert the writer is the `hermes_cli.skills_config` mutator (NOT `agent.skill_utils`).
- `test_save_disabled_skills_signature_is_positional` — assert the call passes the disabled set as the 2nd positional arg.

### Shared enabled-detection module
- `test_get_enabled_skills_honors_config_toggle` — fixture with `disabled: [foo]`; assert `foo` is NOT in the result.
- `test_get_enabled_skills_honors_platform_filter` — fixture with `disabled_if_platform: [bar]` for `darwin`; assert `bar` is excluded when `platform="darwin"`.
- `test_get_enabled_skills_honors_conditional_exclusions` — fixture with a per-skill `disable_if` rule; assert the rule wins over the toggle list.
- `test_get_enabled_skills_returns_frozenset` — assert return type is `frozenset[str]`.
- `test_get_enabled_skills_no_fallback_to_real_hermes_home` — assert the function reads ONLY from `profile_path`; it MUST NOT touch `~/.hermes/` (regression sentinel).

### Directory walk correctness
- `test_walks_profile_dirs_set` — fixture; assert the audit walks `{memories, sessions, skills, skins, logs, plans, workspace, cron, home}` (NOT `gateway/` as a subdir).
- `test_gateway_pid_read_as_flat_file` — fixture with `gateway.pid` in profile root; assert it is stat-read but not parsed; no error.
- `test_walks_skills_dir_for_skill_md` — fixture with two skills; assert both are in `current_installed`.

### Bilingual + CLI
- `test_help_is_bilingual` — both "Usage (English)" and "Hasznalat (magyar)" sections; mirrored content.
- `test_dry_run_default_no_writes` — running without `--apply` writes zero bytes to any profile.
- `test_json_output_path_resolved_under_workdir` — `--json ./profile-audit.json` writes under cwd; absolute path also accepted.

### Safety
- `test_apply_refuses_real_hermes_home_without_yes` — when the only profile is the real `~/.hermes` AND there is no `--yes` AND stdout is a TTY: the script must prompt; under non-TTY: the script must abort with exit 5.
- `test_apply_does_not_touch_hermes_agent` — sentinel: sha256 of `~/.hermes/hermes-agent/agent/skill_utils.py` is unchanged after a full run.

## Coverage target

100% line + branch. Every branch of the apply sequence, every error path, every bilingual message reachable. The shared `get_enabled_skills` module is covered by Script #2's tests; Script #3 (reporter) re-uses those fixtures and adds only its own tokenization + Curator-lookup coverage.

<!-- end of file: 185 lines (budget 400) -->
