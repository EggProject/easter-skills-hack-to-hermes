# ⚡ User Install

[Magyar verzio](getting-started.hu.md) | [Docs](README.md)

This page is for operators who want to use the release artifact. It is separate
from [developer setup](development.md).

## Requirements

| Requirement | Why |
| --- | --- |
| Python `>=3.14` | The `.pyz` zipapp runs with system `python3`. |
| Release artifact | Contains wrappers, the Hermes plugin payload, and the migrated `skill-creator`. |
| Hermes checkout | The patch wrapper defaults to Hermes' live checkout path. |

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
plugin/easter-hermes-sorry-skills-plugin/
skills/skill-creator/
README.md
README.hu.md
LICENSE
docs/
```

## 2. Install the Hermes Plugin Payload

```bash
plugin_backup="$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" ] || \
  mv "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" "$plugin_backup"
mkdir -p "$HOME/.hermes/plugins"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin"
```

Hermes directory plugins live under `~/.hermes/plugins/<plugin-name>/` and need
`plugin.yaml` plus `__init__.py`. The release bundle provides that exact
directory under `plugin/easter-hermes-sorry-skills-plugin/`.

## 3. Replace the Installed `skill-creator`

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

This replaces the installed OpenAI `skill-creator` skill with the Hermes port in
this repository. The backup step preserves the previous directory when one
exists.

## 4. Enable the Hermes Plugin

The wrapper scripts run outside Hermes. The plugin runs inside Hermes through
Hermes' plugin loader and must be enabled in Hermes config.

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

## 5. Run the Patcher in Dry-Run Mode

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
```

The wrapper runs the packaged `.pyz`. It does not create `.venv/`, does not
install dependencies, and does not call `uv`.

## 6. Run the Read-Only Report

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

Use `--format json --json PATH` when another tool needs structured output.

## Not Developer Setup

If you need to edit the repository, run tests, or rebuild the release artifact,
switch to [Development](development.md). That is where `uv sync --locked
--all-extras --dev` belongs.
