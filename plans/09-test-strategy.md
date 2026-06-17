<!-- title: Test strategy — TDD, fixtures, coverage, AST-grep, no-touch sentinels -->
<!-- scope: Sec 8. Drives 100% code+logic coverage and integration safety. -->
<!-- ACs covered: AC-2.x (test lists), AC-3.x (test lists), AC-4.x (test lists), AC-1.x (test lists) -->

# 09 — Test Strategy

## TDD methodology

- Every code file is written test-first. The TDD test list in 03/04/05/06/07/08 is the binding contract.
- Red → Green → Refactor: write a failing test, make it pass, refactor.
- 100% code coverage (line) AND 100% logic coverage (branch + error path) are mandatory. The CI gate fails on < 100%.
- `pytest --cov=hermes_skill_creator_plugin --cov-branch --cov-fail-under=100` is the canonical command.

## Test pyramid

```
                          E2E (sparse)
                         /             \
              Integration (per-file)     Contract (T3 inventory)
                   /         \               |
              Unit (per-function)        Snapshot (--help, MIGRATION.md)
```

- **Unit** — pure logic, no Hermes installation reads. Mock `agent.skill_utils`, `hermes_cli.*`, `tools.skill_manager_tool`. Run in < 1s per test.
- **Integration** — uses a fixture HERMES_HOME under `tmp_path`. Exercises the installer's file copy, Script #1's atomic write, Script #2's per-profile apply. The fixture NEVER touches the real `~/.hermes/`. Run in < 30s per test.
- **Contract** — T3 inventory: one test per binding replacement; reads the migrated file and asserts the forbidden string is absent and the Hermes string is present.
- **Snapshot** — `--help` output (bilingual format), `MIGRATION.md` (deterministic), frontmatter after install.
- **E2E** — one or two flows: (a) fresh `tmp_path` Hermes install → run install → run Script #1 (against a separate user-owned checkout fixture) → run Script #2 → start a fake Hermes session and assert `skills_list` returns `skill-creator`. Bounded to < 5 minutes.

## Fixture strategy (the `tmp_path` HERMES_HOME)

`tests/conftest.py`:

```python
import pytest
from pathlib import Path

@pytest.fixture
def hermes_home(monkeypatch, tmp_path):
    """Redirect HERMES_HOME to a tmp dir; never touch the real ~/.hermes."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "skills").mkdir()
    (home / "plugins").mkdir()
    (home / "profiles").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    yield home

@pytest.fixture
def hermes_checkout(monkeypatch, tmp_path):
    """A USER-OWNED fake Hermes checkout (the --target for Script #1).

    NOT ~/.hermes/hermes-agent. Lays down the minimum tree so Script #1's
    pre-validation can resolve all anchors.
    """
    checkout = tmp_path / "hermes-checkout"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    (checkout / "hermes_cli").mkdir(parents=True)
    # Copy the minimum real files from the read-only Hermes install so the
    # anchors are real. The test NEVER writes to ~/.hermes/hermes-agent.
    from tests.fixtures.minimal_hermes import seed_minimal
    seed_minimal(checkout)
    yield checkout

@pytest.fixture
def frozen_time(monkeypatch):
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    yield "2026-06-17T00:00:00Z"

@pytest.fixture
def real_hermes_agent_sentinel(monkeypatch):
    """Hash ~/.hermes/hermes-agent/agent/skill_utils.py before and after a run.

    The test FAILS if the hash changes. This is the no-touch sentinel.
    """
    import hashlib
    target = Path.home() / ".hermes" / "hermes-agent" / "agent" / "skill_utils.py"
    if not target.exists():
        pytest.skip("~/.hermes/hermes-agent not present on this host")
    pre = hashlib.sha256(target.read_bytes()).hexdigest()
    yield pre
    post = hashlib.sha256(target.read_bytes()).hexdigest()
    assert pre == post, f"HERMES-AGENT TOUCHED: {target} sha changed {pre} -> {post}"
```

## Bilingual AST-grep rule

A pre-commit hook (`tools/check_bilingual.py`) walks every `print(...)` and `logger.{info,warning,error}(...)` call in `src/hermes_skill_creator_plugin/`, `scripts/`, and the migrated `scripts/`, and asserts the format string matches `^\[en\] .+ / \[hu\] .+$`.

```python
# tools/check_bilingual.py (sketch)
import ast, pathlib, re, sys
BILINGUAL = re.compile(r"\[en\][^/]+/ \[hu\]")
def walk(path):
    for p in pathlib.Path(path).rglob("*.py"):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Call,)) and getattr(node.func, "id", "") in {"print", "info", "warning", "error"}:
                # extract first arg as a JoinedStr / Constant
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if not BILINGUAL.search(arg.value):
                        print(f"NOT BILINGUAL: {p}:{node.lineno}", file=sys.stderr)
                        sys.exit(1)
                elif isinstance(arg, ast.JoinedStr):
                    # The whole f-string should be a constant joined by {en} and {hu} markers
                    ...
```

`--help` is checked separately: asserts both "Usage (English)" and "Hasznalat (magyar)" sections are present and the option table is mirrored.

## No-touch sentinel for ~/.hermes/hermes-agent

A test decorator `@assert_hermes_agent_untouched` wraps every Script #1 unit test. It snapshots the sha256 of `~/.hermes/hermes-agent/agent/skill_utils.py` at test start and asserts it is unchanged at test end. The decorator NEVER writes to that file; it only reads. If the file is missing (e.g., CI on a non-Hermes host), the test is `pytest.skip`'d, not silently passing.

## Snapshot fixtures for --help and MIGRATION.md

`tests/snapshots/help_script_1.txt`, `tests/snapshots/help_script_2.txt`, `tests/snapshots/help_plugin_install.txt` — frozen golden output of `--help`. Updated by `pytest --snapshot-update` only on explicit operator action; CI fails on diff.

`tests/snapshots/migration_hermes_patch_default.md`, `tests/snapshots/migration_hermes_patch_task_e.md`, `tests/snapshots/migration_hermes_patch_task_e_no_schema.md` — three snapshots, one per flag combination. The frozen-time fixture ensures byte-identical output.

## Coverage matrix (per file)

| Source file | Lines (target) | Test file | Coverage target |
| --- | --- | --- | --- |
| `src/hermes_skill_creator_plugin/__init__.py` | 20 | `tests/unit/test_init.py` | 100% |
| `src/hermes_skill_creator_plugin/hooks.py` | 80 | `tests/unit/test_hooks.py`, `tests/integration/test_hooks_advisory.py` | 100% |
| `src/hermes_skill_creator_plugin/skill_register.py` | 60 | `tests/unit/test_skill_register.py` | 100% |
| `src/hermes_skill_creator_plugin/installer.py` | 200 | `tests/unit/test_installer.py`, `tests/integration/test_installer_apply.py` | 100% |
| `src/hermes_skill_creator_plugin/_scope.py` | 40 | `tests/unit/test_scope.py` | 100% |
| `src/hermes_skill_creator_plugin/_subprocess.py` | 30 | `tests/unit/test_subprocess.py` | 100% |
| `src/hermes_skill_creator_plugin/_advisory.py` | 60 | `tests/unit/test_advisory.py` | 100% |
| `scripts/script_1_patch.py` | 400 | `tests/unit/test_script_1_*.py`, `tests/integration/test_script_1_apply.py` | 100% |
| `scripts/script_2_profiles.py` | 400 | `tests/unit/test_script_2_*.py`, `tests/integration/test_script_2_apply.py` | 100% |
| `scripts/utils.py` (migrated) | 100 | `tests/unit/test_utils.py` | 100% |
| `scripts/run_eval.py` (migrated) | 200 | `tests/unit/test_run_eval.py`, `tests/integration/test_run_eval_end_to_end.py` | 100% |
| `scripts/improve_description.py` (migrated) | 100 | `tests/unit/test_improve_description.py` | 100% |
| `eval-viewer/generate_review.py` (migrated) | 100 | `tests/unit/test_generate_review.py` | 100% |

## Mocking discipline

- `agent.skill_utils` — patched via `monkeypatch.setattr`. NEVER imported into a test that asserts on the live install.
- `hermes_cli.config` — patched via `monkeypatch.setattr`. The integration test for `hermes_home_scope` exercises both the override token AND the env var.
- `hermes_cli.skills_hub.do_install` — replaced with a spy that records calls. The spy asserts `force=True, skip_confirm=True, name_override=""` and that `os.environ['HERMES_HOME']` matches the scope.
- `clear_skills_system_prompt_cache` — replaced with a spy that records calls and can be made to raise.
- `subprocess.run` (in migrated `scripts/run_eval.py`) — replaced with a fake that records the call and returns a fixture NDJSON stream.

## TDD test list (per-code-file, the comprehensive list)

(See 03 / 04 / 05 / 06 / 07 / 08 for the per-feature test lists. The list here is the *test strategy* test list — meta-tests that guard the test infrastructure itself.)

- `test_conftest_hermes_home_does_not_touch_real` — assert `hermes_home` fixture writes zero bytes to the real `~/.hermes/`.
- `test_conftest_hermes_checkout_does_not_touch_real` — assert `hermes_checkout` fixture writes zero bytes to the real `~/.hermes/hermes-agent/`.
- `test_real_hermes_agent_sentinel_decorator_skips_when_absent` — when `~/.hermes/hermes-agent/agent/skill_utils.py` is missing, the decorator `pytest.skip`s, not silently passes.
- `test_bilingual_hook_catches_missing_hu` — `print("[en] only english")` triggers the pre-commit hook to fail.
- `test_bilingual_hook_catches_missing_en` — `print("[hu] csak magyar")` triggers failure.
- `test_bilingual_hook_passes_clean_line` — `print("[en] hello / [hu] szia")` passes.
- `test_snapshot_help_script_1` — `--help` matches the frozen golden file.
- `test_snapshot_migration_default` — `MIGRATION.hermes-patch.md` (default mode) matches the frozen golden file.
- `test_snapshot_migration_task_e` — same for `--task-e-redirect`.
- `test_coverage_100_percent_enforced` — `pytest --cov-fail-under=100` exits non-zero if a single line or branch is missed.
- `test_ruff_clean` — `ruff check .` exits 0.
- `test_black_clean` — `black --check .` exits 0.
- `test_mypy_strict_clean` — `mypy --strict src/` exits 0.
- `test_wemake_clean` — `flake8 src/` (wemake-python-styleguide) exits 0.
- `test_pre_commit_hooks_installed_and_passing` — `pre-commit run --all-files` exits 0.

### Seed-minimal-fixture meta-tests
- `test_seed_minimal_matches_patch_anchors` — runs `seed_minimal(tmp_checkout)`; reads `agent/skill_utils.py` and `tools/skills_tool.py`; asserts the 4 anchor lines match the contract table (line 647 function def, line 653 cap-raise site, line 654 replacement target, line 95 `MAX_DESCRIPTION_LENGTH = 1024`). This is the meta-test that the fixture stays in sync with Script #1's patch anchors.
- `test_seed_minimal_patched_variant_replaces_literal_60` — runs `seed_minimal_patched(tmp_checkout)`; asserts line 653 of `agent/skill_utils.py` contains `MAX_DESCRIPTION_LENGTH` and NOT the literal `60`.
- `test_hermes_checkout_fixture_uses_seed_minimal` — asserts the `hermes_checkout` fixture (in conftest.py) calls `seed_minimal` exactly once and the resulting tree matches the contract.
- `test_seed_minimal_writes_only_six_files` — asserts `seed_minimal` writes exactly 6 files (4 anchor + 2 empty `__init__.py`); any drift is a fixture bug, not a code bug.

## Branch coverage matrix (the bits the 100% target is hardest on)

- Script #1: every `argparse` choice; every exit code (0/1/2/3/4/5); the with/without `--task-e-redirect` × with/without `--no-schema-redirect` × with/without `--force` × with/without `--i-accept-line-drift` matrix.
- Script #2: empty-profile / single-profile / N-profile / missing-`~/.hermes` matrix; `set_hermes_home_override` raise × `os.environ` set × `do_install` raise × `clear_skills_system_prompt_cache` raise matrix.
- Installer: TTY confirmed × `--yes` × real-`~/.hermes` × tmp-`HERMES_HOME` × collision × partial-copy × read-only target matrix.
- Migrated `run_eval.py`: `HERMES_SESSION` set × unset × helper called × subprocess env stripped matrix.

## TDD ordering (the work order for Phase 5)

1. Write `tests/unit/test_scope.py` (the simplest) first. Make it pass.
2. Write `tests/unit/test_subprocess.py`. Make it pass.
3. Write `tests/unit/test_advisory.py`. Make it pass.
4. Write `tests/unit/test_skill_register.py`. Make it pass.
5. Write `tests/unit/test_installer.py` (mocked paths). Make it pass.
6. Write `tests/integration/test_installer_apply.py` (real fixture HERMES_HOME). Make it pass.
7. Write `tests/unit/test_script_1_*.py` (one per branch). Make them pass.
8. Write `tests/integration/test_script_1_apply.py`. Make it pass.
9. Write `tests/unit/test_script_2_*.py`. Make them pass.
10. Write `tests/integration/test_script_2_apply.py`. Make it pass.
11. Write `tests/unit/test_run_eval.py`, `test_improve_description.py`, `test_generate_review.py`. Make them pass.
12. Write `tests/integration/test_eval_pipeline_end_to_end.py`. Make it pass.
13. Write `tests/integration/test_eval_viewer_static_open.py`. Make it pass.
14. Run the meta-tests (`test_bilingual_hook_*`, `test_snapshot_*`, `test_coverage_*`, lint suite). Fix any gaps.

## Seed-minimal-fixture contract (`tests/fixtures/minimal_hermes/seed_minimal.py`)

The `hermes_checkout` fixture calls `seed_minimal(checkout)` to lay down the
minimum tree so Script #1's pre-validation can resolve all patch anchors.
The fixture is the contract; the patch anchors are read from it.

**Files written by `seed_minimal(checkout: Path) -> None`**:

| path (relative to checkout) | line | required text | purpose |
| --- | --- | --- | --- |
| `agent/skill_utils.py` | 647 | `def extract_skill_description(frontmatter: Dict[str, Any]) -> str:` | function definition anchor (S1.cap) |
| `agent/skill_utils.py` | 653 | `    if len(desc) > 60:` | cap-raise site (S1.cap, UNPATCHED state) |
| `agent/skill_utils.py` | 654 | `        return desc[:57] + "..."` | the cap-raise replacement target |
| `tools/skills_tool.py` | 95 | `MAX_DESCRIPTION_LENGTH = 1024` | the patched comparator constant (imported by S1.cap's replacement) |
| `agent/__init__.py` | n/a | (empty) | makes `agent` a package so `from agent.skill_utils import extract_skill_description` resolves in tests |
| `tools/__init__.py` | n/a | (empty) | makes `tools` a package so `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` resolves in tests |

The fixture also exposes a `seed_minimal_patched(checkout)` variant that
replaces the literal `60` with `MAX_DESCRIPTION_LENGTH` on line 653 of
`agent/skill_utils.py`, so the integration tests cover BOTH the unpatched
cap-state (default) and the patched cap-state (`--with-short-description`
false-positive guard).

**No other files are written.** `hermes_cli/` is NOT seeded (Script #1's
cap-raise does not touch it). `home/`, `profiles/`, `sessions/` are NOT
seeded (Script #2's profile audit uses a different fixture).

## Meta-test guarding the fixture contract

`test_seed_minimal_matches_patch_anchors` (added to the TDD test list
above) runs `seed_minimal(tmp_checkout)`, reads the 4 anchor files, and
asserts the contract lines match. A second variant
`test_seed_minimal_patched_variant_replaces_literal_60` covers the
patched state. The meta-test is the single source of truth that the
fixture stays in sync with the patch anchors — if a future Hermes
release moves the cap-raise site, the meta-test fails first, naming
the drifted line, and the fixture is updated to match.

<!-- end of file: 193+ lines (budget 300) -->
