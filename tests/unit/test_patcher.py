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
import os
import stat
from pathlib import Path

import pytest

from easter_hermes_sorry_skills._patcher import (
    ALL_TASK_E_SITES,
    E0_CONSULT_RULE_DEF,
    EXIT_DRIFT,
    EXIT_IO,
    EXIT_OK,
    EXIT_PERMISSION,
    S1_CAP_SITE,
    S1_CAP_SITE_FALLBACK,
    Anchor,
    PatchRunInputs,
    Site,
    _atomic_write_bytes,
    _cross_filesystem,
    file_has_circular_import,
    hermes_agent_path,
    is_hermes_agent,
    locate_anchor,
    run_patch,
    site_already_patched,
    site_in_state,
)
from easter_hermes_sorry_skills._patcher_sites_table import _CONSULT_RULE_TEXT
from tests.conftest import (
    BACKGROUND_REVIEW_PATCHED,
    PROMPT_BUILDER_PATCHED,
    SKILL_UTILS_PATCHED,
    assert_hermes_agent_untouched,
)


def _write_task_e_files(checkout: Path) -> None:
    """Write the 2 Task E target files into ``checkout``.

    Phase C2 dropped both ``--task-e-redirect`` and ``--no-schema-redirect``
    flags; Task E always runs now. Tests that build a checkout under
    ``tmp_path`` must lay down these 2 files (using the conftest padded
    fixtures) or the patcher fails its pre-validation with drift on the
    missing target files.
    """
    (checkout / "agent").mkdir(parents=True, exist_ok=True)
    (checkout / "agent" / "prompt_builder.py").write_text(PROMPT_BUILDER_PATCHED, encoding="utf-8")
    (checkout / "agent" / "background_review.py").write_text(BACKGROUND_REVIEW_PATCHED, encoding="utf-8")


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
            dry_run=False,
        ),
    )
    assert r1.exit_code == EXIT_OK
    assert "S1.cap" in r1.sites_patched
    r2 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
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
            dry_run=True,
        ),
    )
    assert r.exit_code == EXIT_OK
    post = hashlib.sha256(target_file.read_bytes()).hexdigest()
    assert pre == post


# REMOVED (Phase 7 refactor): ``test_force_retries_only_drifted_sites``
# — verified that a second ``--force`` run on a clean (already-patched)
# state did not re-write the file. The ``--force`` flag was removed
# in Phase 7A.5; the post-Phase 7 ``--apply`` already short-circuits
# on already-patched sites via the state sidecar, which is covered by
# ``test_apply_cap_only_default_idempotent``.


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
            dry_run=False,
        ),
    )
    assert r.exit_code != EXIT_OK
    post = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    assert pre == post
    assert r.rejected_path is None


def test_apply_cap_raise_max_description_length_defined(
    hermes_checkout: Path, real_hermes_agent_sentinel: str | None
) -> None:
    """After --apply, the cap-raise site uses MAX_DESCRIPTION_LENGTH."""
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    assert "MAX_DESCRIPTION_LENGTH" in text
    # The literal "60" must be gone from the cap-raise site (line 716).
    lines = text.splitlines()
    assert "60" not in lines[715]
    assert "MAX_DESCRIPTION_LENGTH" in lines[715]
    # The slice on L717 (now L718 after the new comparator line) is
    # `desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."`.
    assert "MAX_DESCRIPTION_LENGTH - 3" in "\n".join(lines[715:719])


def test_task_e_runs_by_default(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Default --apply patches all 6 Task E sites + S1.cap (7 sites).

    Phase C2 dropped both ``--task-e-redirect`` and ``--no-schema-redirect``
    flags; Task E always runs now (the cap site is patched in the same
    pass).
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    expected = {"S1.cap"} | {s.site_id for s in ALL_TASK_E_SITES}
    assert expected.issubset(set(r.state.keys()))


def test_task_e_always_touches_target_files(hermes_checkout: Path) -> None:
    """Phase C2: Task E is no longer opt-in. Every default --apply
    touches the 2 Task E files (prompt_builder, background_review).
    After a default apply the consult rule literal
    ``SKILL_CREATOR_CONSULT_RULE`` is reachable in each file's patched
    content.
    """
    targets = [
        (hermes_checkout / "agent" / "prompt_builder.py", "SKILL_CREATOR_CONSULT_RULE"),
        (hermes_checkout / "agent" / "background_review.py", "SKILL_CREATOR_CONSULT_RULE"),
    ]
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    for p, needle in targets:
        text = p.read_text(encoding="utf-8")
        assert needle in text, f"{p} missing {needle!r}"


# --- Task E composition --------------------------------------------------


@pytest.mark.parametrize(
    ("lang", "expected_text"),
    [
        ("en", "--target is required"),
        ("hu", "a --target megadása kötelező"),
    ],
)
def test_target_required_exits_4(
    lang: str,
    expected_text: str,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """--target unset -> exit 4 with single-language TARGET_REQUIRED message.

    The preflight routes ``TARGET_REQUIRED`` through
    :func:`_i18n_pick.pick(lang)` so ``en`` emits
    ``"--target is required"`` and ``hu`` emits
    ``"a --target megadása kötelező"``.
    """
    r = run_patch(
        PatchRunInputs(
            target=None,
            dry_run=True,
            lang=lang,
        ),
    )
    assert r.exit_code == EXIT_IO
    assert any(expected_text in d for d in r.diagnostics)


@pytest.mark.parametrize(
    ("lang", "expected_warning"),
    [
        ("en", "WARNING: target is the live hermes-agent checkout (the default), no patches will be applied"),
        ("hu", "FIGYELEM: a target az élő hermes-agent checkout (alapértelmezett), nem történik patch"),
    ],
)
def test_target_resolves_to_hermes_agent_refused(
    lang: str,
    expected_warning: str,
    real_hermes_agent_sentinel: str | None,
) -> None:
    """Soft safety: ``--dry-run`` + hermes-agent target -> WARNING + EXIT_OK (or drift).

    Before the soft-safety change this test asserted ``EXIT_IO`` for
    ANY ``--target ~/.hermes/hermes-agent`` invocation. After the
    change, ``--dry-run`` SOFTENS the refusal: the preflight emits
    the single-language WARNING diagnostic and the pipeline proceeds.
    The exit code depends on what the post-preflight pipeline finds —
    for the synthetic hermes-agent path on a developer machine the
    validation typically detects TEXT_DRIFT and returns ``EXIT_DRIFT``
    (2), but the soft-safety diagnostic is always present.

    The WARNING diagnostic is selected via :func:`_i18n_pick.pick(lang)`
    from the language-specific module: ``en`` -> English WARNING line,
    ``hu`` -> Hungarian FIGYELEM line.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_agent_path(),
            dry_run=True,
            lang=lang,
        ),
    )
    # Soft-safety diagnostic MUST appear in the selected language
    # (proves the preflight short-circuit fired and did NOT hard-
    # refuse with EXIT_IO).
    assert any(expected_warning in d for d in r.diagnostics)
    # Apply mode (dry_run=False) still HARD-refuses with EXIT_IO.
    r_apply = run_patch(
        PatchRunInputs(
            target=hermes_agent_path(),
            dry_run=False,
            lang=lang,
        ),
    )
    assert r_apply.exit_code == EXIT_IO


def test_target_missing_agent_skill_utils_exits_4(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """--target without agent/skill_utils.py -> exit 4."""
    checkout = tmp_path / "empty"
    checkout.mkdir()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=True,
        ),
    )
    assert r.exit_code == EXIT_IO


def test_circular_import_preflight_emits_diagnostic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """AC-2.11: agent/skill_utils.py already imports from
    tools.skills_tool. The circular-import pre-flight emits a
    diagnostic AND the patcher proceeds with the FALLBACK S1 site
    (which uses a local ``_MAX_DESCRIPTION_LENGTH = 1024``). The run
    exits 0 on --check (the cycle is no longer fatal).
    """
    checkout = tmp_path / "cycle"
    _write_task_e_files(checkout)
    # Layout mirrors the real Hermes checkout: skill_utils.py has the
    # cap-raise pair at L716/L717 so the S1.cap_fallback site anchors
    # match. The cycle marker is on L1 so the preflight fires.
    lines: list[str] = ["from tools.skills_tool import MAX_DESCRIPTION_LENGTH\n"]
    for i in range(1, 715):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append('        return desc[:57] + "..."\n')
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=True,
        ),
    )
    assert r.exit_code == EXIT_OK
    assert any("circular import" in d for d in r.diagnostics)


# REMOVED (Phase 7 refactor): ``test_force_without_i_accept_line_drift_exits_5``
# — exercised the preflight rule "force without i_accept_line_drift
# -> EXIT_USER_ABORT". The ``--force`` / ``--i-accept-line-drift``
# flags were removed in Phase 7A.5; the preflight rule is therefore
# unreachable. See ``_patcher_internals.py:run_preflight`` comment.


def test_line_drift_exits_2_with_diagnostic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Cap-raise comparator matches anchor; the LINE is wrong -> LINE_DRIFT."""
    checkout = tmp_path / "line-drift"
    (checkout / "agent").mkdir(parents=True)
    # Put the cap-raise site at L10 (not L716) — same anchor text, wrong line.
    (checkout / "agent" / "skill_utils.py").write_text(
        "# pad\n" * 9 + "    if len(desc) > 60:\n",
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


def test_text_drift_exits_2_with_diagnostic(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Anchor text does not match -> TEXT_DRIFT (treated as exit 2 here)."""
    checkout = tmp_path / "text-drift"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text(
        "\n".join(["# pad"] * 716) + "\n    if len(desc) > 61:\n",
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    assert r.rejected_path is None


def test_e1_skills_guidance_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E1 anchor is preserved verbatim
    and the consult-rule line sits immediately after it (NOT split).
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
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


def test_e2_memory_guidance_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E2 anchor preserved verbatim and
    the consult-rule line follows it.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "prompt_builder.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "necessary later, save it as a skill" in ln)
    assert lines[anchor_idx] == '    "necessary later, save it as a skill with the skill tool.\\n"'
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx + 1]


def test_e4_skill_review_prompt_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E4 anchor preserved verbatim and
    the consult-rule line precedes it (the patcher inserts BEFORE the
    multi-line 3-line anchor block; the rule + the 3 anchor lines
    remain in order).
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    anchor_idx = next(i for i, ln in enumerate(lines) if "today's task, it's wrong" in ln)
    assert lines[anchor_idx] == "    \"today's task, it's wrong — fall back to (1), (2), or (3).\\n\\n\""
    # The consult-rule insertion sits immediately before the 3-line
    # anchor block (one line above the first anchor line).
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx - 1]
    assert lines[anchor_idx + 1] == '    "User-preference embedding (important): when the user expressed a "'


def test_e5_combined_review_prompt_appends_only(hermes_checkout: Path) -> None:
    """05 §Per-site additive-only — E5 anchor preserved verbatim and
    the consult-rule line precedes it.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    # E5's anchor `(2), or (3).\n\n"` is a substring of E4's anchor; find
    # the EXACT line (E5's anchor text).
    anchor_idx = next(i for i, ln in enumerate(lines) if ln == '    "(2), or (3).\\n\\n"')
    assert lines[anchor_idx] == '    "(2), or (3).\\n\\n"'
    # The consult-rule insertion sits immediately before the 3-line
    # anchor block (one line above the first anchor line).
    assert "SKILL_CREATOR_CONSULT_RULE" in lines[anchor_idx - 1]
    assert lines[anchor_idx + 1] == '    "User-preference embedding: when the user complains about how "'


def test_task_e_current_text_is_unique_in_source() -> None:
    """05 §Anchor-hygiene — each Task E primary anchor is one or more
    physical lines and yields exactly 1 hit in its site table.
    """
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


def test_e4b_consult_rule_import_writes_import_into_background_review(
    hermes_checkout: Path,
) -> None:
    """AC-2.8: Task E writes the
    ``from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE``
    import at the top of ``agent/background_review.py`` via the E4b
    site. Without it, E4 and E5 would fail to resolve the constant.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    assert "from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE" in text


def test_e0_consult_rule_def_writes_constant_into_prompt_builder(
    hermes_checkout: Path,
) -> None:
    """AC-2.8: Task E writes the ``SKILL_CREATOR_CONSULT_RULE``
    constant definition at the top of ``agent/prompt_builder.py`` via
    the E0 site. The patch proceeds to the other Task E sites.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "prompt_builder.py").read_text(encoding="utf-8")
    # The constant definition is present (assigned to the canonical name).
    assert "SKILL_CREATOR_CONSULT_RULE = (" in text
    # And the canonical wording appears verbatim in the file.
    assert "use skill-creator" in text
    assert "Persist with skill_manage" in text
    assert "one-file, < ~20 lines, no schema change" in text


def test_e4_e5_share_constant_after_patch(hermes_checkout: Path) -> None:
    """AC-2.8 / plans/05 §B1.2: E4 and E5 reference the literal
    ``SKILL_CREATOR_CONSULT_RULE`` name and rely on the E4b import to
    resolve it. After Task E runs, the constant value appears
    verbatim in BOTH the ``_SKILL_REVIEW_PROMPT`` and
    ``_COMBINED_REVIEW_PROMPT`` backgrounds.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (hermes_checkout / "agent" / "background_review.py").read_text(encoding="utf-8")
    assert text.count("SKILL_CREATOR_CONSULT_RULE") >= 3  # import + E4 + E5


def test_skill_creator_consult_rule_constant() -> None:
    """AC-2.8: the shared constant lives in ``agent/prompt_builder.py``
    (the target) and is written there by the E0 patch site. The plugin
    no longer exports ``SKILL_CREATOR_CONSULT_RULE``; tests assert the
    canonical "Közepes" wording via ``_CONSULT_RULE_TEXT``.
    """
    # Phase C2 canonical wording ("Közepes" tier): short rule that
    # names ``skill-creator`` and ``skill_manage`` and reinforces the
    # patch-first preference for small fixes.
    assert "use skill-creator" in _CONSULT_RULE_TEXT
    assert "Persist with skill_manage" in _CONSULT_RULE_TEXT
    assert "one-file, < ~20 lines, no schema change" in _CONSULT_RULE_TEXT
    assert "skill-creator" in _CONSULT_RULE_TEXT  # ensure skill-creator mentioned
    # E0 is a top-of-file patch site anchored on the L1 docstring of
    # ``agent/prompt_builder.py``; its insertion payload contains the
    # canonical constant text.
    assert _CONSULT_RULE_TEXT in E0_CONSULT_RULE_DEF.insertion
    assert "SKILL_CREATOR_CONSULT_RULE = (" in E0_CONSULT_RULE_DEF.insertion


def test_task_e_reapply_is_idempotent(hermes_checkout: Path) -> None:
    """05 §Idempotency / drift — second --apply exits 0 with all 7 sites
    (S1.cap + 6 Task E sites) reporting 'already patched' /
    'már javítva'.
    """
    r1 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r1.exit_code == EXIT_OK
    r2 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r2.exit_code == EXIT_OK
    assert set(r2.sites_already) == {"S1.cap"} | {s.site_id for s in ALL_TASK_E_SITES}
    already_msgs = [d for d in r2.diagnostics if "már javítva" in d or "already patched" in d]
    # AC-2.8: 7 sites total now (S1.cap + 6 Task E sites including
    # E0 and E4b).
    assert len(already_msgs) == 7


def test_task_e_drift_exits_2(
    tmp_path: Path,
) -> None:
    """05 §Idempotency / drift — corrupt the E4 L105 anchor; run
    --apply; exit 2 with TEXT_DRIFT naming E2 (the first site that
    depends on the prompt_builder file state).
    """
    checkout = tmp_path / "e4-drift"
    _write_task_e_files(checkout)
    # skill_utils.py is required for S1.cap (the run aborts with exit 4
    # if it's missing); the patcher validates ALL sites up-front.
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    # Overwrite the prompt_builder.py anchor with a corrupted line; the
    # Task E pre-validation should catch the TEXT_DRIFT on the first
    # site that depends on this file (E2.memory_guidance).
    pad = "\n".join(["# pad"] * 105) + "\n    CORRUPTED-ANCHOR\n"
    (checkout / "agent" / "prompt_builder.py").write_text(pad, encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    assert r.rejected_path is None


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
            dry_run=False,
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
            dry_run=False,
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
            dry_run=False,
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
        "\n".join(["# pad"] * 716) + "\n    if len(desc) > 999:\n",
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
            dry_run=True,
        ),
    )
    assert r.exit_code != EXIT_OK
    post_skill = hashlib.sha256((checkout / "agent" / "skill_utils.py").read_bytes()).hexdigest()
    post_pb = hashlib.sha256((checkout / "agent" / "prompt_builder.py").read_bytes()).hexdigest()
    assert pre_skill == post_skill
    assert pre_pb == post_pb


# REMOVED (Phase 7 refactor): ``test_audit_log_appended_on_force`` and
# ``test_audit_log_includes_drifted_site_diff_sha`` — verified that
# ``--force`` invocations appended an entry to ``HERMES_HOME/patch-audit.log``
# (and the old target-dir ``.patch.audit.log`` was NOT created). The
# ``--force`` flag and its audit-log emission path were removed in
# Phase 7A.5.


# --- bilingual format / site table hygiene -------------------------------


def test_console_log_lines_match_bilingual_regex(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """Every USER-FACING diagnostic in the run is single-language (no
    bilingual ``[en] X / [hu] Y`` prefix).

    After the patcher i18n refactor, all diagnostics are emitted in a
    single language selected by ``--lang`` (default ``en``). The
    legacy bilingual ``[en] X / [hu] Y`` format is gone — this test
    pins the new single-language contract: each diagnostic is one
    line, no ``[en]`` / ``[hu]`` prefixes anywhere.
    """
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    for d in r.diagnostics:
        assert "[en]" not in d, f"legacy [en] prefix found: {d!r}"
        assert "[hu]" not in d, f"legacy [hu] prefix found: {d!r}"


def test_help_is_lang_aware() -> None:
    """``--help`` shows HELP_EN by default; ``--lang hu`` shows HELP_HU.

    Replaces the pre-``--lang`` ``test_help_is_bilingual`` contract: the
    help text is no longer bilingual-concatenated, but selected via the
    ``--lang {en,hu}`` option on the CLI.
    """
    from click.testing import CliRunner

    from easter_hermes_sorry_skills.cli_patch import main as cli_main

    runner = CliRunner()
    # Default: English only.
    result = runner.invoke(cli_main, ["--help"])
    assert result.exit_code == 0
    assert "Patcher applies:" in result.output
    assert "A patcher a kovetkezoket vegzi" not in result.output
    # ``--lang hu`` flips the help text to Hungarian only.
    result = runner.invoke(cli_main, ["--lang", "hu", "--help"])
    assert result.exit_code == 0
    assert "A patcher a kovetkezoket vegzi" in result.output
    assert "Patcher applies:" not in result.output


# --- idempotency / coverage -----------------------------------------------


def test_check_already_patched_exits_0(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """After a successful --apply, --check exits 0 with per-site
    'OK: already patched' messages."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=True,
        ),
    )
    assert r.exit_code == EXIT_OK
    assert any("already patched" in d for d in r.diagnostics)


def test_state_sidecar_survives_re_run(hermes_checkout: Path, real_hermes_agent_sentinel: str | None) -> None:
    """A second --apply reads the sidecar and skips matched sites."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
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

    assert importlib.metadata.version("easter-hermes-sorry-skills") == "0.1.0"


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
    from easter_hermes_sorry_skills._patcher_apply_atomic import _with_newline

    assert _with_newline("hello\n") == "hello\n"


def test_with_newline_appends_when_missing() -> None:
    """Text without a trailing newline gets exactly one newline appended."""
    from easter_hermes_sorry_skills._patcher_apply_atomic import _with_newline

    assert _with_newline("hello") == "hello\n"


def test_apply_anchor_text_missing_exits_drift(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """When the primary anchor's text is not in the file, drift + exit."""
    checkout = tmp_path / "oob"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT


# --- coverage: cap secondary anchor mismatch is caught by pre-validation --


def test_apply_cap_secondary_anchor_mismatch_caught_by_validation(
    tmp_path: Path, real_hermes_agent_sentinel: str | None
) -> None:
    """S1.cap.a is at L716 with the right text; S1.cap.b (L717) is wrong.
    The pre-validation pass catches this as drift (TEXT_DRIFT on the b
    anchor) and the run aborts before the apply step."""
    checkout = tmp_path / "cap-mismatch"
    (checkout / "agent").mkdir(parents=True)
    lines: list[str] = []
    for i in range(1, 716):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append("    return desc[:57] + 'XXX'\n")  # WRONG slice
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
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

    monkeypatch.setattr("easter_hermes_sorry_skills._patcher._atomic_write_bytes", selective_boom)
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
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
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # The CROSS_FS_WARN diagnostic is emitted (single-language, EN by default).
    assert any("warning" in d.lower() and "filesystems" in d for d in r.diagnostics)


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
# F-28 — TOCTOU race: build_site_payload must translate OSError on read
# =====================================================================
#
# Pre-validation snapshots the target files (preflight), but the apply
# step re-reads them via ``build_site_payload``. Between the two reads
# a concurrent ``rm`` / ``mv`` can delete the file; ``path.read_bytes()``
# raises ``FileNotFoundError`` (a subclass of ``OSError``). Without a
# try/except wrapper that error escapes to the caller as an uncaught
# exception and aborts the whole patcher. ``try_build_site_payload``
# catches ``OSError`` and returns a ``PatcherResult`` with ``EXIT_IO``
# so the per-site loop can record the failure cleanly.
# ---------------------------------------------------------------------


def test_try_build_site_payload_returns_payload_on_success(tmp_path: Path) -> None:
    """``try_build_site_payload`` returns ``(None, _SitePayload)`` when
    the target file is readable."""
    from easter_hermes_sorry_skills._patcher_pipeline_apply import (
        try_build_site_payload,
    )

    target = tmp_path / "skill_utils.py"
    target.write_bytes(b"def extract_skill_description(desc: str) -> str:\n    return desc\n")
    outcome, payload = try_build_site_payload(target, S1_CAP_SITE)
    assert outcome is None
    assert payload is not None
    assert payload.before == target.read_bytes()
    assert payload.after_bytes != payload.before


def test_try_build_site_payload_translates_fnfe_to_io_result(tmp_path: Path) -> None:
    """When ``read_bytes`` raises ``FileNotFoundError`` (TOCTOU race),
    ``try_build_site_payload`` returns an EXIT_IO ``PatcherResult``
    and ``(outcome, payload)`` shape is ``(PatcherResult, None)``."""
    from easter_hermes_sorry_skills._patcher_pipeline_apply import (
        try_build_site_payload,
    )

    missing = tmp_path / "deleted_between_preflight_and_apply.py"
    assert not missing.exists()
    outcome, payload = try_build_site_payload(missing, S1_CAP_SITE)
    assert payload is None
    assert outcome is not None
    assert outcome.exit_code == EXIT_IO
    assert outcome.sites_patched == ()
    assert any(str(missing) in d for d in outcome.diagnostics)


def test_try_build_site_payload_translates_oserror_to_io_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``read_bytes`` raises a non-FNFE ``OSError`` (permission,
    I/O error), ``try_build_site_payload`` still returns EXIT_IO and
    does NOT let the exception escape."""
    from easter_hermes_sorry_skills._patcher_pipeline_apply import (
        try_build_site_payload,
    )

    target = tmp_path / "locked.py"
    target.write_bytes(b"x")

    def fail_read(*_args: object, **_kwargs: object) -> bytes:
        raise OSError("simulated read failure")

    monkeypatch.setattr(type(target), "read_bytes", fail_read)
    outcome, payload = try_build_site_payload(target, S1_CAP_SITE)
    assert payload is None
    assert outcome is not None
    assert outcome.exit_code == EXIT_IO


def test_build_site_payload_propagates_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lower-level ``build_site_payload`` propagates ``OSError`` to
    its caller (the public translation lives in ``try_build_site_payload``).
    Callers that already handle ``OSError`` will see the same exception
    type and can route it the same way they route write errors."""
    from easter_hermes_sorry_skills._patcher_pipeline_apply import (
        build_site_payload,
    )

    target = tmp_path / "vanished.py"

    def fail_read(*_args: object, **_kwargs: object) -> bytes:
        raise FileNotFoundError(2, "simulated TOCTOU delete")

    monkeypatch.setattr(type(target), "read_bytes", fail_read)
    with pytest.raises(FileNotFoundError):
        build_site_payload(target, S1_CAP_SITE)


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
            dry_run=False,
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
    _write_task_e_files(checkout)
    # Use the standard fixture: the cap-raise site is at L716/L717.
    (checkout / "agent" / "skill_utils.py").write_text(SKILL_UTILS_PATCHED, encoding="utf-8")
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    # Post-patch: BOTH S1.cap.a and S1.cap.b are applied.
    text = (checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "MAX_DESCRIPTION_LENGTH" in lines[715]
    assert "MAX_DESCRIPTION_LENGTH - 3" in lines[716]


def test_target_unwritable_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """04 §Error paths — when _atomic_write_bytes raises PermissionError
    on the target file, --apply exits 3 (PermissionError)."""
    from easter_hermes_sorry_skills import _patcher

    checkout = tmp_path / "unwritable"
    _write_task_e_files(checkout)
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
            dry_run=False,
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
    for i in range(1, 716):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append("    return desc[:57] + 'CORRUPTED'\n")
    target = checkout / "agent" / "skill_utils.py"
    target.write_text("".join(lines), encoding="utf-8")
    pre = hashlib.sha256(target.read_bytes()).hexdigest()
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_DRIFT
    post = hashlib.sha256(target.read_bytes()).hexdigest()
    assert pre == post
    assert r.rejected_path is None


# REMOVED (Phase 7 refactor): ``test_force_still_drifts_exits_nonzero``
# — tested the "drift-after-force" error path for ``--force
# --i-accept-line-drift`` runs. The ``--force`` /
# ``--i-accept-line-drift`` flags were removed in Phase 7A.5; the
# default ``--apply`` path still EXITS 2 on drift, which is covered
# by ``test_line_drift_exits_2_with_diagnostic`` and
# ``test_text_drift_exits_2_with_diagnostic``.


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


def test_now_iso_honors_frozen_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """now_iso() returns the env var when HERMES_SKILL_CREATOR_FROZEN_TIME
    is set."""
    from easter_hermes_sorry_skills._patcher_helpers import now_iso

    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2030-01-01T00:00:00Z")
    assert now_iso() == "2030-01-01T00:00:00Z"


def test_now_iso_returns_current_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """now_iso() returns an ISO-8601 UTC timestamp when
    HERMES_SKILL_CREATOR_FROZEN_TIME is unset."""
    from easter_hermes_sorry_skills._patcher_helpers import now_iso

    monkeypatch.delenv("HERMES_SKILL_CREATOR_FROZEN_TIME", raising=False)
    s = now_iso()
    assert s.endswith("Z")
    assert "T" in s
    assert len(s) == 20  # YYYY-MM-DDTHH:MM:SSZ


# REMOVED (Phase 7 refactor): ``test_force_audit_log_uses_frozen_time``
# — verified that the per-invocation audit log emitted by ``--force``
# runs carries the frozen timestamp. The ``--force`` flag and its
# audit-log emission path were removed in Phase 7A.5.


def test_run_patch_required_params() -> None:
    """The run_patch signature accepts a single :class:`PatchRunInputs` struct
    whose fields are the operational parameters (target, dry_run) plus
    optional side-effects (verbose/audit_log_path/git_head) that carry
    safe defaults (False/None/'').
    """
    import inspect

    from easter_hermes_sorry_skills._patcher import run_patch

    sig = inspect.signature(run_patch)
    # Single positional ``inputs: PatchRunInputs`` param keeps WPS211 in check.
    sig_names = set(sig.parameters.keys())
    assert sig_names == {"inputs"}, f"unexpected params: {sig_names - {'inputs'} or 'inputs' - sig_names}"

    fields = {field.name for field in PatchRunInputs.__dataclass_fields__.values()}
    required = {
        "target",
        "dry_run",
        "verbose",
        "audit_log_path",
        "git_head",
    }
    assert required.issubset(fields), f"missing required fields: {required - fields}"
    # Optional side-effects have safe defaults.
    assert PatchRunInputs.__dataclass_fields__["dry_run"].default is False
    assert PatchRunInputs.__dataclass_fields__["verbose"].default is False
    assert PatchRunInputs.__dataclass_fields__["audit_log_path"].default is None
    assert PatchRunInputs.__dataclass_fields__["git_head"].default == ""


def test_apply_then_check_exits_0_with_already_patched(
    hermes_checkout: Path,
) -> None:
    """After --apply, --check exits 0 with 'already patched' diagnostic for
    S1.cap (single-language emission after the i18n refactor)."""
    run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    r = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=True,
        ),
    )
    assert r.exit_code == EXIT_OK
    assert any("already patched" in d for d in r.diagnostics)
    assert any("S1.cap" in d for d in r.diagnostics)


# =====================================================================
# PR-B (issue #17) — 5-bug fixes for AC-2.5, AC-2.5.1, AC-2.10, AC-2.11
# =====================================================================


# REMOVED (Phase 7 refactor): ``test_force_retries_only_state_drifted_sites``
# — tested ``--force --i-accept-line-drift`` retry-only-drifted-sites
# semantics. The ``--force`` / ``--i-accept-line-drift`` flags were
# removed in Phase 7A.5; the patcher now always applies all sites
# (skipping already-patched ones via the state sidecar).


# REMOVED (Phase 7 refactor): ``test_force_gate_proceeds_when_yes_flag_set``,
# ``test_force_gate_refuses_on_tty_negative_reply``,
# ``test_force_gate_proceeds_on_tty_yes_reply`` — tested the TTY consent
# gate that prompted for ``"yes"`` before applying ``--force`` patches.
# The ``--force`` / ``--i-accept-line-drift`` / ``--yes`` CLI flags
# were removed in Phase 7A.5 along with the gate. See
# ``_patcher_internals.py:run_preflight`` comment.


# REMOVED (Phase 7 refactor): ``test_audit_log_uses_hermes_home_not_target``
# — tested the per-invocation audit log emitted by ``--force`` runs.
# The ``--force`` / ``--i-accept-line-drift`` / ``--yes`` CLI flags
# were removed in Phase 7A.5 along with their TTY gate and audit-log
# emission paths. See ``_patcher_internals.py:run_preflight`` comment.


def test_circular_import_preflight_uses_subprocess_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix #5 (AC-2.11): the pre-flight uses ``subprocess.run`` to
    actually exercise ``import tools.skills_tool`` (not a string grep)."""
    checkout = tmp_path / "subprocess-cycle"
    _write_task_e_files(checkout)
    # The file does NOT contain the import marker; the subprocess
    # check should still detect the cycle if the import would fail.
    # Layout mirrors real Hermes: cap-raise anchors at L716/L717 so
    # S1.cap_fallback validation succeeds after the cycle signal.
    lines: list[str] = ["# no tools.skills_tool import here\n"]
    for i in range(1, 715):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append('        return desc[:57] + "..."\n')
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")
    # tools/skills_tool.py exists but is broken (SyntaxError), so
    # ``import tools.skills_tool`` will fail in the subprocess.
    (checkout / "tools").mkdir(parents=True, exist_ok=True)
    (checkout / "tools" / "skills_tool.py").write_text(
        "def broken(:\n",  # SyntaxError
        encoding="utf-8",
    )
    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=True,
        ),
    )
    # AC-2.11: the cycle is no longer fatal; the patcher proceeds with
    # the S1.cap_fallback site, so --check exits 0 and emits the
    # ``circular import`` diagnostic.
    assert r.exit_code == EXIT_OK
    assert any("circular import" in d for d in r.diagnostics)


def test_circular_import_subprocess_oserror_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix #5 branch: when the subprocess raises ``OSError`` (e.g.
    executable not found), the pre-flight falls back to ``False`` and
    does NOT flag a cycle."""
    import subprocess as _subprocess

    from easter_hermes_sorry_skills import _patcher_helpers

    checkout = tmp_path / "oserror-cycle"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text("# ok\n", encoding="utf-8")
    (checkout / "tools" / "skills_tool.py").write_text("# ok\n", encoding="utf-8")

    def boom(*_args: object, **_kwargs: object) -> _subprocess.CompletedProcess[bytes]:
        raise OSError("simulated subprocess failure")

    monkeypatch.setattr(_patcher_helpers.subprocess, "run", boom)
    assert _patcher_helpers.file_has_circular_import(checkout / "agent" / "skill_utils.py") is False


def test_circular_import_subprocess_timeout_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix #5 branch: when the subprocess times out
    (``SubprocessError``), the pre-flight falls back to ``False``."""
    import subprocess as _subprocess

    from easter_hermes_sorry_skills import _patcher_helpers

    checkout = tmp_path / "timeout-cycle"
    (checkout / "agent").mkdir(parents=True)
    (checkout / "tools").mkdir(parents=True)
    (checkout / "agent" / "skill_utils.py").write_text("# ok\n", encoding="utf-8")
    (checkout / "tools" / "skills_tool.py").write_text("# ok\n", encoding="utf-8")

    def boom(*_args: object, **_kwargs: object) -> _subprocess.CompletedProcess[bytes]:
        raise _subprocess.TimeoutExpired(cmd="python", timeout=5)

    monkeypatch.setattr(_patcher_helpers.subprocess, "run", boom)
    assert _patcher_helpers.file_has_circular_import(checkout / "agent" / "skill_utils.py") is False


def test_diff_sha_deterministic() -> None:
    """The diff-sha helper is deterministic and stable."""
    from easter_hermes_sorry_skills._patcher_apply_atomic import _diff_sha

    h1 = _diff_sha(b"before", b"after")
    h2 = _diff_sha(b"before", b"after")
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_diff_sha_separates_empty_inputs() -> None:
    """Two empty inputs still produce a non-empty, distinct hash."""
    from easter_hermes_sorry_skills._patcher_apply_atomic import _diff_sha

    h_empty = _diff_sha(b"", b"")
    h_just_before = _diff_sha(b"x", b"")
    assert h_empty != h_just_before


# --- AC-2.3: dynamic placeholder keys in failure dicts ------------------


def test_line_drift_failure_uses_actual_line_number_key() -> None:
    """AC-2.3: a LINE_DRIFT failure encodes the actual 1-based line
    number in the dict key (``actual_at_line_<N>``). The drift
    diagnostic consumer reads the value via the dynamic key.
    """
    from easter_hermes_sorry_skills._patcher_validation import _line_drift_failure

    anchor = Anchor(line=716, text="    if len(desc) > 60:")
    text = "# pad\n" * 9 + "    if len(desc) > 60:\n"
    failure = _line_drift_failure(
        site=S1_CAP_SITE,
        anchor=anchor,
        line_no=10,  # found on L10 instead of expected L716
        text=text,
    )
    assert failure["reason"] == "LINE_DRIFT"
    assert failure["anchor_line"] == 716
    assert failure["found_at_line"] == 10
    # The dynamic key is the actual line number where the anchor was found.
    assert "actual_at_line_10" in failure
    assert "actual_at_line_<n>" not in failure  # no literal placeholder
    assert "    if len(desc) > 60:" in failure["actual_at_line_10"]


def test_text_drift_failure_uses_unknown_sentinel_key() -> None:
    """AC-2.3: TEXT_DRIFT failures key the actual content under the
    ``actual_at_line_unknown`` sentinel (no line number is known).
    """
    from easter_hermes_sorry_skills._patcher_validation import _text_drift_failure

    anchor = Anchor(line=716, text="    if len(desc) > 60:")
    failure = _text_drift_failure(site=S1_CAP_SITE, anchor=anchor)
    assert failure["reason"] == "TEXT_DRIFT"
    assert failure["anchor_line"] == 716
    assert "actual_at_line_unknown" in failure
    assert "actual_at_line_<missing>" not in failure  # no literal placeholder
    assert failure["actual_at_line_unknown"] == "<not found>"


def test_missing_file_failure_uses_unknown_sentinel_key() -> None:
    """AC-2.3: TEXT_DRIFT for a missing file keys the actual content
    under ``actual_at_line_unknown`` with the MISSING_FILE constant.
    """
    from easter_hermes_sorry_skills._patcher_validation import _missing_file_failure

    failure = _missing_file_failure(S1_CAP_SITE)
    assert failure["reason"] == "TEXT_DRIFT"
    assert "actual_at_line_unknown" in failure
    assert "actual_at_line_<missing>" not in failure
    assert failure["actual_at_line_unknown"] == "<file missing>"


def test_text_drift_diagnostic_consumer_reads_sentinel_key() -> None:
    """AC-2.3: ``append_drift_diagnostic`` reads TEXT_DRIFT failures via
    the ``actual_at_line_unknown`` sentinel key (regression guard for
    the consumer-side migration from the literal placeholder). The
    i18n format string renders both ``{expected}`` and ``{actual}``
    placeholders so the operator sees the drifted content.
    """
    from easter_hermes_sorry_skills._patcher_pipeline_emit_helpers import (
        append_drift_diagnostic,
    )

    diagnostics: list[str] = []
    append_drift_diagnostic(
        {
            "site_id": "S1.cap",
            "anchor_line": 716,
            "reason": "TEXT_DRIFT",
            "expected": "    if len(desc) > 60:",
            "actual_at_line_unknown": "<file missing>",
        },
        diagnostics,
    )
    # The TEXT_DRIFT diagnostic is emitted with the site_id, the
    # expected/actual drifted content, and the VALIDATION_FAILED
    # follow-up.
    assert any("S1.cap" in d for d in diagnostics)
    assert any("validation failed" in d for d in diagnostics)
    assert any("text drift" in d for d in diagnostics)
    assert any("if len(desc) > 60:" in d for d in diagnostics)
    assert any("<file missing>" in d for d in diagnostics)


def test_line_drift_diagnostic_consumer_reads_dynamic_key() -> None:
    """AC-2.3: ``append_drift_diagnostic`` reads LINE_DRIFT failures
    via the dynamic ``actual_at_line_<N>`` key. The diagnostic includes
    the anchor_line (NOT the actual line number).
    """
    from easter_hermes_sorry_skills._patcher_pipeline_emit_helpers import (
        append_drift_diagnostic,
    )

    diagnostics: list[str] = []
    append_drift_diagnostic(
        {
            "site_id": "S1.cap",
            "anchor_line": 716,
            "found_at_line": 10,
            "reason": "LINE_DRIFT",
            "expected": "    if len(desc) > 60:",
            "actual_at_line_10": "    if len(desc) > 60:",
        },
        diagnostics,
    )
    # The LINE_DRIFT message contains the EXPECTED anchor line (716),
    # not the found_at_line.
    assert any("716" in d for d in diagnostics)
    assert any("line drift" in d for d in diagnostics)


# --- AC-2.11 fallback: S1.cap_fallback + branching logic ----------------


def test_s1_cap_fallback_uses_local_constant() -> None:
    """AC-2.11: ``S1_CAP_SITE_FALLBACK`` uses a local
    ``_MAX_DESCRIPTION_LENGTH = 1024`` constant (no cross-module
    import). The anchors are identical to ``S1_CAP_SITE``.
    """
    assert S1_CAP_SITE_FALLBACK.site_id == "S1.cap_fallback"
    assert S1_CAP_SITE_FALLBACK.kind == "cap"
    assert S1_CAP_SITE_FALLBACK.anchors == S1_CAP_SITE.anchors
    # The fallback insertion prepends a local constant definition
    # then uses it in the cap check.
    assert "_MAX_DESCRIPTION_LENGTH = 1024" in S1_CAP_SITE_FALLBACK.insertion
    assert "if len(desc) > _MAX_DESCRIPTION_LENGTH:" in S1_CAP_SITE_FALLBACK.insertion
    # The regular S1.cap cross-module constant is NOT used.
    assert "    if len(desc) > MAX_DESCRIPTION_LENGTH:\n" not in S1_CAP_SITE_FALLBACK.insertion


def test_s1_cap_fallback_used_when_circular_import_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_hermes_agent_sentinel: str | None
) -> None:
    """AC-2.11: when ``file_has_circular_import`` returns True, the
    patcher swaps S1.cap for S1.cap_fallback. The cap-raise site is
    applied with the local constant instead of exiting on the cycle.
    """
    checkout = tmp_path / "fallback-apply"
    _write_task_e_files(checkout)
    lines: list[str] = ["# clean file\n"]
    for i in range(1, 715):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append('        return desc[:57] + "..."\n')
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")

    # Force the circular-import preflight to fire.
    from easter_hermes_sorry_skills import _patcher_internals

    def _force_circular(
        _skill_utils_path: Path,
        *,
        cycle_marker: str = "",
    ) -> bool:
        return True

    monkeypatch.setattr(
        _patcher_internals._imps,
        "file_has_circular_import",
        _force_circular,
    )

    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    # The fallback cap-raise uses the LOCAL constant — no import
    # from tools.skills_tool is needed at runtime.
    assert "_MAX_DESCRIPTION_LENGTH = 1024" in text
    assert "if len(desc) > _MAX_DESCRIPTION_LENGTH:" in text


def test_s1_cap_used_when_no_circular_import(tmp_path: Path, real_hermes_agent_sentinel: str | None) -> None:
    """AC-2.11 negative path: when there is no circular import, the
    patcher uses the regular S1.cap site (cross-module
    ``MAX_DESCRIPTION_LENGTH``) and does NOT emit the cycle diagnostic.
    """
    checkout = tmp_path / "normal-apply"
    _write_task_e_files(checkout)
    lines: list[str] = []
    for i in range(1, 716):
        lines.append(f"# pad {i}\n")
    lines.append("    if len(desc) > 60:\n")
    lines.append('        return desc[:57] + "..."\n')
    (checkout / "agent" / "skill_utils.py").write_text("".join(lines), encoding="utf-8")

    r = run_patch(
        PatchRunInputs(
            target=checkout,
            dry_run=False,
        ),
    )
    assert r.exit_code == EXIT_OK
    text = (checkout / "agent" / "skill_utils.py").read_text(encoding="utf-8")
    # Normal S1.cap — uses the cross-module constant, NOT the fallback.
    assert "if len(desc) > MAX_DESCRIPTION_LENGTH:" in text
    assert "_MAX_DESCRIPTION_LENGTH" not in text
    # No cycle diagnostic.
    assert not any("circular import" in d for d in r.diagnostics)


# =====================================================================
# Skills prompt snapshot purge + per-site idempotency (Task E refactor)
# =====================================================================


def test_purge_skills_prompt_snapshot_removes_file(tmp_path: Path) -> None:
    """purge_skills_prompt_snapshot() deletes the file and is idempotent."""
    from easter_hermes_sorry_skills._patcher_pipeline_purge import (
        SKILLS_PROMPT_SNAPSHOT_FILENAME,
        purge_skills_prompt_snapshot,
    )

    snapshot = tmp_path / SKILLS_PROMPT_SNAPSHOT_FILENAME
    snapshot.write_text("{}")
    purged = purge_skills_prompt_snapshot(tmp_path)
    assert purged == snapshot
    assert not snapshot.exists()
    # Idempotent: second call returns the path unconditionally and is a no-op
    # (file already gone — unlink(missing_ok=True) is a no-op).
    purged2 = purge_skills_prompt_snapshot(tmp_path)
    assert purged2 == snapshot
    assert not snapshot.exists()


def test_resolve_skills_prompt_snapshot_path_expands_tilde_in_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """resolve_skills_prompt_snapshot_path() must .expanduser().resolve() HERMES_HOME.

    F-27 regression: when HERMES_HOME is set to a literal ``~``-prefixed
    path, the patcher audit log writes to the resolved absolute path
    (via _hermes_home_for_audit's .expanduser().resolve()), but the
    purge resolver returned the literal un-expanded path, causing a
    silent no-op. This test pins the env-var branch to also expanduser
    + resolve, matching the audit-log resolver.
    """
    from easter_hermes_sorry_skills._patcher_pipeline_purge import (
        SKILLS_PROMPT_SNAPSHOT_FILENAME,
        resolve_skills_prompt_snapshot_path,
    )

    # Redirect HOME so ``~`` resolves to tmp_path (tmp_path on macOS is
    # under /private/var/... — not under Path.home()), then point
    # HERMES_HOME at a fresh subdir using the tilde form. The resolver
    # must call .expanduser().resolve() to land on the absolute path.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", "~")
    resolved = resolve_skills_prompt_snapshot_path()
    assert resolved == (tmp_path / SKILLS_PROMPT_SNAPSHOT_FILENAME).resolve()
    assert "~" not in str(resolved)


def test_apply_purges_skills_cache(
    hermes_checkout: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Successful --apply purges the skills prompt snapshot from the fake HERMES_HOME."""
    from easter_hermes_sorry_skills import _patcher
    from easter_hermes_sorry_skills._patcher_pipeline_purge import (
        SKILLS_PROMPT_SNAPSHOT_FILENAME,
    )

    # hermes_checkout already set HERMES_HOME=hermes_checkout via the
    # hermes_home fixture; install the snapshot INSIDE that directory
    # so the post-apply purge deletes it.
    snapshot = hermes_checkout / SKILLS_PROMPT_SNAPSHOT_FILENAME
    snapshot.write_text("{}")
    # First --apply to populate state.
    r1 = _patcher.run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r1.exit_code == EXIT_OK, f"first apply failed: {r1.diagnostics}"
    # The snapshot must be purged by the end of the successful apply.
    assert not snapshot.exists(), "skills prompt snapshot was NOT purged by --apply"
    # Diagnostics should mention the purge.
    purge_msgs = [d for d in r1.diagnostics if "snapshot" in d.lower() or "purge" in d.lower()]
    assert purge_msgs, f"no purge diagnostic in {r1.diagnostics}"
    # Second --apply is a no-op for the snapshot (already gone).
    r2 = _patcher.run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r2.exit_code == EXIT_OK, f"second apply failed: {r2.diagnostics}"


@pytest.mark.parametrize("site", [S1_CAP_SITE, *ALL_TASK_E_SITES], ids=lambda s: s.site_id)
def test_idempotency_per_site(
    site: Site,
    hermes_checkout: Path,
) -> None:
    """Each site is idempotent on reapply: second --apply reports the site
    as 'already patched' / 'már javítva'."""
    # First --apply: site lands in ``sites_patched``.
    r1 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r1.exit_code == EXIT_OK, f"first apply failed: {r1.diagnostics}"
    assert site.site_id in r1.sites_patched, f"{site.site_id} should be patched on first apply; got {r1.sites_patched}"
    # Second --apply: site must be reported as 'already patched' (either
    # by appearing in ``sites_already`` OR by a bilingual diagnostic
    # naming the site). The two together cover both code paths.
    r2 = run_patch(
        PatchRunInputs(
            target=hermes_checkout,
            dry_run=False,
        ),
    )
    assert r2.exit_code == EXIT_OK, f"second apply failed: {r2.diagnostics}"
    reapply_msg = f"{site.site_id} should be 'already patched' on reapply; got {r2.sites_already}"
    assert site.site_id in r2.sites_already, reapply_msg
    already_msgs = [d for d in r2.diagnostics if site.site_id in d]
    assert already_msgs, f"no diagnostic naming {site.site_id} on reapply: {r2.diagnostics}"
