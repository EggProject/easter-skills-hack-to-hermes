<!-- title: Test strategy — TDD, fixtures, coverage, AST-grep, no-touch sentinels -->
<!-- scope: Sec 8. Drives 100% code+logic coverage and integration safety. -->
<!-- ACs covered: AC-2.x (test lists), AC-3.x (test lists), AC-4.x (test lists), AC-1.x (test lists) -->

# 09 — Test Strategy

## TDD methodology

- Every code file is written test-first. The TDD test list in 03/04/05/06/07/08 is the binding contract.
- Red → Green → Refactor: write a failing test, make it pass, refactor.
- 100% code coverage (line) AND 100% logic coverage (branch + error path) are mandatory. The CI gate fails on < 100%.
- `pytest --cov=hermes_skill_creator_plugin --cov-branch --cov-fail-under=100` is the canonical command.
- Each script is tested as an isolated unit, then as a subprocess invocation. The CLI argument matrix is parametrized.

## Test pyramid

```
                          E2E (sparse)
                         /             \
              Integration (per-file)     Contract (T3 inventory)
                   /         \               |
              Unit (per-function)        Snapshot (--help, MIGRATION.md)
```

- **Unit** — pure logic, no Hermes installation reads. Mock `agent.skill_utils`, `hermes_cli.*`, `tools.skill_manager_tool`. Run in < 1s per test.
- **Integration** — uses a fixture HERMES_HOME under `tmp_path`. Exercises the installer's file copy, Script #1's atomic write, Script #2's per-profile apply, Script #3's read-only probe. The fixture NEVER touches the real `~/.hermes/`. Run in < 30s per test.
- **Contract** — T3 inventory: one test per binding replacement; reads the migrated file and asserts the forbidden string is absent and the Hermes string is present.
- **Snapshot** — `--help` output (bilingual format), `MIGRATION.md` (deterministic), frontmatter after install.
- **E2E** — one or two flows: (a) fresh `tmp_path` Hermes install → run install → run Script #1 (against a separate user-owned checkout fixture) → run Script #2 → run Script #3 (read-only) → start a fake Hermes session and assert `skills_list` returns `skill-creator`. Bounded to < 5 minutes.

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

@pytest.fixture
def hermes_home_writable(monkeypatch, tmp_path):
    """A writable HERMES_HOME that mirrors real-disk layout for Script #3 tests.

    Seeds skills/, profiles/, config.yaml so the reporter can walk the tree.
    Asserts NO bytes are written outside this tree by Script #3 (the
    reporter is strictly READ-ONLY).
    """
    home = tmp_path / "hermes-home-report"
    (home / "skills").mkdir(parents=True)
    (home / "profiles").mkdir(parents=True)
    (home / "config.yaml").write_text("profiles: {default: {enabled: []}}\n")
    monkeypatch.setenv("HERMES_HOME", str(home))
    yield home
```

## Bilingual AST-grep rule

A pre-commit hook (`tools/check_bilingual.py`) walks every `print(...)` and `logger.{info,warning,error}(...)` call in `src/hermes_skill_creator_plugin/`, `scripts/`, the migrated `scripts/`, and the new `scripts/script_3_report.py`. It asserts the format string matches `^\[en\] .+ / \[hu\] .+$`.

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

`--help` is checked separately: asserts both "Usage (English)" and "Hasznalat (magyar)" sections are present and the option table is mirrored. Script #3's `--help` is covered by `test_report_help_is_bilingual`.

## No-touch sentinel for ~/.hermes/hermes-agent

A test decorator `@assert_hermes_agent_untouched` wraps every Script #1 unit test. It snapshots the sha256 of `~/.hermes/hermes-agent/agent/skill_utils.py` at test start and asserts it is unchanged at test end. The decorator NEVER writes to that file; it only reads. If the file is missing (e.g., CI on a non-Hermes host), the test is `pytest.skip`'d, not silently passing.

## Read-only sentinel for Script #3

Script #3 is REPORT-ONLY. A separate fixture (`hermes_home_writable` above) wraps every Script #3 test. Before and after the run, it walks the fixture tree and asserts zero bytes have changed. The reporter MUST NOT create, modify, or delete any file under HERMES_HOME. Tests fail loudly if any bytes are written.

## Snapshot fixtures for --help and MIGRATION.md

`tests/snapshots/help_script_1.txt`, `tests/snapshots/help_script_2.txt`, `tests/snapshots/help_script_3.txt`, `tests/snapshots/help_plugin_install.txt` — frozen golden output of `--help`. Updated by `pytest --snapshot-update` only on explicit operator action; CI fails on diff.

`tests/snapshots/migration_hermes_patch_default.md`, `tests/snapshots/migration_hermes_patch_task_e.md`, `tests/snapshots/migration_hermes_patch_task_e_no_schema.md` — three snapshots, one per flag combination. The frozen-time fixture ensures byte-identical output.

## Coverage matrix (per file)

| Source file | Lines (target) | Test file | Coverage target |
| --- | --- | --- | --- |
| `src/hermes_skill_creator_plugin/__init__.py` | 20 | `tests/unit/test_init.py` | 100% |
| `src/hermes_skill_creator_plugin/hooks.py` | 80 | `tests/unit/test_hooks.py`, `tests/integration/test_hooks_advisory.py` | 100% |
| `src/hermes_skill_creator_plugin/installer.py` | 200 | `tests/unit/test_installer.py`, `tests/integration/test_installer_apply.py` | 100% |
| `src/hermes_skill_creator_plugin/_scope.py` | 40 | `tests/unit/test_scope.py` | 100% |
| `src/hermes_skill_creator_plugin/_subprocess.py` | 30 | `tests/unit/test_subprocess.py` | 100% |
| `src/hermes_skill_creator_plugin/_advisory.py` | 60 | `tests/unit/test_advisory.py` | 100% |
| `scripts/script_1_patch.py` | 400 | `tests/unit/test_script_1_*.py`, `tests/integration/test_script_1_apply.py` | 100% |
| `scripts/script_2_profiles.py` | 400 | `tests/unit/test_script_2_*.py`, `tests/integration/test_script_2_apply.py` | 100% |
| `scripts/script_3_report.py` | 250 | `tests/unit/test_script_3_*.py`, `tests/integration/test_script_3_read_only.py` | 100% |
| `scripts/utils.py` (migrated) | 100 | `tests/unit/test_utils.py` | 100% |
| `scripts/run_eval.py` (migrated) | 200 | `tests/unit/test_run_eval.py`, `tests/integration/test_run_eval_end_to_end.py` | 100% |
| `scripts/improve_description.py` (migrated) | 100 | `tests/unit/test_improve_description.py` | 100% |
| `eval-viewer/generate_review.py` (migrated) | 100 | `tests/unit/test_generate_review.py` | 100% |
| `skills/skill-creator/SKILL.md` (migrated, top-level standalone) | n/a | `tests/unit/test_skill_creator_frontmatter.py`, `tests/integration/test_skill_creator_install_path.py` | 100% of frontmatter validation logic |

## Mocking discipline

- `agent.skill_utils` — patched via `monkeypatch.setattr`. NEVER imported into a test that asserts on the live install.
- `hermes_cli.config` — patched via `monkeypatch.setattr`. The integration test for `hermes_home_scope` exercises both the override token AND the env var.
- `hermes_cli.skills_hub.do_install` — replaced with a spy that records calls. The spy asserts `force=True, skip_confirm=True, name_override=""` and that `os.environ['HERMES_HOME']` matches the scope.
- `clear_skills_system_prompt_cache` — replaced with a spy that records calls and can be made to raise. The spy targets `agent.prompt_builder.clear_skills_system_prompt_cache` (the real location, sig `(*, clear_snapshot: bool=False)`) with `clear_snapshot=True`; no fallback to a literal `~/.hermes/...` path.
- `subprocess.run` (in migrated `scripts/run_eval.py`) — replaced with a fake that records the call and returns a fixture NDJSON stream.
- Script #3's tokenizer — replaced with a fake that returns deterministic token counts; tests assert the reporter calls the tokenizer with the rendered name+description string.
- Script #3's Curator access — replaced with a fake that returns fixture `(use_count, last_used)` tuples or `None` to exercise the n/a path.

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
- `test_seed_minimal_matches_patch_anchors` — runs `seed_minimal(tmp_checkout)`; reads `agent/skill_utils.py` and `tools/skills_tool.py`; asserts the 4 anchor lines match the contract table (function def for `extract_skill_description`, cap-raise site `if len(desc) > 60:`, replacement target `return desc[:57] + "..."`, `MAX_DESCRIPTION_LENGTH = 1024` at line 95). This is the meta-test that the fixture stays in sync with Script #1's patch anchors.
- `test_seed_minimal_patched_variant_replaces_literal_60` — runs `seed_minimal_patched(tmp_checkout)`; asserts the cap-raise site of `agent/skill_utils.py` contains `MAX_DESCRIPTION_LENGTH` and NOT the literal `60`; AND the slice is `desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` (the cap-raise patch is complete — comparator AND slice are both updated).
- `test_hermes_checkout_fixture_uses_seed_minimal` — asserts the `hermes_checkout` fixture (in conftest.py) calls `seed_minimal` exactly once and the resulting tree matches the contract.
- `test_seed_minimal_writes_only_six_files` — asserts `seed_minimal` writes exactly 6 files (4 anchor + 2 empty `__init__.py`); any drift is a fixture bug, not a code bug.
- `test_seed_minimal_patched_variant_completes_cap_raise` — asserts the patched variant's slice is `desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."`, matching the codebase idiom in `tools/skills_tool.py` (lines 659, 814). This guards against the partial-patch bug where only the comparator is replaced.

## Script #3 tests (TDD test list)

All Script #3 tests use the `hermes_home_writable` fixture and assert zero bytes are written.

- `test_report_read_only_zero_writes` — run the reporter against `hermes_home_writable`; walk the fixture tree before/after; assert identical file list, sizes, and mtimes; assert no new files anywhere under `~/.hermes/`. Also asserts no files inside any profile's enabled set are touched.
- `test_report_default_profile` — `--profile` (no name) lists the default profile's enabled skills; assert all enabled skills present, all disabled skills absent.
- `test_report_named_profile` — `--profile <name>` lists the named profile's enabled skills; assert the reporter resolves the profile from `~/.hermes/profiles/<name>.yaml` (or the equivalent config key) and applies the profile-specific toggle.
- `test_report_sort_by_tokens` — `--sort tokens`; assert the table rows are sorted descending by token count; assert the total-token row at the bottom reflects the sorted ordering.
- `test_report_sort_by_use_count` — `--sort use_count`; assert the rows are sorted descending by `use_count`; assert skills with `n/a` use_count sort to the end.
- `test_report_sort_by_last_used` — `--sort last_used`; assert the rows are sorted descending by `last_used` timestamp; assert skills with `n/a` last_used sort to the end.
- `test_report_tokens_match_fixture` — inject a fixture skill with a known name + description; assert the reported token count equals the tokenizer's output for the rendered `name + description` string; when the tokenizer is unavailable, assert the fallback is `len(rendered) // 4`.
- `test_report_tokens_projected_against_1024_cap` — when the column projection is enabled, assert each row shows a `(tokens / 1024)` percentage and the total row shows an aggregate.
- `test_report_usage_n_a_when_curator_absent` — when the Curator store is missing or the skill has no usage record, the `use_count` and `last_used` columns show `n/a` (and the row still renders); assert no exception is raised.
- `test_report_usage_present_when_curator_available` — when the Curator returns `(view_count, use_count, patch_count, last_used)`, the row shows them in the correct columns.
- `test_report_shares_enabled_detection_with_script_2` — import `scripts.script_3_report`; assert it imports `get_enabled_skills` from `hermes_skill_creator_plugin._enabled_detection`; assert it is the SAME helper that `scripts.script_2_profiles` uses (single canonical import path, function name `get_enabled_skills(profile_path: Path, *, platform: Optional[str] = None) -> frozenset[str]`).
- `test_report_help_is_bilingual` — `script_3_report.py --help` output contains both the English "Usage (English)" section and the Hungarian "Hasznalat (magyar)" section; assert the option table is mirrored (each `--option` appears in both halves).
- `test_report_console_log_lines_match_bilingual_regex` — AST-grep the source: walk every `print(...)` and `logger.{info,warning,error}(...)` call in `scripts/script_3_report.py`; assert each format-string constant matches `^\[en\] .+ / \[hu\] .+$`; assert each f-string contains both `[en]` and `[hu]` markers.
- `test_report_honors_platforms_conditional` — when a profile disables a skill for a specific platform only, the reporter (called without `--platform`) lists it as enabled; with `--platform linux` it lists it as disabled. Assert the same logic as Script #2.
- `test_report_no_args_prints_help` — `script_3_report.py` with no args prints bilingual help and exits 0.
- `test_report_coverage_100_percent` — `pytest --cov=scripts.script_3_report --cov-branch --cov-fail-under=100` exits 0.
- `test_report_no_modify_when_curator_partial` — when the Curator returns data for some skills and `None` for others, the reporter still writes nothing and exits 0.

## Branch coverage matrix (the bits the 100% target is hardest on)

- Script #1: every `argparse` choice; every exit code (0/1/2/3/4/5); the with/without `--task-e-redirect` × with/without `--no-schema-redirect` × with/without `--force` × with/without `--i-accept-line-drift` matrix.
- Script #2: empty-profile / single-profile / N-profile / missing-`~/.hermes` matrix; `set_hermes_home_override` raise × `os.environ` set × `do_install` raise × `clear_skills_system_prompt_cache` raise matrix.
- Script #3: empty-profile / single-profile / N-profile / missing-`~/.hermes` / missing-Curator matrix; tokenizer-available × tokenizer-fallback matrix; all three `--sort` modes × ascending/descending × n/a-tiebreaker matrix; profile + platform toggle matrix; bilingual-help × no-args × named-profile × default-profile matrix.
- Installer: TTY confirmed × `--yes` × real-`~/.hermes` × tmp-`HERMES_HOME` × collision × partial-copy × read-only target matrix.
- Migrated `run_eval.py`: `HERMES_SESSION` set × unset × helper called × subprocess env stripped matrix.

## TDD ordering (the work order for Phase 5)

1. Write `tests/unit/test_scope.py` (the simplest) first. Make it pass.
2. Write `tests/unit/test_subprocess.py`. Make it pass.
3. Write `tests/unit/test_advisory.py`. Make it pass.
4. Write `tests/unit/test_installer.py` (mocked paths). Make it pass.
5. Write `tests/integration/test_installer_apply.py` (real fixture HERMES_HOME). Make it pass.
6. Write `tests/unit/test_script_1_*.py` (one per branch). Make them pass.
7. Write `tests/integration/test_script_1_apply.py`. Make it pass.
8. Write `tests/unit/test_script_2_*.py`. Make them pass.
9. Write `tests/integration/test_script_2_apply.py`. Make it pass.
10. Write `tests/unit/test_script_3_*.py` (sort, profile, tokens, usage, bilingual, read-only). Make them pass.
11. Write `tests/integration/test_script_3_read_only.py` (asserts zero bytes written across a full run). Make it pass.
12. Write `tests/unit/test_run_eval.py`, `test_improve_description.py`, `test_generate_review.py`. Make it pass.
13. Write `tests/integration/test_eval_pipeline_end_to_end.py`. Make it pass.
14. Write `tests/integration/test_eval_viewer_static_open.py`. Make it pass.
15. Run the meta-tests (`test_bilingual_hook_*`, `test_snapshot_*`, `test_coverage_*`, lint suite). Fix any gaps.

## Seed-minimal-fixture contract (`tests/fixtures/minimal_hermes/seed_minimal.py`)

The `hermes_checkout` fixture calls `seed_minimal(checkout)` to lay down the
minimum tree so Script #1's pre-validation can resolve all patch anchors.
The fixture is the contract; the patch anchors are read from it.

**Files written by `seed_minimal(checkout: Path) -> None`**:

| path (relative to checkout) | anchor | required text | purpose |
| --- | --- | --- | --- |
| `agent/skill_utils.py` | function def | `def extract_skill_description(frontmatter: Dict[str, Any]) -> str:` | function definition anchor (S1.cap) |
| `agent/skill_utils.py` | cap-raise site | `    if len(desc) > 60:` | cap-raise site (S1.cap, UNPATCHED state) |
| `agent/skill_utils.py` | replacement target | `        return desc[:57] + "..."` | the cap-raise replacement target |
| `tools/skills_tool.py` | constant | `MAX_DESCRIPTION_LENGTH = 1024` | the patched comparator constant (imported by S1.cap's replacement) |
| `agent/__init__.py` | n/a | (empty) | makes `agent` a package so `from agent.skill_utils import extract_skill_description` resolves in tests |
| `tools/__init__.py` | n/a | (empty) | makes `tools` a package so `from tools.skills_tool import MAX_DESCRIPTION_LENGTH` resolves in tests |

The fixture also exposes a `seed_minimal_patched(checkout)` variant that
replaces the literal `60` with `MAX_DESCRIPTION_LENGTH` on the cap-raise site
AND replaces `desc[:57]` with `desc[:MAX_DESCRIPTION_LENGTH - 3]`, so the
integration tests cover BOTH the unpatched cap-state (default) and the
patched cap-state (`--with-short-description` false-positive guard). The
patched variant must use the same `MAX_DESCRIPTION_LENGTH - 3` idiom found
in `tools/skills_tool.py` lines 659 and 814.

**No other files are written.** `hermes_cli/` is NOT seeded (Script #1's
cap-raise does not touch it). `home/`, `profiles/`, `sessions/` are NOT
seeded (Script #2's profile audit uses a different fixture).

## Meta-test guarding the fixture contract

`test_seed_minimal_matches_patch_anchors` (added to the TDD test list
above) runs `seed_minimal(tmp_checkout)`, reads the 4 anchor files, and
asserts the contract lines match. A second variant
`test_seed_minimal_patched_variant_replaces_literal_60` covers the
patched state. A third variant
`test_seed_minimal_patched_variant_completes_cap_raise` asserts the
patched slice is `desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` (not the
partial patch `desc[:57] + "..."`). The meta-tests are the single source
of truth that the fixture stays in sync with the patch anchors — if a
future Hermes release moves the cap-raise site or changes the slice
idiom, the meta-tests fail first, naming the drifted anchor, and the
fixture is updated to match.

## C3 contract inventory (18 rows)

> **Namespace note (R5).** The `T3.*` namespace belongs to **07's skill-port inventory** (Claude-binding replacements). The `C3.*` namespace is **09's contract inventory** (acceptance criteria + patch anchors). Different namespaces prevent ID collision when cross-referencing 07 and 09 from 12-Q6.

The C3 inventory below is the binding contract between the migrated
plugin and the upstream Hermes agent. Each row is enforced by a dedicated
contract test (`test_C3_001` through `test_C3_018`).

| ID | Site | Hermes string (forbidden) | Migrated string (required) | AC ref |
| --- | --- | --- | --- | --- |
| C3.001 | `agent/prompt_builder.py` SKILLS_GUIDANCE | (none — additive append) | appended: "Before creating a NEW skill, check installed skills; if skill-creator is installed, skill_view(name='skill-creator') and follow its authoring/validation guidance; persist with skill_manage(action='create'); if absent, continue with built-in class-level rules; NEVER auto-install it." | AC-1.1 |
| C3.002 | `agent/prompt_builder.py` MEMORY_GUIDANCE | "If you've discovered a new way to do something, solved a problem that could be necessary later, save it as a skill with the skill tool." | "...save it as a skill with the skill tool. Before creating a NEW skill, consult skill-creator (if installed) for authoring/validation guidance; otherwise follow built-in class-level rules." | AC-1.1 |
| C3.003 | `agent/prompt_builder.py` `build_skills_system_prompt` near `skill_manage(action='patch')` | "If a skill has issues, fix it with skill_manage(action='patch')." | same + appended new-skill rule | AC-1.1 |
| C3.004 | `agent/prompt_builder.py` `build_skills_system_prompt` near "offer to save as a skill" | "After difficult/iterative tasks, offer to save as a skill." | same + appended new-skill rule | AC-1.1 |
| C3.005 | `agent/background_review.py` `_SKILL_REVIEW_PROMPT` option 4 | "4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL when no existing skill covers the class." | same + inserted skill-creator consultation step before `skill_manage(action='create')` | AC-1.1 |
| C3.006 | `agent/background_review.py` `_COMBINED_REVIEW_PROMPT` option 4 | "4. CREATE A NEW CLASS-LEVEL UMBRELLA when nothing exists." | same + inserted skill-creator consultation step; shares constant with C3.005 | AC-1.1 |
| C3.007 | `tools/skill_manager_tool.py` `SKILL_MANAGE_SCHEMA` | (no skill-creator language today) | appended clarifier: "skill-creator, when installed, provides authoring guidance only. Use skill_manage to persist all skill files." | AC-1.1 |
| C3.008 | `website/docs/user-guide/features/skills.md` "## Agent-Managed Skills (skill_manage tool)" | (no skill-creator language today) | appended maybe-patch-points clarifications (skill_manage is the writer; skill-creator is optional/hub-installed/NOT bundled/NOT mandatory; absence doesn't disable auto-creation; background never auto-installs) | AC-1.1 |
| C3.009 | `agent/skill_utils.py` `extract_skill_description` cap-raise | `if len(desc) > 60:` | `if len(desc) > MAX_DESCRIPTION_LENGTH:` | AC-1.2 |
| C3.010 | `agent/skill_utils.py` `extract_skill_description` slice | `return desc[:57] + "..."` | `return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` | AC-1.2 |
| C3.011 | `tools/skill_manager_tool.py` `SKILL_MANAGE_SCHEMA` | (preserved verbatim) | unchanged | AC-1.3 |
| C3.012 | `hermes_cli/skills_config.py` `save_disabled_skills` callsite (Script #2) | `save_disabled_skills(config, names=disabled, platform=plat)` | `save_disabled_skills(config, disabled, platform=plat)` (positional `Set[str]`) | AC-1.4 |
| C3.013 | Plugin install path for `skill-creator` | (nested `src/hermes_skill_creator_plugin/skills/skill-creator/`) | flat `~/.hermes/skills/skill-creator/` (standalone top-level deliverable) | AC-4.1 |
| C3.014 | Plugin manifest format | `plugin.json` | `plugin.yaml` (manifest fields: name/version/description/author/provides_hooks; no `kind`) | AC-1.1 |
| C3.015 | Plugin entry-point model | split `hooks:register` + `skill_register:register` | single `register(ctx)` in `__init__.py` calling `ctx.register_hook` + `ctx.register_skill` (advisory only) | AC-1.1 |
| C3.016 | `clear_skills_system_prompt_cache` callsite | `clear_skills_system_prompt_cache` (location TBD) | `agent.prompt_builder.clear_skills_system_prompt_cache(clear_snapshot=True)` | AC-1.4 |
| C3.017 | `spawn_background_review_thread` selection logic | (preserved verbatim) | unchanged: patch → update-umbrella → support-file → create | AC-1.1 |
| C3.018 | `description[:1021]` true-cap test | (no test today) | parametrized test injecting a 1100-char description; asserts the returned string is `1100 chars → 1021 chars + "..."` (NOT `60 chars`) | AC-1.2 |

The C3 contract tests are parametrized via `pytest.mark.parametrize` so
each binding replacement is verified individually:

```python
@pytest.mark.parametrize("site,forbidden,required,anchor", [
    ("agent/prompt_builder.py SKILLS_GUIDANCE",
     None,
     "Before creating a NEW skill, check installed skills",
     "After completing a complex task"),
    ("agent/prompt_builder.py MEMORY_GUIDANCE",
     "save it as a skill with the skill tool.",
     "save it as a skill with the skill tool. Before creating a NEW skill, consult skill-creator",
     "If you've discovered a new way"),
    ("agent/skill_utils.py extract_skill_description cap",
     "if len(desc) > 60:",
     "if len(desc) > MAX_DESCRIPTION_LENGTH:",
     "def extract_skill_description"),
    ("agent/skill_utils.py extract_skill_description slice",
     'return desc[:57] + "..."',
     'return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."',
     "def extract_skill_description"),
    # ... 14 more rows, one per C3 ID ...
])
def test_C3_binding_replacement(site, forbidden, required, anchor, hermes_checkout):
    ...
```

<!-- end of file: 345 lines (budget 300) -->
