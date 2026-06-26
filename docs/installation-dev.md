# Installation — Development mode

> [English](installation-dev.md) · [Magyar verzió](installation-dev.hu.md)
> [Back to Installation](installation.md)

Development install is the source-of-truth install: the one the
maintainers run, the one CI runs, and the one you need if you intend
to edit source, run the test suite, or rebuild the release artifact. It
bootstraps a locked `.venv` via `uv` and wires the unified pre-commit
gate (ruff + black + mypy + wemake + flake8 + pytest + bats + shellcheck).

Last verified: 2026-06-27 against `pyproject.toml` (HEAD `76b7cc3`).

---

## Why development install?

The release artifact install (see
[installation-release.md](installation-release.md)) ships a single
`.pyz` plus three bash wrappers — fast, but frozen at build time. The
development install is the inverse trade-off:

| Aspect | Development install | Release artifact install |
|---|---|---|
| Source code + tests + lint | yes (full git checkout) | no (just the `.pyz`) |
| Rebuild the `.pyz` | yes (`scripts/build-release.sh`) | no |
| Disk footprint | ~500 MB (`.venv` + `.git`) | ~30 MB (`.pyz` + wrappers) |
| Time-to-ready | ~2 min on a warm `uv` cache | ~30 s |
| Required on the machine | Python 3.14, `uv`, `git` | Python 3.14 only |

Pick development install when you intend to change source, run CI
locally, or ship a new release. Pick release install when you only need
the three CLIs from scripts or cron.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | `>=3.14` | declared at `pyproject.toml:6` |
| `uv` | `>=0.4` | resolves the locked venv; install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `git` | any recent | `git rev-parse --show-toplevel` is used by `scripts/build-release.sh` and by the bash wrappers |
| `just` | any recent | **optional** — a recipe runner is not required, but useful for the common task shortcuts |

`shiv`, `bats`, and `shellcheck` are NOT required on a developer
machine for the install itself — `shiv` is fetched into the venv at
build time (see [installation-release.md](installation-release.md));
`bats` and `shellcheck` are installed by the pre-commit gate on the
first commit, or by the CI workflow on `ubuntu-latest`.

---

## Install

Four commands. Step 2 is the bulk of the work; steps 3-4 wire the gate
and the smoke test.

```bash
# 1. Clone the repo and enter it
git clone https://github.com/EggProject/easter-skills-hack-to-hermes.git
cd easter-skills-hack-to-hermes

# 2. Bootstrap the venv with locked dependencies + dev extras
uv sync --locked --all-extras --dev

# 3. Install the unified pre-commit gate (ruff + black + mypy + wemake + flake8 + pytest + bats + shellcheck)
uv run --locked pre-commit install

# 4. Verify the three CLIs are on PATH
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-install-profiles --version
uv run --locked easter-hermes-sorry-skills-report --version
```

After step 2, `.venv/` exists. After step 3, every `git commit` runs
the pre-commit gate defined in `.pre-commit-config.yaml` (see
[docs/development.md](development.md)). After step 4 the CLIs are
callable from `.venv/bin/` without the `uv run --locked` prefix; the
prefix is still required to keep `uv.lock` authoritative per
`.claude/rules/worktree-pr-workflow.md`.

### Optional: add `.venv/bin` to `PATH`

If you want to invoke the CLIs without the `uv run --locked` prefix,
export `.venv/bin` ahead of `/usr/local/bin` in your shell profile.

```bash
# Current shell only
export PATH="$(pwd)/.venv/bin:${PATH}"

# Persist (pick one)
echo 'export PATH="'$(pwd)'/.venv/bin:${PATH}"' >> ~/.zshrc   # zsh
echo 'export PATH="'$(pwd)'/.venv/bin:${PATH}"' >> ~/.bashrc  # bash
```

---

## Verify

Three checks; every command must exit `0`.

```bash
# 1. Each CLI prints --version
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-install-profiles --version
uv run --locked easter-hermes-sorry-skills-report --version

# 2. The pre-commit gate is wired
uv run --locked pre-commit run --files pyproject.toml

# 3. The full test + lint sweep runs clean
uv run --locked pre-commit run --all-files
uv run --locked pytest
```

For the full bilingual smoke test (EN + HU help, `.pyz` zip listing,
plugin tree), see [docs/installation-verify.md](installation-verify.md).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `error: Python 3.13 or older is not supported` | `requires-python = ">=3.14"` (`pyproject.toml:6`) failed | Install Python 3.14 and re-export `PATH` so `python3` resolves to it; or pass `--python 3.14` to `uv sync` |
| `command not found: uv` | `uv` is not on `PATH` | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh`, then `source ~/.zshrc` (or `~/.bashrc`) |
| `error: The lockfile at uv.lock would be modified` | `uv sync` would change `uv.lock` against the committed copy | Re-run as `uv sync --locked --all-extras --dev` (the `--locked` flag refuses to mutate the lockfile); only `uv lock` is allowed to regenerate it |
| `.venv/bin/python3: No such file or directory` | A fresh checkout with no venv bootstrap | Run `uv sync --locked --all-extras --dev` once; subsequent commands expect `.venv/` to exist |
| `easter-hermes-sorry-skills-patch-hermes: command not found` | Ran the wrapper without `uv run --locked` | Either prefix with `uv run --locked`, or use `.venv/bin/easter-hermes-sorry-skills-patch-hermes` directly, or export `.venv/bin` to `PATH` (see above) |
| `pre-commit: command not found` (during step 3) | The venv was not bootstrapped with dev extras | Run `uv sync --locked --all-extras --dev` — the `--dev` flag installs `pre-commit` into `.venv` |
| `pre-commit install` fails with a hook error | One of the hook tools is missing on the host (e.g. `shellcheck`, `bats`) | Install via the platform package manager (e.g. `sudo apt-get install -y shellcheck bats` on Ubuntu 24.04) or let CI handle it on `ubuntu-latest` |

If none of the above matches, capture the full `uv run --locked`
command, its exit code, and the first 10 lines of stderr, and open an
issue.
