# Development

> [Magyar verzió](development.hu.md)
> [Back to README](../README.md)

This page describes the local test, lint, and CI setup for `easter-hermes-sorry-skills`. Read it before opening a PR — every gate listed here is enforced by the CI workflow on GitHub.

---

## Layout

The test suite is split into four layers. Each layer has a single responsibility and a separate runner command.

- `tests/unit/` — 11 Python unit tests (`pytest`). Covers `cli_patch`, the profiles CLI, the patcher, the safety decorator, scope, the conftest sentinel, and the subprocess placeholder.
- `tests/report/` — 9 reporter tests + `_fixtures.py`. Covers `cli_report`, the reporter format, token counting, verbose mode, and the readonly + branch surfaces.
- `tests/meta/` — 3 meta-tests for the `tools/` helpers. Covers `check_bilingual.py`, `check_line_count.py`, and the meta conftest.
- `tests/bats/` — bash smoke tests (`patch-hermes.bats`, `report.bats`). Exercise the shell wrappers end-to-end.

Top-level tests (`test_register.py`, `test_advisory.py`, `test_i18n_bilingual.py`) live alongside the `tests/conftest.py` merged fixture file. The conftest exposes `hermes_home`, `hermes_checkout`, `skill_creator_home`, and `real_hermes_agent_sentinel`, and pre-registers stub modules for `hermes_cli.profiles` and `hermes_cli.skills_config` at import time so `tests/unit/*.py` can import the production code under test without the real Hermes runtime on the path.

Stubs live under `tests/stubs/` (type-only `.pyi` files for `agent`, `hermes_cli`, `rich`, `tools`, plus `hermes_constants.pyi` and `yaml.pyi`). The minimal-Hermes fixture lives at `tests/fixtures/minimal_hermes/seed_minimal.py` and exports `MINIMAL_HERMES_FILES` + `seed_minimal()`.

---

## Running tests

The unified gate runs every hook and the test layers in one go:

```bash
uv run --locked pre-commit run --all-files
```

To run layers individually:

```bash
uv run --locked pytest                  # Python tests (unit + report + meta + top-level)
bats tests/bats/                        # shell smoke tests
uv run --locked ruff check              # ruff lint
uv run --locked black --check           # black format check
uv run --locked mypy                    # static type check (calls mypy_wrapper.sh)
uv sync --all-extras --dev              # one-time: install every dependency
```

All Python commands MUST be prefixed with `uv run --locked` (per `.claude/rules/worktree-pr-workflow.md`); this keeps `uv.lock` authoritative. Never call `pytest`, `ruff`, `mypy`, `black`, `wemake-python-styleguide`, or `pre-commit` directly.

Coverage is gated at 100% branch coverage via `pyproject.toml` (`--cov-fail-under=100`). The Python gate covers the package, `tools/`, and shared test fixtures; bats smoke tests cover the shell wrappers separately.

---

## Lint and type-check

`.pre-commit-config.yaml` is the single source of truth for the gate. Hooks run in this order (strictest first):

1. `check-line-count` (local) — enforces a 500-line per-file cap plus three other invariants on the planning markdown directory (the glob is configurable at `tools/check_line_count.py:37`). Excludes `docs/research/` (vendored upstream skill-creator reference).
2. `bats` (local) — runs `tests/bats/`.
3. `wemake-python-styleguide` 1.6.2 — strictest Python linter. Scope: `src/`.
4. `flake8` 7.1.1 — secondary strictest Python lint. Scope: `src/`.
5. `ruff` 0.11.9 + `ruff-format` — fast lint + format. Scope: `src/`, `tests/`, `tools/`.
6. `black` 25.11.0 — secondary formatter (line length 120). Scope: `src/`, `tests/`, `tools/`.
7. `mypy` v1.11.2 `--strict` — static type check. Scope: `src/`.
8. `shellcheck` (local binary) — `scripts/*.sh` lint. Severity = warning.

The pre-commit config deliberately excludes `check_bilingual.py` because the migrated skill stays English-only (operator-authorized deviation).

---

## CI workflow

`.github/workflows/ci.yml` runs on `push` to `main` and on every pull request. It uses separate jobs so independent checks can run in parallel:

1. `lint` — `uv sync --locked --all-extras --dev`, system `bats` + `shellcheck`, then `uv run --locked pre-commit run --all-files --show-diff-on-failure`.
2. `test-python` — `uv run --locked pytest -q`, using the 100% branch coverage gate from `pyproject.toml`.
3. `test-bats` — builds a Linux-compatible `.pyz`, then runs `bats tests/bats/`.
4. `static-safety` — asserts that no `# noqa`, `# type: ignore`, or `# pragma: no cover` lines exist in `src/`.
5. `build-package` — runs `scripts/build-release.sh --only-shiv` as a release-artifact smoke build.

Pull requests that show CI red MUST NOT be merged with `--admin`. Wait for CI to pass or request an explicit operator override.

---

## Custom tools

### `tools/check_bilingual.py`

AST-walks `src/`, `scripts/`, and `skills/`. For every `print(...)` and `logger.{info,warning,error,...}(...)` call whose first argument is a static string, asserts the format string matches `^\[en\] .+?/ \[hu\] .+?$` — i.e. the `[en] ... / [hu] ...` single-line bilingual surface (`tools/check_bilingual.py:44`). Non-static strings (variables, f-strings with non-literal placeholders) are skipped; the caller must produce bilingual output at runtime.

The tool also walks Click command docstrings and asserts both `Usage (English)` and `Használat (magyar)` sections are present (`tools/check_bilingual.py:45-46`). Help docstrings missing either section are reported as findings.

Currently disabled in pre-commit per operator decision (see `.pre-commit-config.yaml:25-30`).

### `tools/check_line_count.py`

Enforces four invariants on the planning markdown directory. The directory glob and the four invariants are configured in the module docstring at `tools/check_line_count.py:1-23`; the per-file line cap is `PER_FILE_CAP = 500` (`tools/check_line_count.py:36`):

1. **Per-file cap** — every plan file MUST be `<= 500` lines (`PER_FILE_CAP = 500`, `tools/check_line_count.py:36`).
2. **Footer drift** — every non-index plan file MUST end with `<!-- end of file: NN lines (budget BB) -->` where `NN == wc -l`. `00-index.md` MUST use the bare `<!-- end of file -->` marker.
3. **Budget-table Total** — the `**Total**` cell in `00-index.md` AND any `Sum NNNN < Total` prose MUST equal the live `wc -l` sum across every plan file (00-index included).
4. **Per-cell guard** — for every row of the file-map table, `Actual` MUST equal `wc -l` of the cited path and `Budget` MUST be `>= Actual`.

CLI flags: `--no-footer`, `--no-budget-table`, `--no-per-cell` disable individual invariants; `--enforce-X` re-enables them (default on).

### `tools/mypy_wrapper.sh`

Runs mypy on `src/easter_hermes_sorry_skills/__init__.py` and `src/easter_hermes_sorry_skills/_advisory.py` with `MYPYPATH=src` and `--strict --explicit-package-bases` (`tools/mypy_wrapper.sh:1-22`). Exists because pre-commit-mypy ignores the `MYPYPATH` env var and cannot run with `pass_filenames: false` plus a package name on the CLI without it. Prefers `.venv/bin/mypy` and falls back to PATH.

---

## Contribution workflow

> Note: All `.claude/rules/*.md` paths below refer to project-internal rule files committed to this repository. They govern the worktree+PR workflow and are not external dependencies.

Every change goes in a dedicated worktree on a dedicated branch; nothing lands on `main` directly.

1. Create a worktree: `git worktree add .claude/worktrees/<branch> -b <branch>`.
2. Immediately run `uv sync --locked` to populate `.venv` with locked dependencies.
3. Make the change. ALL subsequent commands MUST use `uv run --locked <command>`.
4. Run the unified gate locally: `uv run --locked pre-commit run --all-files`.
5. Commit. Open a PR.
6. **Follow up the PR until it merges.** A PR that is opened and forgotten (or closed without merge) is a violation of `.claude/rules/follow-up-pr-until-merged.md`. If CI blocks the PR, fix the blocker — do not close it. If a CI failure is unrelated to your change, rebase and re-run.
7. After every PR merge, run `git pull origin main` to refresh the local `origin/main` reference.

When `.claude/` itself changes (CLAUDE.md, rules, agents, skills), REBASE every active worktree onto main AND start a NEW agent so the new instructions load cleanly.

When opening a PR, reference the EN doc your change documents; the HU mirror follows the same lifecycle as a sister file.
