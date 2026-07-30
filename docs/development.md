# 🧪 Development

[Magyar verzio](development.hu.md) | [Docs](README.md)

## Local Environment

This is not the user install path. Use it only when editing this repository,
running the quality gates, or rebuilding `dist/`.

```bash
uv sync --locked --all-extras --dev
uv run --locked pre-commit install
```

Use `uv run --locked` for Python tools. Direct `pytest`, `ruff`, `black`, or
`mypy` calls can drift from the locked environment.

## Test Gate

```bash
uv run --locked pytest -q
```

`pyproject.toml` enables branch coverage and requires `--cov-fail-under=100`.
When new Python code is added, tests must cover it completely.

## Lint Gate

```bash
uv run --locked pre-commit run --all-files --show-diff-on-failure
```

The gate includes strict Python linting, formatting, mypy, shell checks, and
local meta checks.

## Hermes Compatibility

Never use a live Hermes checkout for development validation when a pinned target
is available. Validate against:

```bash
/tmp/hermes-a4973c3f
```

Use the patcher only with `--dry-run` during development handoff:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run
```

## Documentation Rules

- English is canonical.
- Hungarian translations use the same filename plus `.hu.md`.
- `docs/wow-skills-flowcharts.md` and `docs/wow-skills-flowcharts.hu.md`
  preserve the hook diagrams and examples.
- Keep examples executable and prefer exact commands over prose-only guidance.

## Branch Workflow

Work on a feature branch, push it, open or update the PR, and wait for green CI.
Every new change should be a new commit.
