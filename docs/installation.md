# Installation

> [English](installation.md) · [Magyar verzió](installation.hu.md)
> [Back to README](../README.md)

`easter-hermes-sorry-skills` ships three CLIs and one migrated skill. The
three install modes below cover the three operational profiles: a developer
who edits source, an operator who only runs the CLIs, and a user who
wires the plugin into a Hermes runtime. Pick the mode that matches your
goal; each link below walks the full procedure.

After install, see [docs/usage.md](usage.md) for the operator commands and
[docs/development.md](development.md) for the lint / test / CI conventions.

Last verified: 2026-06-27 against `pyproject.toml` (HEAD `76b7cc3`).

---

## Prerequisites

The same three tools are required across all modes; the optional tools
vary by mode.

| Tool | Version | Required for | Notes |
|---|---|---|---|
| Python | `>=3.14` | all modes | declared at `pyproject.toml:6` (`requires-python = ">=3.14"`); the `.pyz` shebang points to the system `python3` |
| `uv` | `>=0.4` | dev install + release build | `uv.lock` is authoritative; `uv` resolves the venv and the pre-commit gate |
| `git` | any recent | dev install + release build | `git rev-parse --show-toplevel` is used by `scripts/build-release.sh` and by the bash wrappers |
| `shiv` | `>=1.0,<2.0` | release build only | installed into `.venv` by `scripts/build-release.sh`; required on the build machine, never on the operator machine |
| `bats` | any recent | smoke tests | `tests/bats/*.bats` exercise the shell wrappers end-to-end |
| `shellcheck` | any recent | pre-commit lint | `scripts/*.sh` are lint-gated at severity=warning |

The three entry points live at `pyproject.toml:33-36`:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-install-profiles`
- `easter-hermes-sorry-skills-report`

The `.pyz` is a single-file standalone zipapp (PEP 441) produced by
`shiv` from the venv's `site-packages/`; it embeds Python 3.14
site-packages but expects `python3` on PATH at run time.

---

## Quick install

Three modes, one CLI surface. Each mode links to the full procedure
plus a verification link for the smoke test.

### Mode 1 — Development install

For source edits, test runs, and rebuilds. Bootstraps the venv with
locked dependencies and the pre-commit gate.

- Prereq extras: `just` (optional) for the recipe runner.
- Time-to-ready: ~2 minutes on a warm cache.

→ [docs/installation-dev.md](installation-dev.md)

### Mode 2 — Release artifact install

For operator machines that only need to run the three CLIs. No
source, no `uv`, no rebuild — just the `.pyz` plus the bash wrappers
on `PATH`.

- Prereq extras: none beyond Python 3.14.
- Time-to-ready: ~30 seconds.

→ [docs/installation-release.md](installation-release.md)

### Mode 3 — Hermes plugin + skill install

For Hermes runtimes that should expose the migrated `skill-creator`
skill and load the patcher plugin at startup. Independent of modes 1
and 2.

- Prereq extras: a user-owned Hermes checkout (the patcher refuses the
  upstream repo, exit code 4).
- Time-to-ready: ~5 minutes including the patch audit.

→ [docs/installation-hermes.md](installation-hermes.md)

### Verify the install

After any mode, run the bilingual smoke test. Every command must exit
`0`; the EN + HU help sections must both print.

→ [docs/installation-verify.md](installation-verify.md)

---

## See also

- [Installation — dev mode](installation-dev.md) — clone, `uv sync`, pre-commit
- [Installation — release mode](installation-release.md) — `.pyz` + wrappers on `PATH`
- [Installation — Hermes mode](installation-hermes.md) — patch + plugin + skill
- [Installation — verify](installation-verify.md) — bilingual smoke test
- [Usage](usage.md) — driving the three CLIs end-to-end
- [Workflows](workflows.md) — common install / authoring / report recipes
- [Development](development.md) — test, lint, CI, worktree + PR conventions
- [Scripts](scripts.md) — flag-by-flag reference for the three CLIs
- [Skill-creator](skill-creator.md) — the migrated skill under `skills/skill-creator/`
- [Patches](patches.md) — what the patcher writes, and how to roll back
- [LICENSE](../LICENSE) — MIT
- [README](../README.md) — project landing page
