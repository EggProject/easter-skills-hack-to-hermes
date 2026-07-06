# ⚡ User Install

[Magyar verzio](getting-started.hu.md) | [Docs](README.md)

This page is for operators who want to use the release artifact. It is separate
from [developer setup](development.md).

## Requirements

| Requirement | Why |
| --- | --- |
| Python `>=3.14` | The `.pyz` zipapp runs with system `python3`. |
| Release artifact | Contains `dist/easter-hermes-sorry-skills.pyz` and shell wrappers. |
| Hermes checkout | Patch dry-run target, usually `/tmp/hermes-30e947e0a` for validation. |

No `uv` command is required for user install.

## 1. Extract the Release Bundle

```bash
tar -xzf dist/easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0
```

The bundle contains:

```text
dist/easter-hermes-sorry-skills.pyz
scripts/easter-hermes-sorry-skills-patch-hermes.sh
scripts/easter-hermes-sorry-skills-report.sh
README.md
README.hu.md
```

## 2. Run the Patcher in Dry-Run Mode

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

The wrapper runs the packaged `.pyz`. It does not create `.venv/`, does not
install dependencies, and does not call `uv`.

## 3. Run the Read-Only Report

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

Use `--format json --json PATH` when another tool needs structured output.

## 4. Enable the Hermes Plugin Separately

The CLI bundle and the Hermes plugin are different install surfaces. The wrapper
scripts run outside Hermes. The plugin runs inside Hermes through Hermes' plugin
loader and must be discovered and enabled there.

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

See [Plugin and hooks](plugin.md) for the runtime behavior.

## Not Developer Setup

If you need to edit the repository, run tests, or rebuild the release artifact,
switch to [Development](development.md). That is where `uv sync --locked
--all-extras --dev` belongs.
