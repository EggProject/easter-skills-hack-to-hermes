# ⚡ Getting Started

[Magyar verzio](getting-started.hu.md) | [Docs](README.md)

## Prerequisites

| Tool | Why |
| --- | --- |
| Python `>=3.14` | Project runtime and release zipapp target. |
| `uv` | Virtual environment, dependency sync, and locked command runner. |
| Git | Branching, PR workflow, and release metadata. |
| Hermes checkout | Validate against commit `30e947e0a`. |

## 1. Prepare the Project

```bash
uv sync --locked --all-extras --dev
```

`uv run --locked` refuses to update the lockfile implicitly. That keeps local
commands aligned with CI and the committed `uv.lock`.

## 2. Validate Hermes Without Writing

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

Review the printed plan. Drift findings mean the patch anchors no longer match
the supported Hermes source and must be fixed before apply mode is used.

## 3. Enable the Plugin

Add the package as a Hermes plugin and configure the hook in `config.yaml`:

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
```

The hook reads enabled skills through the Hermes runtime API. It does not scan
profile directories itself.

## 4. Inspect Skill State

```bash
uv run --locked easter-hermes-sorry-skills-report
```

Use `--format json --json PATH` when another tool needs structured output.

## Next

- [Commands](commands.md) lists all flags.
- [Plugin and hooks](plugin.md) explains `adaptive`, `first`, and `off`.
- [Patching Hermes](patching.md) explains patch sites and dry-run output.

