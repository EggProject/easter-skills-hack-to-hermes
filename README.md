# easter-hermes-sorry-skills

> [Magyar verzió](README.hu.md)

[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)](#license)
[![Language: EN](https://img.shields.io/badge/lang-EN-blue.svg)](README.md)
[![Language: HU](https://img.shields.io/badge/lang-HU-blue.svg)](README.hu.md)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-pre--commit%20%2B%20pytest-green.svg)](.github/workflows/ci.yml)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-plugin-blueviolet.svg)](src/easter_hermes_sorry_skills/_register.py)
[![Hermes Hack: deliverable](https://img.shields.io/badge/Hermes%20Hack-deliverable-orange.svg)](#what-is-this)

## What is this

Two coordinated artifacts from the Hermes Skills Hack:

1. **Hermes plugin** (`src/easter_hermes_sorry_skills/`) — emits a one-time bilingual
   advisory when the 60-character skill-description cap is un-raised in your
   Hermes checkout. The plugin is **advisory only**: it never mutates Hermes
   (`_register.py:1-13`).
2. **Migrated `skill-creator`** (`skills/skill-creator/`) — ported from
   Anthropic's `claude-plugins-official` to Hermes (`claude` → `hermes`,
   `.skill` → `.zip`, NDJSON → ShareGPT, plus `compatibility` frontmatter).
   See `skills/skill-creator/SKILL.md:4` for the frontmatter contract.

The package ships three operator-facing CLI entry points (`pyproject.toml:34-36`)
plus the bilingual message catalog at `src/easter_hermes_sorry_skills/i18n/`.

## Quick start

```sh
# 1. Install runtime + dev + extras (locked to uv.lock)
uv sync --locked --all-extras --dev

# 2. Install the unified pre-commit gate (ruff + black + mypy + wemake + pytest)
uv run --locked pre-commit install

# 3. Apply the 8 patches to your Hermes checkout (S1.cap + 6 Task E sites)
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run   # audit first
uv run --locked easter-hermes-sorry-skills-patch-hermes              # then apply
```

After install the three CLIs are on your `PATH`:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-install-profiles`
- `easter-hermes-sorry-skills-report`

## Documentation

| Topic | Link |
|---|---|
| Patches (S1.cap + Task E sites) | [docs/patches.md](docs/patches.md) |
| Skill-creator (migrated) | [docs/skill-creator.md](docs/skill-creator.md) |
| Scripts (the three CLIs) | [docs/scripts.md](docs/scripts.md) |
| Migration log (claude → hermes) | [docs/migration.md](docs/migration.md) |
| Development (uv + pre-commit) | [docs/development.md](docs/development.md) |

## Scripts at a glance

All three entry points are declared in `pyproject.toml:34-36`. Run any of them
through `uv run --locked` so `uv.lock` stays authoritative.

- `easter-hermes-sorry-skills-patch-hermes` — applies the **8 patches**
  (S1.cap + 6 Task E sites + S1.cap skills-prompt-snapshot purge) to your
  Hermes checkout. Defaults to `--target ~/.hermes/hermes-agent`. WRITES by
  default; pass `--dry-run` to audit without writing.
- `easter-hermes-sorry-skills-install-profiles` — **read-only** per-profile
  audit of the migrated `skill-creator` (which profiles have it enabled, which
  skills are visible). Emits tables by default, JSON with `--json`.
- `easter-hermes-sorry-skills-report` — **read-only** usage reporter. Shows
  which skills are currently enabled and what the daily cost surface looks
  like. NO writes, NO config flips.

All three CLIs emit bilingual EN/HU console output (`i18n/messages_en.py`,
`i18n/messages_hu.py`); `--help` carries mirrored English / magyar sections.

## Project layout

```
src/easter_hermes_sorry_skills/   # plugin + the three CLIs
  _register.py                    # hermes_cli.plugins entry point
  _advisory.py                    # static-AST cap detection (no mutation)
  _patcher*.py                    # the 8-patch engine
  cli_patch.py                    # patch-hermes CLI
  cli_profiles.py                 # install-profiles CLI
  cli_report.py                   # report CLI
  i18n/                           # bilingual message catalog (en, hu)
skills/skill-creator/             # migrated skill (Hermes variant)
docs/                             # per-topic docs (see table above)
scripts/                          # bash wrappers around each CLI
```

## Development

This project is **Python 3.14+**, **uv-managed**, and gated by
[pre-commit](https://pre-commit.com/). The strictest hooks (wemake-python-styleguide,
mypy strict, ruff, black) are configured in `.pre-commit-config.yaml` per the
toolchain conventions plan.

```sh
uv sync --locked --all-extras --dev           # one-shot venv bootstrap
uv run --locked pre-commit install            # gate on every commit
uv run --locked pre-commit run --all-files    # full sweep before pushing
uv run --locked pytest                        # run the test suite
uv run --locked ruff check src tests          # lint only
uv run --locked mypy src                      # type-check only
```

CI runs the same `uv sync --all-extras --dev` step (`.github/workflows/ci.yml`),
so a passing local pre-commit run guarantees a passing CI run for the same code.

## License

Proprietary. See [pyproject.toml:7](pyproject.toml). Internal Hermes Skills
Hack deliverable. Not for redistribution outside the hack team without explicit
operator approval.

## Contributing

All path references below point to project-internal files (`.claude/rules/*.md`)
that govern the worktree+PR workflow; they are not external dependencies.

Internal contributions only. Open a feature branch in
`.claude/worktrees/<branch>/`, run the unified pre-commit gate, and submit a PR
to `main`. Direct commits to `main` are forbidden per the worktree + PR workflow
rule (`.claude/rules/worktree-pr-workflow.md`). Follow up every PR until it
merges with green CI (`.claude/rules/follow-up-pr-until-merged.md`,
`.claude/rules/no-pr-merge-without-green-ci.md`).