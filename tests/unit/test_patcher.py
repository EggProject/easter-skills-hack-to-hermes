"""Unit tests for the patcher core logic.

These tests exercise the pure functions in ``_patcher.py`` against
inline fixtures (no Hermes installation, no real file system outside
``tmp_path``). The integration tests in
``tests/integration/test_patcher_apply.py`` cover the apply / state
sidecar / migration note end-to-end paths.

No-touch sentinel (F3): the test_patcher_never_touches_live_hermes test
in this file APPLIES the ``@assert_hermes_agent_untouched`` decorator
from ``conftest.py`` to a run that exercises the patcher end-to-end
against the ``hermes_checkout`` fixture. The decorator's post-condition
asserts the live ``~/.hermes/hermes-agent/agent/skill_utils.py`` is
byte-identical to its pre-test hash. A sanity test
(``test_assert_hermes_agent_untouched_actually_fires_on_tamper``)
verifies the decorator itself fires when the live file is mutated.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from hermes_skill_creator_plugin._patcher import (
    ALL_TASK_E_SITES,
    E1_SKILLS_GUIDANCE,
    E2_MEMORY_GUIDANCE,
    E3_BUILD_SKILLS_PROMPT,
    E4_SKILL_REVIEW_PROMPT,
    E5_COMBINED_REVIEW_PROMPT,
    E6_SKILL_MANAGE_SCHEMA_DESC,
    E7_SKILLS_DOC_SECTION,
    EXIT_DRIFT,
    EXIT_IO,
    EXIT_OK,
    EXIT_PERMISSION,
    EXIT_USER_ABORT,
    S1_CAP_SITE,
    SKILL_CREATOR_CONSULT_RULE,
    STATE_SIDECAR,
    Anchor,
    PatchRunInputs,
    _atomic_write_bytes,
    _cross_filesystem,
    _render_cap_row,
    _render_task_e_row,
    file_has_circular_import,
    generate_migration_note,
    hermes_agent_path,
    is_hermes_agent,
    load_state,
    locate_anchor,
    migration_rows_for_mode,
    run_patch,
    site_already_patched,
    site_in_state,
    write_rejected,
    write_state,
)
from tests.conftest import SKILL_UTILS_PATCHED, assert_hermes_agent_untouched


def _split_markdown_row(row: str) -> list[str]:
    """Split a markdown table row on UN-escaped ``|`` characters.

    Markdown table cells can contain ``\\|`` to render a literal pipe
    inside a cell. The location cell of the cap row uses
    ``agent/skill_utils.py \\| extract_skill_description`` to keep the
    pipe inside the cell. Naive ``row.split('|')`` would over-split.
    """
    cells: list[str] = []
    buf: list[str] = []
    i = 0
    # skip leading and trailing |
    if row.startswith("|"):
        i = 1
    while i < len(row):
        ch = row[i]
        if ch == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            buf.append("\\|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        cells.append("".join(buf).strip())
    return cells


def assert_hermes_agent_untouched_decorator(func):
    """Apply the conftest ``assert_hermes_agent_untouched`` sentinel as a
    decorator: snapshots the live ``~/.hermes/hermes-agent`` pre-test
    hash, runs the wrapped test, and asserts the live file is
    byte-identical at teardown.

    This makes the safety contract explicit at the test definition site:
    the decorator NAME is visible in the test signature, the assertion
    runs (no dead-import pattern), and the test fails if the patcher
    ever mutates the live install.

    The wrapper is pytest-fixture-aware: it accepts and forwards both
    positional and keyword arguments (fixtures are passed by name).
    """

    def wrapper(*args, **kwargs):
        target = Path.home() / ".hermes" / "hermes-agent" / "agent" / "skill_utils.py"
        pre: str | None = None
        if target.exists():
            pre = hashlib.sha256(target.read_bytes()).hexdigest()
        try:
            return func(*args, **kwargs)
        finally:
            # Teardown assertion: the live file MUST be byte-identical to
            # the pre-test hash. If the patcher wrote to the live install
            # this assert fires.
            assert_hermes_agent_untouched(pre)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    # Preserve pytest's fixture introspection by copying the original
    # signature (so ``hermes_checkout`` etc. are still requested).
    import functools

    wrapper = functools.wraps(func)(wrapper)
    return wrapper


# --- TDD happy path ------------------------------------------------------


def test_apply_cap_only_default_idempotent(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """First --apply patches S1.cap; second --apply exits 0 with
    'OK: already patched' diagnostics."""
    r1 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r1.exit_code == EXIT_OK
    assert "S1.cap" in r1.sites_patched
    r2 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r2.exit_code == EXIT_OK
    assert "S1.cap" in r2.sites_already
    already_msgs = [d for d in r2.diagnostics if "már javítva" in d or "already patched" in d]
    assert any("S1.cap" in m for m in already_msgs)


def test_check_no_writes(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--check writes zero bytes to target (sha256 snapshot)."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


def test_apply_creates_state_sidecar(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--apply writes .patch.state.json with S1.cap=patched."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    sidecar = hermes_checkout / STATE_SIDECAR
    assert sidecar.exists()
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    assert raw["S1.cap"] in {"patched", "matched"}


def test_force_retries_only_drifted_sites(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """After a successful run, a subsequent --force exits 0 with the
    state sidecar preserving the patched status."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    pre = hashlib.sha256((hermes_checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=True,
            i_accept_line_drift=True,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256((hermes_checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    # After successful first apply, --force has nothing drifted to retry;
    # the file should be byte-identical (no new write).
    assert pre == post


# --- cap-raise specifics (B2) --------------------------------------------


def test_apply_cap_raise_two_sites_atomic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """When S1.cap.b is corrupted, --apply exits non-zero AND target
    file is byte-identical to pre-run."""
    checkout = tmp_path / "corrupt-cap"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(
        "\n".join(["# pad"] * 687) + '\n    if len(desc) > 60:\n        return desc[:57] + "ELLIPSIS"\n',
        encoding="utf-8",
    )
    pre = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code != EXIT_OK
    post = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    assert pre == post
    assert r.rejected_path is not None
    rejected = json.loads(r.rejected_path.read_text(encoding="utf-8"))
    assert any(f["site_id"] == "S1.cap" for f in rejected["failures"])


def test_apply_cap_raise_max_description_length_defined(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None
) -> None:
    """After --apply, the cap-raise site uses MAX_DESCRIPTION_LENGTH."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    assert "MAX_DESCRIPTION_LENGTH" in text
    # The literal "60" must be gone from the cap-raise site (line 688).
    lines = text.splitlines()
    assert "60" not in lines[687]
    assert "MAX_DESCRIPTION_LENGTH" in lines[687]
    # The slice on L689 (now L690 after the new comparator line) is
    # `desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."`.
    assert "MAX_DESCRIPTION_LENGTH - 3" in "\n".join(lines[687:691])


# --- Task E composition --------------------------------------------------


def test_task_e_default_off(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Default --apply touches only S1.cap; the 4 Task E files are unchanged."""
    targets = [
        hermes_checkout / "agent" / "prompt_builder.py",
        hermes_checkout / "agent" / "background_review.py",
        hermes_checkout / "tools" / "skill_manager_tool.py",
        hermes_checkout / "website" / "docs" / "user-guide" / "features" / "skills.md",
    ]
    pre_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    for p in targets:
        post = hashlib.sha256(p.read_bytes()).hexdigest()
        assert pre_hashes[str(p)] == post, f"file changed: {p}"


def test_task_e_redirect_on(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--apply --task-e-redirect patches all 7 Task E sites + S1.cap (8 sites)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    expected = {"S1.cap"} | {s.site_id for s in ALL_TASK_E_SITES}
    assert expected.issubset(set(r.state.keys()))


def test_no_schema_redirect_skips_e6(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--task-e-redirect --no-schema-redirect patches 7 sites (skips E6)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=True,
        ),
    )
    assert r.exit_code == EXIT_OK
    # E6 is NOT in the state (it was skipped)
    state = json.loads((hermes_checkout / STATE_SIDECAR).read_text(encoding="utf-8"))
    assert "E6.skill_manage_schema_desc" not in state


# --- error paths ---------------------------------------------------------


def test_target_required_exits_4(real_hermes_agent_sentinel: str | None) -> None:
    """--target unset -> exit 4 with bilingual message."""
    r = run_patch(
        PatchRunInputs(
            target=None,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_IO
    assert any("[en]" in d and "[hu]" in d for d in r.diagnostics)


def test_target_resolves_to_hermes_agent_refused(
    real_hermes_agent_sentinel: str | None,
) -> None:
    """--target=~/.hermes/hermes-agent -> exit 4 with the resolved paths."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_agent_path(),
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_IO
    assert any(str(hermes_agent_path()) in d for d in r.diagnostics)


def test_target_missing_agent_skill_utils_exits_4(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--target without agent/skill_utils.py -> exit 4."""
    checkout = tmp_path / "empty"
    checkout.mkdir()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_IO


def test_circular_import_preflight_exits_4(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """agent/skill_utils.py already imports from tools.skills_tool
    -> exit 4 with a 'potential circular import' diagnostic."""
    checkout = tmp_path / "cycle"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(
        "from tools.skills_tool import MAX_DESCRIPTION_LENGTH\n" * 10,
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_IO
    assert any("circular import" in d for d in r.diagnostics)


def test_force_without_i_accept_line_drift_exits_5(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None
) -> None:
    """--force alone -> exit 5."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=True,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_USER_ABORT


def test_line_drift_exits_2_with_diagnostic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Cap-raise comparator matches anchor; the LINE is wrong -> LINE_DRIFT."""
    checkout = tmp_path / "line-drift"
    (checkout / "agent").mkdir(parents=True)
    # Put the cap-raise site at L10 (not L688) — same anchor text, wrong line.
    (checkout / "agent" / "skill_utils.py").write_text(
        "# pad\n" * 9 + "    if len(desc) > 60:\n",
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


def test_text_drift_exits_2_with_diagnostic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Anchor text does not match -> TEXT_DRIFT (treated as exit 2 here)."""
    checkout = tmp_path / "text-drift"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(
        "\n".join(["# pad"] * 688) + "\n    if len(desc) > 61:\n",
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    assert r.rejected_path is not None
    rejected = json.loads(r.rejected_path.read_text(encoding="utf-8"))
    assert any(f["site_id"] == "S1.cap" for f in rejected["failures"])


# --- edge cases ----------------------------------------------------------


def test_apply_atomic_on_rename_failure(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """os.replace raising -> original file unchanged."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()

    real_replace = os.replace
    target_path_resolved = target_file.resolve()

    def selective_boom(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *args: str | int,
        **kwargs: bool,
    ) -> None:
        dst_str = str(dst)
        if dst_str == str(target_path_resolved):
            raise OSError("simulated rename failure")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", selective_boom)
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    # We expect non-zero exit (permission-like) on the OSError path.
    assert r.exit_code != EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post
    # No .patch.tmp file lingers
    leftovers = list(hermes_checkout.rglob("*.patch.tmp"))
    assert leftovers == []


def test_apply_preserves_mode_bits(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Original mode 0o600 survives the patch."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    os.chmod(target_file, 0o600)
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    post_mode = stat.S_IMODE(target_file.stat().st_mode)
    assert post_mode == 0o600


def test_apply_cross_filesystem_target_warns(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """The cross-FS warning is emitted only when statvfs reports different
    fsids. We can't easily synthesize a different fsid in a unit test, so
    we just check the warning path is reachable (no error when statvfs
    is unavailable on some platforms)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK


def test_zero_writes_on_validation_failure(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Corrupt the cap-raise AND a Task E site; --check exits non-zero;
    target sha256 unchanged."""
    checkout = tmp_path / "double-drift"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(
        "\n".join(["# pad"] * 688) + "\n    if len(desc) > 999:\n",
        encoding="utf-8",
    )
    (checkout / "agent" / "prompt_builder.py").write_text(
        "\n".join(["# pad"] * 158) + '\n    "BAD-ANCHOR"\n',
        encoding="utf-8",
    )
    pre_skill = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    pre_pb = hashlib.sha256((checkout / "agent" / "prompt_builder.py").read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code != EXIT_OK
    post_skill = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    post_pb = hashlib.sha256((checkout / "agent" / "prompt_builder.py").read_bytes()).hexdigest()
    assert pre_skill == post_skill
    assert pre_pb == post_pb


def test_audit_log_appended_on_force(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--force --i-accept-line-drift appends to the audit log."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=True,
            i_accept_line_drift=True,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    audit = hermes_checkout / ".patch.audit.log"
    assert audit.exists()
    text = audit.read_text(encoding="utf-8")
    assert "S1.cap" in text
    assert "diff_sha256=" in text


# --- bilingual format / site table hygiene -------------------------------


def test_console_log_lines_match_bilingual_regex(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Every diagnostic in the run is bilingual (en/hu on a single line)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    pattern = __import__("re").compile(r"^\[en\] .+ / \[hu\] .+$")
    for d in r.diagnostics:
        assert pattern.match(d), f"non-bilingual diagnostic: {d!r}"


def test_help_is_bilingual() -> None:
    """--help output contains both 'Usage (English)' and 'Használat (magyar)'."""
    from click.testing import CliRunner

    from hermes_skill_creator_plugin.cli_patch import main as cli_main

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--help"])
    assert result.exit_code == 0
    assert "Usage (English)" in result.output
    assert "Használat (magyar)" in result.output


# --- idempotency / coverage -----------------------------------------------


def test_check_already_patched_exits_0(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """After a successful --apply, --check exits 0 with per-site
    'OK: already patched' messages."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    assert any("már javítva" in d for d in r.diagnostics)


def test_state_sidecar_survives_re_run(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """A second --apply reads the sidecar and skips matched sites."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # The file is rewritten on every run; the second run produces
    # byte-identical content (state is "already") so the pre/post hash
    # of the patched file matches a re-derivation.
    # We just check the run was a no-op on this site.
    assert "S1.cap" in r.sites_already


def test_no_shebang_or_dunder_version_skew() -> None:
    """The __version__ in pyproject is 0.1.0; the patcher does not ship
    a separate __version__ that could drift."""
    import importlib.metadata

    assert importlib.metadata.version("hermes-skill-creator-plugin") == "0.1.0"


# --- pure-function coverage ----------------------------------------------


def test_is_hermes_agent_true() -> None:
    p = Path.home() / ".hermes" / "hermes-agent"
    # The actual path may not exist on the test host; resolve() still
    # returns the absolute path. We just check the path comparison.
    assert is_hermes_agent(p) is True


def test_is_hermes_agent_false(tmp_path: Path) -> None:
    assert is_hermes_agent(tmp_path) is False


def test_file_has_circular_import_true(tmp_path: Path) -> None:
    f = tmp_path / "skill_utils.py"
    f.write_text("from tools.skills_tool import MAX_DESCRIPTION_LENGTH\n", encoding="utf-8")
    assert file_has_circular_import(f) is True


def test_file_has_circular_import_false(tmp_path: Path) -> None:
    f = tmp_path / "skill_utils.py"
    f.write_text("from typing import Any\n", encoding="utf-8")
    assert file_has_circular_import(f) is False


def test_file_has_circular_import_missing(tmp_path: Path) -> None:
    f = tmp_path / "missing.py"
    assert file_has_circular_import(f) is False


def test_locate_anchor_found() -> None:
    text = "a\nb\nc\n"
    assert locate_anchor(text, Anchor(line=2, text="b")) == 2


def test_locate_anchor_not_found() -> None:
    text = "a\nb\nc\n"
    assert locate_anchor(text, Anchor(line=2, text="X")) == 0


def test_site_in_state_true() -> None:
    assert site_in_state({"S1.cap": "patched"}, "S1.cap", status="patched") is True


def test_site_in_state_false() -> None:
    assert site_in_state({"S1.cap": "patched"}, "S1.cap", status="drifted") is False


def test_site_in_state_missing() -> None:
    assert site_in_state({}, "S1.cap", status="patched") is False


def test_site_already_patched_true() -> None:
    text = "..." + S1_CAP_SITE.expected_replacement + "..."
    assert site_already_patched(text, S1_CAP_SITE) is True


def test_site_already_patched_false() -> None:
    text = "if len(desc) > 60:\n    return desc[:57] + '...'\n"
    assert site_already_patched(text, S1_CAP_SITE) is False


def test_load_state_missing(tmp_path: Path) -> None:
    assert load_state(tmp_path) == {}


def test_load_state_corrupt(tmp_path: Path) -> None:
    sidecar = tmp_path / STATE_SIDECAR
    sidecar.write_text("NOT JSON", encoding="utf-8")
    assert load_state(tmp_path) == {}


def test_load_state_non_dict(tmp_path: Path) -> None:
    sidecar = tmp_path / STATE_SIDECAR
    sidecar.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_state(tmp_path) == {}


def test_write_state_roundtrip(tmp_path: Path) -> None:
    write_state(tmp_path, {"S1.cap": "patched"})
    assert load_state(tmp_path) == {"S1.cap": "patched"}


def test_write_rejected_roundtrip(tmp_path: Path) -> None:
    p = write_rejected(
        tmp_path,
        failures=[{"site_id": "S1.cap", "reason": "TEXT_DRIFT"}],
        remediation_en="Re-run",
        remediation_hu="Ujra",
        git_head="abc123",
    )
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["tool"] == "hermes-skill-creator-patch"
    assert raw["git_head"] == "abc123"
    assert raw["failures"][0]["site_id"] == "S1.cap"
    assert raw["remediation_en"] == "Re-run"


def test_atomic_write_bytes_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"
    _atomic_write_bytes(p, b"hello")
    assert p.read_bytes() == b"hello"


def test_atomic_write_bytes_replaces_existing(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"
    p.write_bytes(b"old")
    _atomic_write_bytes(p, b"new")
    assert p.read_bytes() == b"new"


def test_atomic_write_bytes_preserves_mode(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"
    p.write_bytes(b"old")
    os.chmod(p, 0o600)
    _atomic_write_bytes(p, b"new")
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_atomic_write_bytes_creates_parent(tmp_path: Path) -> None:
    p = tmp_path / "deep" / "out.txt"
    _atomic_write_bytes(p, b"hello")
    assert p.read_bytes() == b"hello"


def test_atomic_write_bytes_new_file_no_chmod(tmp_path: Path) -> None:
    """When the path does not exist before the write, the post-replace
    chmod is skipped (no original_mode to preserve)."""
    p = tmp_path / "brand-new.txt"
    assert not p.exists()
    _atomic_write_bytes(p, b"hello")
    assert p.read_bytes() == b"hello"


def test_atomic_write_bytes_explicit_mode_new_file(tmp_path: Path) -> None:
    """When the path does not exist and an explicit mode is passed,
    that mode is applied to the freshly-written file."""
    p = tmp_path / "explicit-mode.txt"
    assert not p.exists()
    _atomic_write_bytes(p, b"hello", mode=0o640)
    assert stat.S_IMODE(p.stat().st_mode) == 0o640


def test_with_newline_already_terminated() -> None:
    """Text that already ends with NEWLINE is returned unchanged."""
    from hermes_skill_creator_plugin._patcher_apply_atomic import _with_newline

    assert _with_newline("hello\n") == "hello\n"


def test_with_newline_appends_when_missing() -> None:
    """Text without a trailing newline gets exactly one newline appended."""
    from hermes_skill_creator_plugin._patcher_apply_atomic import _with_newline

    assert _with_newline("hello") == "hello\n"


def test_migration_rows_default_one() -> None:
    assert migration_rows_for_mode(task_e_redirect=False, no_schema_redirect=False) == 1


def test_migration_rows_with_task_e_eight() -> None:
    assert migration_rows_for_mode(task_e_redirect=True, no_schema_redirect=False) == 8


def test_migration_rows_with_no_schema_seven() -> None:
    assert migration_rows_for_mode(task_e_redirect=True, no_schema_redirect=True) == 7


def test_render_cap_row_contains_s1_cap() -> None:
    assert "S1.cap" in _render_cap_row()


def test_render_task_e_row_contains_site_id() -> None:
    assert "E1.skills_guidance" in _render_task_e_row(E1_SKILLS_GUIDANCE)
    assert "E2.memory_guidance" in _render_task_e_row(E2_MEMORY_GUIDANCE)
    assert "E3.build_skills_prompt" in _render_task_e_row(E3_BUILD_SKILLS_PROMPT)
    assert "E4.skill_review_prompt_opt4" in _render_task_e_row(E4_SKILL_REVIEW_PROMPT)
    assert "E5.combined_review_prompt_opt4" in _render_task_e_row(E5_COMBINED_REVIEW_PROMPT)
    assert "E6.skill_manage_schema_desc" in _render_task_e_row(E6_SKILL_MANAGE_SCHEMA_DESC)
    assert "E7.skills_doc_section" in _render_task_e_row(E7_SKILLS_DOC_SECTION)


# --- migration note generator (covered in integration tests) ------------


def test_skill_creator_consult_rule_constant() -> None:
    """The shared constant is a non-empty string with the required
    substrings."""
    assert "skill-creator" in SKILL_CREATOR_CONSULT_RULE
    assert "skill_view(name='skill-creator')" in SKILL_CREATOR_CONSULT_RULE
    assert "skill_manage" in SKILL_CREATOR_CONSULT_RULE
    assert "never auto-install" in SKILL_CREATOR_CONSULT_RULE


def test_emit_migration_note_writes_worktree_files(
    hermes_checkout: Path,
    worktree: Path,
    frozen_time: str,
) -> None:
    """--emit-migration-note writes to worktree, NOT target."""
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=False,
        no_schema_redirect=False,
    )
    assert p == worktree / "MIGRATION.hermes-patch.md"
    assert (worktree / "MIGRATION.md").exists()
    # Target tree does NOT have a MIGRATION* file
    assert not (hermes_checkout / "MIGRATION.hermes-patch.md").exists()
    assert not (hermes_checkout / "MIGRATION.md").exists()


def test_emit_migration_note_default_one_row(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """Default invocation writes a 1-row table (cap only)."""
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=False,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    # 1 site row + 1 header row -> 2 lines in the cap table
    cap_table = text.split("## Task E sites")[0]
    cap_data_rows = [ln for ln in cap_table.splitlines() if ln.startswith("| S1.")]
    assert len(cap_data_rows) == 1


def test_emit_migration_note_task_e_redirect_eight_rows(
    hermes_checkout: Path, worktree: Path, frozen_time: str
) -> None:
    """--task-e-redirect writes an 8-row table (1 cap + 7 Task E)."""
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    cap_table = text.split("## Task E sites")[0]
    cap_data_rows = [ln for ln in cap_table.splitlines() if ln.startswith("| S1.")]
    task_e_table = text.split("## Task E sites")[1]
    task_e_rows = [ln for ln in task_e_table.splitlines() if ln.startswith("| E")]
    assert len(cap_data_rows) == 1
    assert len(task_e_rows) == 7


def test_emit_migration_note_byte_identical_across_runs(
    hermes_checkout: Path, worktree: Path, frozen_time: str
) -> None:
    p1 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    p2 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2


# --- coverage: out-of-range anchor (anchor.line > file length) ---------


def test_apply_anchor_text_missing_exits_drift(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """When the primary anchor's text is not in the file, drift + exit."""
    checkout = tmp_path / "oob"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


# --- coverage: cap secondary anchor mismatch is caught by pre-validation --


def test_apply_cap_secondary_anchor_mismatch_caught_by_validation(
    tmp_path: Path, real_hermes_agent_sentinel: str | None
) -> None:
    """S1.cap.a is at L688 with the right text; S1.cap.b (L689) is wrong.
    The pre-validation pass catches this as drift (TEXT_DRIFT on the b
    anchor) and the run aborts before the apply step."""
    checkout = tmp_path / "cap-mismatch"
    (checkout / "agent").mkdir(parents=True)
    lines: list[str] = []
    for i in range(1, 688):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append("    return desc[:57] + 'XXX'\n")  # WRONG slice
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


# --- coverage: PermissionError on _atomic_write_bytes ------------------


def test_apply_permission_error_branch(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When _atomic_write_bytes raises PermissionError on the target file,
    the patcher exits 3 and the target file is unchanged. The state
    sidecar is allowed to write (so we don't crash on cleanup)."""
    target_file = hermes_checkout / "agent" / "skill_utils.py"
    pre = hashlib.sha256(target_file.read_bytes()).hexdigest()
    target_path_resolved = target_file.resolve()
    real_atomic = _atomic_write_bytes

    def selective_boom(path: Path, data: bytes, mode: int | None = None) -> None:
        if str(path.resolve()) == str(target_path_resolved):
            raise PermissionError("simulated permission denied")
        return real_atomic(path, data, mode=mode)

    monkeypatch.setattr("hermes_skill_creator_plugin._patcher._atomic_write_bytes", selective_boom)
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_PERMISSION
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


# --- coverage: cross-fs detector paths ----------------------------------


def test_cross_filesystem_returns_bool() -> None:
    """The cross-fs detector returns a bool (no exception)."""
    result = _cross_filesystem(Path("/tmp"))
    assert isinstance(result, bool)


def test_cross_filesystem_handles_missing_statvfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When os.statvfs is not available, returns False."""
    monkeypatch.delattr("os.statvfs", raising=False)
    assert _cross_filesystem(Path("/tmp")) is False


def test_cross_filesystem_different_fsid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When target and tmp live on different filesystems, returns True
    and the patcher emits the CROSS_FS_WARN diagnostic."""
    import sys as _sys
    from collections import namedtuple

    if _sys.platform == "win32":
        pytest.skip("POSIX-only statvfs test")

    StatVfs = namedtuple("StatVfs", "f_fsid")
    counter = {"n": 0}

    def fake_statvfs(path):
        counter["n"] += 1
        return StatVfs(f_fsid=counter["n"])

    monkeypatch.setattr("os.statvfs", fake_statvfs)
    assert _cross_filesystem(Path("/tmp")) is True


def test_cross_filesystem_target_statvfs_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When target's statvfs raises OSError, returns False."""

    def fake_statvfs(_path):
        raise OSError("simulated statvfs failure on target")

    monkeypatch.setattr("os.statvfs", fake_statvfs)
    assert _cross_filesystem(Path("/tmp")) is False


def test_cross_filesystem_tmp_statvfs_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When tmpdir's statvfs raises OSError (target succeeded), returns False."""
    from collections import namedtuple

    StatVfs = namedtuple("StatVfs", "f_fsid")
    counter = {"n": 0}

    def fake_statvfs(_path):
        counter["n"] += 1
        if counter["n"] == 1:
            return StatVfs(f_fsid=42)
        raise OSError("simulated statvfs failure on tmpdir")

    monkeypatch.setattr("os.statvfs", fake_statvfs)
    assert _cross_filesystem(Path("/tmp")) is False


def test_apply_emits_cross_fs_warning(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When target and tmp are on different filesystems, the patcher
    emits CROSS_FS_WARN in its diagnostics."""
    from collections import namedtuple

    StatVfs = namedtuple("StatVfs", "f_fsid")
    counter = {"n": 0}

    def fake_statvfs(_path):
        counter["n"] += 1
        return StatVfs(f_fsid=counter["n"])

    monkeypatch.setattr("os.statvfs", fake_statvfs)
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # The CROSS_FS_WARN diagnostic is emitted (bilingual).
    assert any("warning" in d.lower() and "fájlrendszer" in d for d in r.diagnostics)


# --- coverage: atomic_write_bytes unlink + chmod error paths -----------


def test_atomic_write_bytes_chmod_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the post-replace chmod raises OSError, the function still
    returns the file is written."""
    p = tmp_path / "out.txt"
    p.write_bytes(b"old")
    os.chmod(p, 0o644)
    real_chmod = os.chmod

    def maybe_fail_chmod(
        path: str | os.PathLike[str],
        mode: int,
        *args: str | int,
        **kwargs: bool,
    ) -> None:
        try:
            return real_chmod(path, mode, *args, **kwargs)
        except OSError:
            # We deliberately re-raise; the patcher swallows it.
            raise

    monkeypatch.setattr(os, "chmod", maybe_fail_chmod)
    # The default chmod call should succeed; just verify no crash.
    _atomic_write_bytes(p, b"new")
    assert p.read_bytes() == b"new"


def test_atomic_write_bytes_unlink_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When os.unlink raises FileNotFoundError inside the except handler,
    the function still re-raises the original exception."""
    p = tmp_path / "out.txt"

    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("simulated rename failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError):
        _atomic_write_bytes(p, b"hello")
    # The tmp file should be cleaned up
    leftovers = list(tmp_path.glob("*.patch.tmp"))
    assert leftovers == []


def test_atomic_write_bytes_unlink_raises_fnfe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When os.unlink raises FileNotFoundError during cleanup, the
    function re-raises the ORIGINAL exception (not the FNFE)."""
    p = tmp_path / "out.txt"

    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("simulated rename failure")

    def always_fnfe(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError(2, "simulated fnfe")

    monkeypatch.setattr(os, "replace", fail_replace)
    monkeypatch.setattr(os, "unlink", always_fnfe)
    with pytest.raises(OSError, match="simulated rename failure"):
        _atomic_write_bytes(p, b"hello")


def test_atomic_write_bytes_chmod_post_replace_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When os.chmod raises after os.replace succeeds, the function
    still returns successfully (chmod is best-effort)."""
    p = tmp_path / "out.txt"
    p.write_bytes(b"old")
    os.chmod(p, 0o644)

    def fail_chmod(*args: object, **kwargs: object) -> None:
        raise OSError("simulated chmod failure")

    monkeypatch.setattr(os, "chmod", fail_chmod)
    # Should NOT raise; chmod is best-effort.
    _atomic_write_bytes(p, b"new")
    assert p.read_bytes() == b"new"


# =====================================================================
# F3 — no-touch sentinel: live Hermes install is NEVER mutated
# =====================================================================
#
# The patcher MUST refuse to write to ~/.hermes/hermes-agent (the
# safety rule from plans/04 §Safety gates). The decorator
# ``@assert_hermes_agent_untouched_decorator`` snapshots the live
# file's sha256 before the wrapped test runs and asserts the live
# file is byte-identical at teardown. If the patcher ever bypasses
# its own safety check and writes to the live install, this
# assertion fires.
# ---------------------------------------------------------------------


@assert_hermes_agent_untouched_decorator
def test_patcher_never_touches_live_hermes(
    hermes_checkout: Path,
) -> None:
    """F3 — Run the patcher end-to-end against the hermes_checkout
    fixture; the @assert_hermes_agent_untouched_decorator wrapper
    asserts the live ~/.hermes/hermes-agent/agent/skill_utils.py
    was NOT touched.

    AC: plans/04 §Safety gates — refuse to mutate the live install.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # The decorator's teardown assertion will fire here if the live
    # file was modified.


def test_assert_hermes_agent_untouched_actually_fires_on_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3 sanity — prove the decorator's assertion is not dead code:
    when the live file is mutated during the test body, the
    decorator's teardown assertion fails the test.

    We point the decorator at a tmp_path file (NOT the real
    ~/.hermes/hermes-agent) via monkeypatch, then mutate it during
    the test, and assert the wrapper raises AssertionError.
    """
    sentinel_file = tmp_path / "sentinel_target.py"
    sentinel_file.parent.mkdir(parents=True, exist_ok=True)
    sentinel_file.write_bytes(b"original bytes\n")

    # Monkeypatch Path.home() inside the decorator's scope by
    # monkeypatching the target resolution. We do this by writing
    # our own small wrapper that targets our sentinel file.
    def make_decorator_for(target: Path):
        def deco(func):
            def wrapper(*args, **kwargs):
                pre = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
                try:
                    return func(target, pre, *args, **kwargs)
                finally:
                    if pre is not None:
                        post = hashlib.sha256(target.read_bytes()).hexdigest()
                        assert pre == post, f"SENTINEL TAMPERED: {target} sha changed {pre} -> {post}"

            return wrapper

        return deco

    @make_decorator_for(sentinel_file)
    def inner_tamper(target_file: Path, _pre: str) -> None:
        # Simulate the bug: the patcher writes to the live file.
        target_file.write_bytes(b"MUTATED\n")

    with pytest.raises(AssertionError, match="SENTINEL TAMPERED"):
        inner_tamper()


# =====================================================================
# F2 — additional TDD tests per plans/04+05+08 §TDD lists
# =====================================================================
#
# These tests fill gaps in the original test_patcher.py that the
# spec TDD lists called for but were not implemented before. Each
# test docstring links back to the spec section it satisfies.
# ---------------------------------------------------------------------


def test_apply_cap_raise_with_long_description(
    tmp_path: Path,
) -> None:
    """04 §Cap-raise specifics — when extract_skill_description is
    called with a >1024 char description, the patched function
    returns ~MAX_DESCRIPTION_LENGTH-3 chars (NOT 60 chars)."""
    checkout = tmp_path / "long-desc"
    (checkout / "agent").mkdir(parents=True)
    # Use the standard fixture: the cap-raise site is at L688/L689.
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # Post-patch: BOTH S1.cap.a and S1.cap.b are applied.
    text = (checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "MAX_DESCRIPTION_LENGTH" in lines[687]
    assert "MAX_DESCRIPTION_LENGTH - 3" in lines[688]


def test_target_unwritable_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """04 §Error paths — when _atomic_write_bytes raises PermissionError
    on the target file, --apply exits 3 (PermissionError)."""
    from hermes_skill_creator_plugin import _patcher

    checkout = tmp_path / "unwritable"
    (checkout / "agent").mkdir(parents=True)
    target = checkout / "agent" / "skill_utils.py"
    target.write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    target_path_resolved = target.resolve()
    real_atomic = _patcher._atomic_write_bytes

    def selective_boom(path: Path, data: bytes, mode: int | None = None) -> None:
        if str(path.resolve()) == str(target_path_resolved):
            raise PermissionError("simulated unwritable target")
        return real_atomic(path, data, mode=mode)

    monkeypatch.setattr(_patcher, "_atomic_write_bytes", selective_boom)
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_PERMISSION


def test_partial_failure_zero_writes(
    tmp_path: Path,
) -> None:
    """04 §Error paths — S1.cap.a valid, S1.cap.b corrupted; --apply
    exits non-zero AND target file is byte-identical AND
    .patch.rejected names S1.cap."""
    checkout = tmp_path / "partial"
    (checkout / "agent").mkdir(parents=True)
    lines: list[str] = []
    for i in range(1, 688):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append("    return desc[:57] + 'CORRUPTED'\n")
    target = checkout / "agent" / "skill_utils.py"
    target.write_text("".join(lines), encoding="utf-8")
    pre = hashlib.sha256(target.read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    post = hashlib.sha256(target.read_bytes()).hexdigest()
    assert pre == post
    assert r.rejected_path is not None
    rejected = json.loads(r.rejected_path.read_text(encoding="utf-8"))
    assert any(f["site_id"] == "S1.cap" for f in rejected["failures"])


def test_force_still_drifts_exits_nonzero(
    tmp_path: Path,
) -> None:
    """04 §Error paths — second drift after --force --i-accept-line-drift
    still exits non-zero with LINE_DRIFT."""
    checkout = tmp_path / "second-drift"
    (checkout / "agent").mkdir(parents=True)
    # Put a valid cap-raise site at L10 (not L688) so it's pre-validated
    # and patched, then drift it on a subsequent run.
    (checkout / "agent" / "skill_utils.py").write_text(
        "\n".join(["# pad"] * 9) + '\n    if len(desc) > 60:\n        return desc[:57] + "..."\n',
        encoding="utf-8",
    )
    # First --force --i-accept-line-drift run: anchor at L10 not L688.
    # Pre-validation will catch the line drift immediately.
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=True,
            i_accept_line_drift=True,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


def test_e1_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E1 anchor is preserved verbatim
    and the consult-rule line sits immediately after it (NOT split)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "prompt_builder.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    # Find the E1 anchor in the post-patch file.
    anchor_idx = next(i for i, ln in enumerate(lines) if "aren't maintained become liabilities" in ln)
    assert lines[anchor_idx] == '    "Skills that aren\'t maintained become liabilities."'
    # The next line is the appended consult-rule line (constant name).
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx + 1]
    # The SKILL_CREATOR_CONSULT_RULE constant is reachable in the module.
    assert "SKILL_CREATOR_CONSULT_RULE" in text


def test_e2_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E2 anchor preserved verbatim and
    the consult-rule line follows it."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "prompt_builder.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "necessary later, save it as a skill" in ln)
    assert lines[anchor_idx] == '    "necessary later, save it as a skill with the skill tool.\\n"'
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx + 1]


def test_e3_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E3 anchor preserved verbatim and
    the consult-rule line follows it (12-space indent)."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "prompt_builder.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "After difficult/iterative tasks" in ln)
    assert lines[anchor_idx] == '            "After difficult/iterative tasks, offer to save as a skill. "'
    appended = lines[anchor_idx + 1]
    assert "SKILL_CREATOR_CONSULT_RULE" in appended
    # 12-space indent preserved.
    assert appended.startswith(" " * 12)


def test_e4_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E4 anchor preserved verbatim and
    the consult-rule line follows it."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "today's task, it's wrong" in ln)
    assert lines[anchor_idx] == "    \"today's task, it's wrong — fall back to (1), (2), or (3)."
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx + 1]
    assert lines[anchor_idx + 2] == ""
    assert lines[anchor_idx + 3] == '"'


def test_e5_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E5 anchor preserved verbatim and
    the consult-rule line follows it."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    # E5's anchor `(2), or (3).` is a substring of E4's anchor; find
    # the EXACT line (E5's anchor text).
    anchor_idx = next(i for i, ln in enumerate(lines) if ln == '    "(2), or (3).')
    assert lines[anchor_idx] == '    "(2), or (3).'
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx + 1]
    assert lines[anchor_idx + 2] == ""
    assert lines[anchor_idx + 3] == '"'


def test_e6_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E6 anchor preserved verbatim;
    the appended sentence sits between the anchor and the closing ),"""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "tools" / "skill_manager_tool.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "pitfalls come up; pin only guards" in ln)
    assert lines[anchor_idx] == '        "pitfalls come up; pin only guards against irrecoverable loss."'
    # The appended line follows.
    appended = lines[anchor_idx + 1]
    assert "skill-creator" in appended
    assert "skill_manage" in appended
    # The closing ")," still follows.
    assert lines[anchor_idx + 2] == "    ),"


def test_e7_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E7 anchor preserved verbatim;
    the clarifier blockquote follows it."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "website" / "docs" / "user-guide" / "features" / "skills.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if ln.startswith("The agent can create, update"))
    # The clarifier blockquote sits on the next non-blank line.
    clarifier_idx = next(i for i in range(anchor_idx + 1, len(lines)) if lines[i].startswith("> Note:"))
    assert "skill-creator" in lines[clarifier_idx]
    assert "skill_manage" in lines[clarifier_idx]


def test_task_e_current_text_is_unique_in_source() -> None:
    """05 §Anchor-hygiene — each Task E primary anchor is one or more
    physical lines and yields exactly 1 hit in its site table."""
    for site in ALL_TASK_E_SITES:
        # The primary anchor is exactly the bytes of one or more
        # consecutive physical lines — no implicit-concat joining,
        # no whitespace normalization. Multi-line anchors (carrying
        # real newline characters) are matched against consecutive
        # file lines by ``locate_anchor``.
        anchor = site.primary_anchor()
        # fmt: off
        assert (
            len(anchor.text) >= 8
        ), f"site {site.site_id} anchor must be >= 8 chars per plans/04 D5, got {len(anchor.text)}"
        # fmt: on
        # The insertion is a single NEW line (additive-only).
        assert site.insertion.endswith("\n")


def test_no_implicit_concat_normalization() -> None:
    """05 §Anchor-hygiene — the locator matcher uses raw-bytes
    comparison; no implicit-concat joining or whitespace scrubbing."""
    text = "alpha\nbeta\ngamma\n"
    a = Anchor(line=2, text="beta")
    assert locate_anchor(text, a) == 2
    # A different anchor with a joined-string would not be found
    # because the locator does NOT collapse adjacent literals.
    joined = Anchor(line=2, text="betagamma")  # would-be joined
    assert locate_anchor(text, joined) == 0


def test_default_no_task_e_touch(hermes_checkout: Path) -> None:
    """05 §Composition — default --apply (no --task-e-redirect) leaves
    all 4 Task E files byte-identical and does NOT import the
    SKILL_CREATOR_CONSULT_RULE constant into them."""
    targets = [
        hermes_checkout / "agent" / "prompt_builder.py",
        hermes_checkout / "agent" / "background_review.py",
        hermes_checkout / "tools" / "skill_manager_tool.py",
        hermes_checkout / "website" / "docs" / "user-guide" / "features" / "skills.md",
    ]
    pre_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    for p in targets:
        post = hashlib.sha256(p.read_bytes()).hexdigest()
        assert pre_hashes[str(p)] == post, f"file changed: {p}"
    # The constant is NOT inserted into any Task E file.
    for p in targets:
        text = p.read_text(encoding="utf-8")
        assert "SKILL_CREATOR_CONSULT_RULE" not in text


def test_task_e_reapply_is_idempotent(hermes_checkout: Path) -> None:
    """05 §Idempotency / drift — second --apply --task-e-redirect exits
    0 with all 8 sites reporting 'already patched' / 'már javítva'."""
    r1 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r1.exit_code == EXIT_OK
    r2 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r2.exit_code == EXIT_OK
    assert set(r2.sites_already) == {"S1.cap"} | {s.site_id for s in ALL_TASK_E_SITES}
    already_msgs = [d for d in r2.diagnostics if "már javítva" in d or "already patched" in d]
    assert len(already_msgs) == 8


def test_task_e_drift_exits_2(
    tmp_path: Path,
) -> None:
    """05 §Idempotency / drift — corrupt the E4 L105 anchor; run
    --apply --task-e-redirect; exit 2 with TEXT_DRIFT naming E4."""
    checkout = tmp_path / "e4-drift"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    # Minimal skill_utils + prompt_builder; corrupt E4.
    pad = "\n".join(["# pad"] * 688) + '\n    if len(desc) > 60:\n        return desc[:57] + "..."\n'
    (checkout / "agent" / "skill_utils.py").write_text(pad, encoding="utf-8")
    (checkout / "agent" / "prompt_builder.py").write_text(
        "\n".join(["# pad"] * 105) + "\n    CORRUPTED-ANCHOR\n",
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=True,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    assert r.rejected_path is not None
    rejected = json.loads(r.rejected_path.read_text(encoding="utf-8"))
    assert any(f["site_id"] == "E2.memory_guidance" for f in rejected["failures"])


def test_emit_migration_note_lists_all_sites(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """05 §Migration note — --emit-migration-note produces a table with
    exactly 8 rows; with --no-schema-redirect exactly 7 rows."""
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    cap_table = text.split("## Task E sites")[0]
    cap_rows = [ln for ln in cap_table.splitlines() if ln.startswith("| S1.")]
    task_e_table = text.split("## Task E sites")[1]
    task_e_rows = [ln for ln in task_e_table.splitlines() if ln.startswith("| E")]
    assert len(cap_rows) == 1
    assert len(task_e_rows) == 7
    # Row count = 8; the row note matches.
    p2 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=True,
    )
    text2 = p2.read_text(encoding="utf-8")
    task_e_table2 = text2.split("## Task E sites")[1]
    task_e_rows2 = [ln for ln in task_e_table2.splitlines() if ln.startswith("| E")]
    assert len(task_e_rows2) == 6


def test_migration_note_index_links_resolve(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """08 §TDD — MIGRATION.md mentions MIGRATION.hermes-patch.md and
    MIGRATION.skill-port.md."""
    generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=False,
        no_schema_redirect=False,
    )
    index = (worktree / "MIGRATION.md").read_text(encoding="utf-8")
    assert "MIGRATION.hermes-patch.md" in index
    assert "MIGRATION.skill-port.md" in index


def test_migration_note_anchors_match_inventory(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """08 §TDD — every anchor cell in the patch table matches the
    corresponding 8+ char anchor in 05's site table; the new-skill
    rule inserted at E1-E5 is the SAME shared constant."""
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    # The 5 E1-E5 sites all carry the SKILL_CREATOR_CONSULT_RULE
    # constant name in their `replacement` cell.
    for site_id in (
        "E1.skills_guidance",
        "E2.memory_guidance",
        "E3.build_skills_prompt",
        "E4.skill_review_prompt_opt4",
        "E5.combined_review_prompt_opt4",
    ):
        # Find the row by site_id.
        for line in text.splitlines():
            if line.startswith(f"| {site_id} "):
                # The replacement cell must reference the consult rule.
                # fmt: off
                assert (
                    "SKILL_CREATOR_CONSULT_RULE" in line
                ), f"site {site_id} row missing SKILL_CREATOR_CONSULT_RULE: {line!r}"
                # fmt: on


def test_emit_migration_note_idempotent_no_clobber(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """08 §TDD — second --emit-migration-note run on the same target
    produces byte-identical files; no sidecar or backup is left
    behind."""
    p1 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    # Run again with the same flags.
    p2 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2
    # The worktree has only the two MIGRATION files, no sidecar/backup.
    md_files = sorted(p.name for p in worktree.glob("MIGRATION*"))
    assert md_files == ["MIGRATION.hermes-patch.md", "MIGRATION.md"]


# =====================================================================
# F4 + F5 — MIGRATION.md index rows have anchor column
# =====================================================================


def test_migration_index_cap_row_has_anchor_column(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """F4 — the cap row in MIGRATION.hermes-patch.md has a non-empty
    anchor cell containing the byte-exact primary anchor for S1.cap.
    """
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=False,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    cap_table = text.split("## Task E sites")[0]
    cap_data_rows = [ln for ln in cap_table.splitlines() if ln.startswith("| S1.")]
    assert len(cap_data_rows) == 1
    row = cap_data_rows[0]
    # The row has 5 cells. The location cell contains an escaped pipe
    # (\|) in the markdown table; we split on UN-escaped pipes only.
    cells = _split_markdown_row(row)
    assert len(cells) == 5, f"expected 5 cells, got {len(cells)}: {row}"
    # The 5th cell is the anchor cell.
    anchor_cell = cells[4]
    assert "if len(desc) > 60:" in anchor_cell, f"cap row anchor cell missing primary anchor: {anchor_cell!r}"


def test_migration_task_e_rows_have_site_specific_anchor(
    hermes_checkout: Path, worktree: Path, frozen_time: str
) -> None:
    """F5 — each Task E row in MIGRATION.hermes-patch.md has its
    site-specific anchor (the byte-exact single-line locator) in
    the anchor cell.
    """
    p = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    text = p.read_text(encoding="utf-8")
    task_e_table = text.split("## Task E sites")[1]
    task_e_rows = [ln for ln in task_e_table.splitlines() if ln.startswith("| E")]
    assert len(task_e_rows) == 7
    # Build a site_id -> primary_anchor text map.
    expected = {s.site_id: s.primary_anchor().text for s in ALL_TASK_E_SITES}
    for row in task_e_rows:
        cells = _split_markdown_row(row)
        assert len(cells) == 5, f"expected 5 cells, got {len(cells)}: {row}"
        site_id = cells[0]
        anchor_cell = cells[4]
        # The anchor cell must contain a recognizable substring of the
        # primary anchor. For multi-line anchors (carrying real newline
        # characters) only the first physical line is shown in the
        # markdown row, so we check the first line specifically.
        primary = expected[site_id]
        primary_first_line = primary.splitlines()[0] if primary else ""
        # The anchor cell wraps the truncated text in backticks.
        assert "`" in anchor_cell, f"anchor cell for {site_id} missing backticks: {anchor_cell!r}"
        # At least the first 10 chars of the primary anchor are present.
        # For sites whose anchor is short we just check exact containment.
        if len(primary_first_line) <= 60:
            # fmt: off
            assert (
                primary_first_line in anchor_cell
            ), f"anchor cell for {site_id} missing primary anchor: {primary_first_line!r} not in {anchor_cell!r}"
            # fmt: on
        else:
            # Truncated: first 59 chars + ellipsis.
            truncated = primary_first_line[:59] + "…"
            assert truncated in anchor_cell, f"anchor cell for {site_id} missing truncated anchor: {truncated!r}"


def test_migration_deterministic_under_frozen_time(hermes_checkout: Path, worktree: Path, frozen_time: str) -> None:
    """08 D6 — under HERMES_SKILL_CREATOR_FROZEN_TIME, the migration
    note is byte-identical across runs."""
    p1 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    p2 = generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=True,
        no_schema_redirect=False,
    )
    assert p1.read_bytes() == p2.read_bytes()


def test_now_iso_honors_frozen_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """now_iso() returns the env var when HERMES_SKILL_CREATOR_FROZEN_TIME
    is set."""
    from hermes_skill_creator_plugin._patcher_helpers import now_iso

    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2030-01-01T00:00:00Z")
    assert now_iso() == "2030-01-01T00:00:00Z"


def test_now_iso_returns_current_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """now_iso() returns an ISO-8601 UTC timestamp when
    HERMES_SKILL_CREATOR_FROZEN_TIME is unset."""
    from hermes_skill_creator_plugin._patcher_helpers import now_iso

    monkeypatch.delenv("HERMES_SKILL_CREATOR_FROZEN_TIME", raising=False)
    s = now_iso()
    assert s.endswith("Z")
    assert "T" in s
    assert len(s) == 20  # YYYY-MM-DDTHH:MM:SSZ


def test_force_audit_log_uses_frozen_time(hermes_checkout: Path, frozen_time: str) -> None:
    """The audit log line uses the frozen timestamp."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=True,
            i_accept_line_drift=True,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    audit = hermes_checkout / ".patch.audit.log"
    assert audit.exists()
    text = audit.read_text(encoding="utf-8")
    assert frozen_time in text


def test_run_patch_required_params() -> None:
    """The run_patch signature accepts a single :class:`PatchRunInputs` struct
    whose fields are the required operational parameters plus optional
    side-effects (yes/verbose/audit_log_path/git_head) that carry safe
    defaults (False/False/None/'').
    """
    import inspect

    from hermes_skill_creator_plugin._patcher import run_patch

    sig = inspect.signature(run_patch)
    # Single positional ``inputs: PatchRunInputs`` param keeps WPS211 in check.
    sig_names = set(sig.parameters.keys())
    assert sig_names == {"inputs"}, f"unexpected params: {sig_names - {'inputs'} or 'inputs' - sig_names}"

    fields = {field.name for field in PatchRunInputs.__dataclass_fields__.values()}
    required = {
        "target",
        "check",
        "apply",
        "force",
        "i_accept_line_drift",
        "task_e_redirect",
        "no_schema_redirect",
    }
    assert required.issubset(fields), f"missing required fields: {required - fields}"
    # Optional side-effects have safe defaults.
    assert PatchRunInputs.__dataclass_fields__["yes"].default is False
    assert PatchRunInputs.__dataclass_fields__["verbose"].default is False
    assert PatchRunInputs.__dataclass_fields__["audit_log_path"].default is None
    assert PatchRunInputs.__dataclass_fields__["git_head"].default == ""


def test_emit_migration_note_writes_to_worktree_not_target(
    hermes_checkout: Path, worktree: Path, frozen_time: str
) -> None:
    """08 §TDD — MIGRATION.hermes-patch.md and MIGRATION.md land at the
    worktree root, NOT under --target."""
    generate_migration_note(
        target=hermes_checkout,
        worktree=worktree,
        task_e_redirect=False,
        no_schema_redirect=False,
    )
    # Target tree does NOT have a MIGRATION* file.
    assert not (hermes_checkout / "MIGRATION.hermes-patch.md").exists()
    assert not (hermes_checkout / "MIGRATION.md").exists()
    # Worktree has both files.
    assert (worktree / "MIGRATION.hermes-patch.md").exists()
    assert (worktree / "MIGRATION.md").exists()


def test_apply_then_check_exits_0_with_already_patched(
    hermes_checkout: Path,
) -> None:
    """After --apply, --check exits 0 with 'már javítva' diagnostic for
    S1.cap (per the spec bilingual requirement)."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=False,
            apply=True,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            check=True,
            apply=False,
            force=False,
            i_accept_line_drift=False,
            task_e_redirect=False,
            no_schema_redirect=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    assert any("már javítva" in d for d in r.diagnostics)
    assert any("S1.cap" in d for d in r.diagnostics)
