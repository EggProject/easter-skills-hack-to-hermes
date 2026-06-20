# worktree + PR workflow

- ALL agent work goes in a dedicated worktree + dedicated branch
- Changes reach main via PR
- FORBIDDEN: direct main commits

## Worktree setup (mandatory after `git worktree add`)

- ALWAYS run `uv sync --locked` immediately after creating a new worktree — sets up the Python venv with locked dependencies
- ALL subsequent commands in the worktree MUST use `uv run --locked {COMMAND}` — e.g. `uv run --locked pytest`, `uv run --locked ruff check`, `uv run --locked wemake-python-styleguide`, `uv run --locked pre-commit run --all-files`, `uv run --locked mypy`, `uv run --locked black`
- NEVER call `pytest`, `ruff`, `wemake-python-styleguide`, `pre-commit`, `mypy`, `black` directly — ALWAYS prefix with `uv run --locked`
- The `--locked` flag ensures `uv.lock` is respected — no new dependencies without explicit `uv lock` update
