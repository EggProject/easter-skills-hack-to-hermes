# easter-hermes-sorry-skills

[Magyar verzio](README.hu.md) | [Docs](docs/README.md) | [License](LICENSE)

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![Hermes plugin](https://img.shields.io/badge/Hermes-plugin-purple.svg)
![Release artifact](https://img.shields.io/badge/release-.pyz%20%2B%20wrappers-green.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

> Supported Hermes commit: `30e947e0a`
> (`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

## What It Does

`easter-hermes-sorry-skills` is a small compatibility bundle for making Hermes
Agent skill usage behave more like the expected Claude-style skill workflow. It
has four parts:

| Part | Runtime | Purpose |
| --- | --- | --- |
| 🩹 Hermes patcher | Release `.pyz` + shell wrapper | Updates the supported Hermes checkout so skill descriptions and skill-authoring prompts behave correctly. |
| 🧩 Hermes plugin | Hermes' plugin loader | Registers `on_session_start` and `pre_llm_call` hooks so Hermes gets short skill reminders before LLM calls. |
| 🛠️ Migrated skill | Hermes skill system | Replaces the installed OpenAI `skill-creator` skill with this Hermes-compatible version. |
| 📊 Reporter | Release `.pyz` + shell wrapper | Prints read-only skill metadata and token surface diagnostics. |

The plugin and the migrated `skill-creator` are intentionally separate. The
plugin only reminds Hermes when `skill-creator` or another enabled skill looks
relevant; Hermes still owns actual skill loading.

## User Install

Use the release artifact when you only want to operate the tool. No `uv` setup is
needed for this path.

```bash
tar -xzf dist/easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0

bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
bash scripts/easter-hermes-sorry-skills-report.sh
```

The wrapper scripts resolve `dist/easter-hermes-sorry-skills.pyz` and execute the
packaged Python entry point. They do not create a virtual environment and do not
run `uv`.

Install the plugin payload into Hermes' user plugin directory:

```bash
plugin_backup="$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" ] || \
  mv "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" "$plugin_backup"
mkdir -p "$HOME/.hermes/plugins"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin"
```

Replace Hermes' installed OpenAI `skill-creator` with this Hermes port:

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

## Hermes Plugin Enablement

Hermes plugins are loaded by Hermes, not by the wrapper scripts. Official Hermes
plugin docs describe general plugins as opt-in: a discovered plugin only loads
after its name appears in `plugins.enabled`.

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

`adaptive` mode runs before LLM calls and injects a short reminder only when the
latest user message matches enabled skill names or descriptions.

## Developer Setup

Use `uv` only when you are editing the repository, running tests, or rebuilding
`dist/`.

```bash
uv sync --locked --all-extras --dev
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
scripts/build-release.sh
```

The Python test gate enforces 100% branch coverage through `pyproject.toml`.

## Documentation

| Topic | Link |
| --- | --- |
| 🧭 Documentation index | [docs/README.md](docs/README.md) |
| ⚡ User install | [docs/getting-started.md](docs/getting-started.md) |
| 🧰 Commands | [docs/commands.md](docs/commands.md) |
| 🧩 Plugin and hooks | [docs/plugin.md](docs/plugin.md) |
| 🩹 Patching Hermes | [docs/patching.md](docs/patching.md) |
| 🛠️ Skill creator | [docs/skill-creator.md](docs/skill-creator.md) |
| 📦 Operations and release | [docs/operations.md](docs/operations.md) |
| 🧪 Development | [docs/development.md](docs/development.md) |
| 🧾 Migration notes | [docs/migration-notes.md](docs/migration-notes.md) |
| 🪝 Hook flowcharts | [docs/wow-skills-flowcharts.md](docs/wow-skills-flowcharts.md) |

## License

The repository contains an MIT license in [LICENSE](LICENSE). The
`pyproject.toml` metadata keeps an internal packaging marker; the repository
license file is the source license for redistribution.
