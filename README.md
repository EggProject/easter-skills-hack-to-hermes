# easter-hermes-sorry-skills

[Magyar verzio](README.hu.md) | [Docs](docs/README.md) | [License](LICENSE)

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![uv managed](https://img.shields.io/badge/uv-managed-green.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)
![Hermes](https://img.shields.io/badge/Hermes-30e947e0a-purple.svg)

> Supported Hermes commit: `30e947e0a`
> (`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

## What It Does

`easter-hermes-sorry-skills` is a small Hermes companion package for skill
loading and skill-authoring workflows.

| Area | Purpose |
| --- | --- |
| 🧩 Hermes plugin | Registers `on_session_start` and `pre_llm_call` hooks. |
| 🪝 WOW skill hook | Reminds the model about relevant enabled skills before an LLM call. |
| 🩹 Hermes patcher | Updates the pinned Hermes checkout so skill descriptions and prompts behave better. |
| 🧰 Migrated skill | Ships a Hermes-compatible `skills/skill-creator/` directory. |
| 📊 Reporter | Shows enabled skill metadata and token/cost surface without changing config. |

The plugin does not own or bundle the migrated `skill-creator` skill. The skill
is a separate top-level artifact under `skills/skill-creator/`.

## Quick Start

```bash
uv sync --locked --all-extras --dev

# Validate a pinned Hermes checkout without writing.
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a

# Inspect enabled skill usage.
uv run --locked easter-hermes-sorry-skills-report
```

The patcher writes by default. Use `--dry-run` for validation and review before
an operator applies the same command without `--dry-run`.

## Commands

| Command | Writes? | Notes |
| --- | --- | --- |
| `easter-hermes-sorry-skills-patch-hermes` | Yes, unless `--dry-run` is set | Patches a Hermes checkout. |
| `easter-hermes-sorry-skills-report` | No, except operator-chosen JSON output | Reads profiles and skill metadata. |

## Configure the Skill Hook

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

`adaptive` mode runs on each turn and injects a short reminder only when the
current user message matches enabled skill names or descriptions. Already loaded
skills are treated as loaded context and are not re-recommended strongly.

## Documentation

| Topic | Link |
| --- | --- |
| 🧭 Documentation index | [docs/README.md](docs/README.md) |
| ⚡ Getting started | [docs/getting-started.md](docs/getting-started.md) |
| 🧰 Commands | [docs/commands.md](docs/commands.md) |
| 🧩 Plugin and hooks | [docs/plugin.md](docs/plugin.md) |
| 🩹 Patching Hermes | [docs/patching.md](docs/patching.md) |
| 🛠️ Skill creator | [docs/skill-creator.md](docs/skill-creator.md) |
| 📦 Operations and release | [docs/operations.md](docs/operations.md) |
| 🧪 Development | [docs/development.md](docs/development.md) |
| 🧾 Migration notes | [docs/migration-notes.md](docs/migration-notes.md) |
| 🪝 Hook flowcharts | [docs/wow-skills-flowcharts.md](docs/wow-skills-flowcharts.md) |

## Quality Gate

```bash
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
scripts/build-release.sh
```

The Python test gate enforces 100% branch coverage through `pyproject.toml`.
Release artifacts are written to `dist/`, and `dist/` should contain the latest
build after release-facing files change.

## License

The repository contains an MIT license in [LICENSE](LICENSE). The
`pyproject.toml` metadata keeps an internal packaging marker; the repository
license file is the source license for redistribution.
