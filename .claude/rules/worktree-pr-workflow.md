# worktree + PR workflow

- ALL agent work goes in a dedicated worktree + dedicated branch
- Changes reach main via PR
- FORBIDDEN: direct main commits

## Operator-Authorized Exception

A direct main commit is permitted ONLY when ALL of the following hold:

- The operator (user) gave EXPLICIT authorization for the specific commit before it was made
- The commit message body contains the literal marker `(operator-authorized exception)` on its own line
- The commit message body documents the reason and the operator's authorization
- The change is scoped to operator-local config (e.g. `.gitignore`, `.mcp.json`, `.claude/settings.json`) OR is a one-shot emergency fix the operator explicitly waved through

Post-hoc reconciliation:

- If a direct main commit landed WITHOUT the marker, the next fix agent MUST retroactively annotate it with `git commit --allow-empty -m "fix(issue-NN/F-X): retroactively annotate <sha> as operator-authorized exception per worktree-pr-workflow.md"`
- The annotation is an audit trail, NOT a re-authorization — it documents that the operator authorized the commit retroactively

Audit trail:

- Every operator-authorized exception commit MUST be linked back to this rule in its commit body
- The audit fix workflow (e.g. issue #33) catalogues every such commit and reconciles them in bulk

FORBIDDEN: agent self-authorizing an exception. The operator's explicit go-ahead is required.

## Worktree setup (mandatory after `git worktree add`)

- ALWAYS run `uv sync --locked` immediately after creating a new worktree — sets up the Python venv with locked dependencies
- ALL subsequent commands in the worktree MUST use `uv run --locked {COMMAND}` — e.g. `uv run --locked pytest`, `uv run --locked ruff check`, `uv run --locked wemake-python-styleguide`, `uv run --locked pre-commit run --all-files`, `uv run --locked mypy`, `uv run --locked black`
- NEVER call `pytest`, `ruff`, `wemake-python-styleguide`, `pre-commit`, `mypy`, `black` directly — ALWAYS prefix with `uv run --locked`
- The `--locked` flag ensures `uv.lock` is respected — no new dependencies without explicit `uv lock` update
