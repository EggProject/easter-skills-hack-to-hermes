# easter-hermes-sorry-skills

> [Magyar verzió](README.hu.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: EN](https://img.shields.io/badge/lang-EN-blue.svg)](README.md)
[![Language: HU](https://img.shields.io/badge/lang-HU-blue.svg)](README.hu.md)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-pre--commit%20%2B%20pytest-green.svg)](.github/workflows/ci.yml)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-plugin-blueviolet.svg)](src/easter_hermes_sorry_skills/_register.py)
[![Hermes Hack: deliverable](https://img.shields.io/badge/Hermes%20Hack-deliverable-orange.svg)](#what-is-this)

## What is this

Two coordinated artifacts from the Hermes Skills Hack:

1. **Hermes plugin** (`src/easter_hermes_sorry_skills/`) — emits a one-time
   language-specific advisory when the 60-character skill-description cap is un-raised in your
   Hermes checkout. The plugin is **advisory only**: it never mutates Hermes
   (`_register.py:1-13`).
2. **Migrated `skill-creator`** (`skills/skill-creator/`) — ported from
   Anthropic's `claude-plugins-official` to Hermes (`claude` → `hermes`,
   `.skill` → `.zip`, NDJSON → ShareGPT, plus `compatibility` frontmatter).
   See `skills/skill-creator/SKILL.md:4` for the frontmatter contract.

The package ships three operator-facing CLI entry points (`pyproject.toml:34-36`)
plus the EN/HU message catalog at `src/easter_hermes_sorry_skills/i18n/`.

## Quick start

```sh
# 1. Install the package (3 modes: development / release artifact / Hermes plugin)
#    See: docs/installation.md
uv sync --locked --all-extras --dev
uv run --locked pre-commit install

# 2. Patch audit (dry-run)
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run

# 3. Patch apply
uv run --locked easter-hermes-sorry-skills-patch-hermes

# 4. Smoke test
uv run --locked easter-hermes-sorry-skills-report
```

Detailed installation guide: [docs/installation.md](docs/installation.md).
Detailed usage guide: [docs/usage.md](docs/usage.md).

After install the three CLIs are on your `PATH`:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-report`

## Documentation

| Topic | Link |
|---|---|
| Installation (3 modes) | [docs/installation.md](docs/installation.md) |
| Installation: development | [docs/installation-dev.md](docs/installation-dev.md) |
| Installation: release artifact | [docs/installation-release.md](docs/installation-release.md) |
| Installation: Hermes plugin | [docs/installation-hermes.md](docs/installation-hermes.md) |
| Verification + lifecycle | [docs/installation-verify.md](docs/installation-verify.md) |
| Usage (quick start + workflows) | [docs/usage.md](docs/usage.md) |
| Common workflows + troubleshooting | [docs/workflows.md](docs/workflows.md) |
| Patches (S1.cap + Task E sites) | [docs/patches.md](docs/patches.md) |
| Skill-creator (migrated) | [docs/skill-creator.md](docs/skill-creator.md) |
| Scripts (the three CLIs) | [docs/scripts.md](docs/scripts.md) |
| Migration log (claude → hermes) | [docs/migration.md](docs/migration.md) |
| Development (uv + pre-commit) | [docs/development.md](docs/development.md) |

## Scripts at a glance

All three entry points are declared in `pyproject.toml:34-36`. Run any of them
through `uv run --locked` so `uv.lock` stays authoritative.

- `easter-hermes-sorry-skills-patch-hermes` — applies the **7 patch sites**
  (S1.cap + 6 Task E sites + S1.cap skills-prompt-snapshot purge) to your
  Hermes checkout. Defaults to `--target ~/.hermes/hermes-agent`. WRITES by
  default; pass `--dry-run` to audit without writing.
- `easter-hermes-sorry-skills-report` — **read-only** usage reporter. Shows
  which skills are currently enabled and what the daily cost surface looks
  like. NO writes, NO config flips.

### `--dry-run` and the dry-run plan

`easter-hermes-sorry-skills-patch-hermes --dry-run` audits every planned
patch without writing a single byte to the target. The output is a
single-language **plan** selected by `--lang` that the operator reads before
deciding to apply:

```text
◇ plan for /path/to/target:
• would patch: agent/skill_utils.py (site S1.cap)
  line 688: - old line content
  line 688: + new line content
◇ 7 patch(es) would be applied
⚠ --dry-run mode, 7 patches were NOT applied
```

Apply mode emits the same plan body, but the trailing tail switches to
the "applied" message instead of the dry-run warning:

```text
✓ 7 patches applied
```

**Soft safety.** The hermes-agent checkout (`~/.hermes/hermes-agent`) is
the default target. Dry-run emits a warning and prints the plan so the
operator can audit the planned changes before deciding to apply. The target
file hash stays byte-identical (verified by the
`test_cli_dry_run_no_writes_to_target` unit test). Apply mode is operator
controlled and writes to the resolved target.

All CLI text output is single-language (`--lang en|hu`) and uses the message
modules in `i18n/messages_en.py` and `i18n/messages_hu.py`.

## Project layout

```
src/easter_hermes_sorry_skills/   # plugin + the three CLIs
  _register.py                    # hermes_cli.plugins entry point
  _advisory.py                    # static-AST cap detection (no mutation)
  _patcher*.py                    # the 8-patch engine
  cli_patch.py                    # patch-hermes CLI
  cli_report.py                   # report CLI
  i18n/                           # EN/HU message catalog
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

## Release build

When the code that goes into the release artifact changes (Python source under `src/` or dependencies in `pyproject.toml` / `uv.lock`), you need to rebuild the release artifact:

```bash
scripts/build-release.sh
```

This script performs 3 steps:

1. **`uv sync --locked`** — installs dependencies from `uv.lock` into `.venv/`
2. **`shiv`** — bundles `.venv/lib/python3.14/site-packages/` into `dist/easter-hermes-sorry-skills.pyz` (a single-file standalone zipapp, PEP 441)
3. **`tar -czf`** — packs `dist/*.pyz` + `scripts/` + `README*` into `dist/easter-hermes-sorry-skills-v{VERSION}.tar.gz`

### Distribution

The resulting `dist/easter-hermes-sorry-skills-v{VERSION}.tar.gz` is a self-contained release artifact. Users download it, extract it, and run the wrapper scripts **without installing anything** (no `uv sync`, no `pip install`):

```bash
tar -xzf easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0/
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh [args...]
```

The only requirement on the user's machine is **Python 3.14+** (the `.pyz` shebang points to the system's `python3`).

### Build flags

`scripts/build-release.sh` supports optional flags:

- `--only-shiv` — only build the `.pyz` (skip `tar.gz`)
- `--only-tar` — only build the `tar.gz` (assumes `.pyz` exists)

To clean the `dist/` folder before a rebuild, run `rm -rf dist/` manually (the `--clean` flag was intentionally not added to keep the script non-destructive).

## License

Dual-licensed:

- The [LICENSE](LICENSE) file is the canonical **MIT License** (Copyright © 2026
  eggproject Kft.) — this is the authoritative license for open-source
  redistribution.
- The `pyproject.toml:7` `license = { text = "Proprietary" }` field is the
  operator-managed marker for internal Hermes Hack packaging and distribution
  control. It is NOT a separate license; the MIT text governs all use of the
  source code in this repository.

## Contributing

All path references below point to project-internal files (`.claude/rules/*.md`)
that govern the worktree+PR workflow; they are not external dependencies.

Internal contributions only. Open a feature branch in
`.claude/worktrees/<branch>/`, run the unified pre-commit gate, and submit a PR
to `main`. Direct commits to `main` are forbidden per the worktree + PR workflow
rule (`.claude/rules/worktree-pr-workflow.md`). Follow up every PR until it
merges with green CI (`.claude/rules/follow-up-pr-until-merged.md`,
`.claude/rules/no-pr-merge-without-green-ci.md`).
