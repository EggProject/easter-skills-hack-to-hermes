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

## Configuration

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

