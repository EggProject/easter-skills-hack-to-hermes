# 🧩 Plugin and Hooks

[Magyar verzio](plugin.hu.md) | [Docs](README.md)

## Runtime Surface

The plugin manifest is `src/easter_hermes_sorry_skills/plugin.yaml`.

```yaml
name: easter-hermes-sorry-skills-plugin
provides_hooks:
  - on_session_start
  - pre_llm_call
```

`register(ctx)` wires both hooks into Hermes. The package-level plugin does not
register the migrated `skill-creator` skill.

This page describes runtime enablement only. The release wrapper scripts are
covered in [User install](getting-started.md) and run outside Hermes.

## Discovery and Enablement

Hermes discovers third-party general plugins from plugin directories or Python
package entry points. A directory plugin belongs under
`~/.hermes/plugins/<plugin-name>/` and must contain `plugin.yaml` plus
`__init__.py`. A discovered general plugin is opt-in: Hermes loads it only after
the plugin key is listed under `plugins.enabled`.

The release bundle includes the ready-to-copy directory at:

```text
plugin/easter-hermes-sorry-skills-plugin/
```

Copy that directory to:

```text
~/.hermes/plugins/easter-hermes-sorry-skills-plugin/
```

Then enable `easter-hermes-sorry-skills-plugin` in Hermes config.

## `on_session_start`

This hook checks whether the target Hermes checkout still has the old skill
description cap. It emits an advisory only; the cap is changed by the patcher,
not by the plugin.

## `pre_llm_call`

This hook can inject a short, ephemeral skill reminder before Hermes calls the
LLM. It is intentionally small:

1. Load `skill_hook` config.
2. Ask Hermes for enabled skills through the runtime API.
3. Match the latest user message against skill names and descriptions.
4. Detect skills that are already loaded in the conversation history.
5. Inject a shortlist only when a useful match exists.

Full decision charts and chat examples are preserved in
[WOW skill flowcharts](wow-skills-flowcharts.md).

## Plugin-Owned Configuration

`plugins.enabled` controls whether Hermes loads the plugin. The nested
`plugins.entries.easter-hermes-sorry-skills-plugin.skill_hook` section is the
configuration this plugin reads for its own hook behavior.

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
  entries:
    easter-hermes-sorry-skills-plugin:
      skill_hook:
        enabled: true
        mode: adaptive
        output: shortlist
        top_k: 3
        min_score: 2
        log_level: INFO
```

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Enables or disables the hook. |
| `mode` | `adaptive` | `adaptive`, `first`, or `off`. |
| `output` | `shortlist` | `shortlist`, `names`, or `index`. |
| `top_k` | `3` | Maximum number of matching skills in the reminder. |
| `min_score` | `2` | Minimum match score before injection. |
| `log_level` | `INFO` | Standard Python logging level. |

The repository does not read a root-level
`easter-hermes-sorry-skills-plugin:` config key.

## Modes

| Mode | Behavior |
| --- | --- |
| `adaptive` | Runs on every turn, injects only when the message matches enabled skills. |
| `first` | Runs only on the first LLM call of the session. |
| `off` | Skips the hook entirely. |

## Output Formats

| Output | Behavior |
| --- | --- |
| `shortlist` | Includes skill names and short reasons. |
| `names` | Includes only matching skill names. |
| `index` | Includes a compact skill index. |

## Debugging

Set `log_level: DEBUG` while validating hook behavior. Keep production config at
`INFO` unless diagnostics are needed.

## References

- Hermes Build a Plugin guide: plugin directories, `register(ctx)`, and
  `ctx.register_hook(...)`.
- Hermes Plugins feature docs: plugin discovery sources and `plugins.enabled`.
- Hermes Hooks feature docs: plugin hooks and `pre_llm_call` behavior.
