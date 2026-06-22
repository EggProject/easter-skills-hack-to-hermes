Hermes skill-creator plugin and migration scripts (Phase 5 of Hermes Skills Hack).

See `docs/plans/` for the full plan.

## Dev setup

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management
and [pre-commit](https://pre-commit.com/) for the unified lint/type/test gate
(strictest hooks per `docs/plans/10-toolchain-and-conventions.md` D1).

After cloning the repository:

```sh
# 1. Install ALL extras + dev group (wemake-python-styleguide, pre-commit,
#    ruff, black, mypy). `--all-extras` includes the `dev` optional group.
uv sync --locked --all-extras --dev

# 2. Install the pre-commit hook so the unified gate runs on every commit.
uv run --locked pre-commit install
```

The `--locked` flag enforces `uv.lock` integrity: no dependency changes without
an explicit `uv lock` update. The first command resolves the full venv (37
packages) including all lint/type/test tooling; without `--all-extras --dev`
only the runtime dependencies (click, ruamel.yaml, pyyaml, python-frontmatter,
pytest, pytest-cov) are installed and pre-commit / wemake / mypy are missing.

CI runs the same `uv sync --all-extras --dev` step (see
`.github/workflows/ci.yml`), so a passing local pre-commit run guarantees a
passing CI run for the same code.

To run the full unified gate locally:

```sh
uv run --locked pre-commit run --all-files
```
