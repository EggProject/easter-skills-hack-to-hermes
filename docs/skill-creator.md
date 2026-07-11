# 🛠️ Skill Creator

[Magyar verzio](skill-creator.hu.md) | [Docs](README.md)

## Location

The migrated skill lives at:

```text
skills/skill-creator/
```

It is intentionally outside the plugin package. Hermes should see it as a flat
skill named `skill-creator`, not as a plugin-owned bundled skill.

## Install Into Hermes

The release bundle includes this directory:

```text
skills/skill-creator/
```

Use it to replace Hermes' installed OpenAI `skill-creator` skill:

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

The backup step keeps the previous OpenAI version available for manual rollback.

## Purpose

Use the skill when a model needs to create, improve, package, or evaluate a
skill. The Hermes port keeps the upstream skill-authoring workflow but replaces
Claude-specific commands and packaging assumptions with Hermes-compatible ones.

## What Changed In The Port

| Upstream assumption | Hermes port |
| --- | --- |
| `claude` command examples | Hermes command examples. |
| `.skill` package target | `.zip` package target. |
| Claude session output | Hermes-compatible output handling. |
| Claude nesting guard | Hermes subprocess helper. |

## Relationship To The Plugin

The plugin may remind the model that `skill-creator` is relevant, but the skill
content is loaded through Hermes' normal skill system. This separation matters:
plugin hooks manage reminders, while Hermes owns actual skill loading.

## Related Docs

- [Plugin and hooks](plugin.md)
- [WOW skill flowcharts](wow-skills-flowcharts.md)
- [Migration notes](migration-notes.md)
