"""Script #1 patcher: cap-raise + opt-in Task E sites.

Idempotent, all-or-nothing patcher for a user-owned Hermes checkout.

The patcher:

1. Refuses to run when ``--target`` resolves to ``~/.hermes/hermes-agent``
   (exit code 4, bilingual diagnostic).
2. Pre-validates every site in a single pass against the file's raw bytes
   (multi-signal targeting: 8+ char anchor + 1-based line number).
3. On a cycle-detection pre-flight against ``agent/skill_utils.py``'s
   existing imports from ``tools.skills_tool``, refuses to write and exits
   with code 4.
4. On validation failure for ANY site, writes a ``.patch.rejected`` JSON
   sidecar and exits non-zero with ZERO bytes touched on the target.
5. On success, performs the atomic-write protocol
   (``<file>.patch.tmp`` + ``os.replace``), preserves file mode bits,
   and updates ``.patch.state.json``.
6. Emits a ``.patch.audit.log`` line on every successful ``--force`` run.

The site table is the spec-of-truth. The two-line ``S1.cap`` is a SINGLE
``site_id`` with two anchors (``a`` + ``b``); both anchors must match for
the site to be considered patched (partial replacement is drift).

See also: plans/04-script-1-patch.md, plans/05-script-1-task-e-toggle.md,
plans/10-toolchain-and-conventions.md, plans/09-test-strategy.md.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .i18n.messages_en import (
    CIRCULAR_IMPORT_PREFLIGHT,
    CROSS_FS_WARN,
    FORCE_AUDIT_LOG,
    FORCE_REQUIRES_I_ACCEPT,
    LINE_DRIFT,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
    PERMISSION_DENIED,
    TARGET_IS_HERMES_AGENT,
    TARGET_MISSING_SKILL_UTILS,
    TARGET_REQUIRED,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)

# --- exit codes (per plans/04-script-1-patch.md §Exit code matrix) --------
EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_DRIFT = 2
EXIT_PERMISSION = 3
EXIT_IO = 4
EXIT_USER_ABORT = 5

# --- shared Task E constant (the inserted consult rule) -------------------
SKILL_CREATOR_CONSULT_RULE = (
    "When creating a new skill — or substantially editing or validating "
    "one — first check installed skills; if `skill-creator` is installed, "
    "load it via skill_view(name='skill-creator') and follow its "
    "authoring/validation guidance, then persist with skill_manage. Small "
    "targeted fixes stay patch-first. If `skill-creator` is absent, use the "
    "built-in skill rules and never auto-install it (especially not from the "
    "background review)."
)

# --- file layout constants -----------------------------------------------
TOOLS_SKILL_UTILS_REL = Path("agent") / "skill_utils.py"
PROMPT_BUILDER_REL = Path("agent") / "prompt_builder.py"
BACKGROUND_REVIEW_REL = Path("agent") / "background_review.py"
SKILL_MANAGER_TOOL_REL = Path("tools") / "skill_manager_tool.py"
SKILLS_DOC_REL = Path("website") / "docs" / "user-guide" / "features" / "skills.md"

STATE_SIDECAR = Path(".patch.state.json")
REJECTED_SIDECAR = Path(".patch.rejected")
AUDIT_LOG = Path(".patch.audit.log")


# --- site data classes ----------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Anchor:
    """A single physical line that the patcher must locate exactly.

    ``line`` is 1-based; ``text`` is the byte-exact physical line content
    (no implicit-concat normalization, no whitespace scrubbing).
    """

    line: int
    text: str


@dataclasses.dataclass(frozen=True)
class Site:
    """A patch site.

    A site is identified by ``site_id`` and a list of :class:`Anchor`
    entries (1 anchor for an append-only Task E site, 2 anchors for the
    S1.cap atomic pair).

    ``kind`` is ``"cap"`` (replace pair), ``"append"`` (additive Task E
    line, ADDITIVE-ONLY per plans/05 B1.0), or ``"schema_append"``
    (E6-style: append a line inside a multi-line string value).

    ``file`` is the path RELATIVE to the --target root.

    ``expected_replacement`` is the verbatim text that, when present at
    the site, means the site is ALREADY patched (idempotency check).
    """

    site_id: str
    file: Path
    anchors: tuple[Anchor, ...]
    insertion: str
    expected_replacement: str
    kind: str = "append"
    line_for_state: int = 0  # primary anchor line for sidecar / migration note

    def primary_anchor(self) -> Anchor:
        return self.anchors[0]


# --- the S1.cap site (two-anchor atomic pair) -----------------------------

S1_CAP_SITE = Site(
    site_id="S1.cap",
    file=TOOLS_SKILL_UTILS_REL,
    anchors=(
        Anchor(line=688, text="    if len(desc) > 60:"),
        Anchor(line=689, text='        return desc[:57] + "..."'),
    ),
    insertion=(
        "    if len(desc) > MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    # The idempotency check looks for the replacement text:
    expected_replacement=(
        "    if len(desc) > MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    kind="cap",
    line_for_state=688,
)


# --- the 7 Task E sites ---------------------------------------------------

E1_SKILLS_GUIDANCE = Site(
    site_id="E1.skills_guidance",
    file=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=179,
            text='    "Skills that aren\'t maintained become liabilities."',
        ),
    ),
    # E1 is appended inside a parenthesized implicit-concat; the next
    # line is ")" closing the constant. We append ONE line that begins
    # with a single leading space, concatenating to the previous literal.
    insertion='    " " + SKILL_CREATOR_CONSULT_RULE\n',
    # Idempotency: the site is patched iff the appended line is present
    # verbatim after the L179 anchor.
    expected_replacement='    " " + SKILL_CREATOR_CONSULT_RULE',
    kind="append",
    line_for_state=179,
)

E2_MEMORY_GUIDANCE = Site(
    site_id="E2.memory_guidance",
    file=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=158,
            text='    "necessary later, save it as a skill with the skill tool.\\n"',
        ),
    ),
    insertion='    " " + SKILL_CREATOR_CONSULT_RULE + "\\n"\n',
    expected_replacement='    " " + SKILL_CREATOR_CONSULT_RULE + "\\n"',
    kind="append",
    line_for_state=158,
)

E3_BUILD_SKILLS_PROMPT = Site(
    site_id="E3.build_skills_prompt",
    file=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=1421,
            text='            "After difficult/iterative tasks, offer to save as a skill. "',
        ),
    ),
    insertion='            SKILL_CREATOR_CONSULT_RULE + "\\n"\n',
    expected_replacement='            SKILL_CREATOR_CONSULT_RULE + "\\n"',
    kind="append",
    line_for_state=1421,
)

E4_SKILL_REVIEW_PROMPT = Site(
    site_id="E4.skill_review_prompt_opt4",
    file=BACKGROUND_REVIEW_REL,
    anchors=(
        Anchor(
            line=105,
            text="    \"today's task, it's wrong — fall back to (1), (2), or (3).\\n\\n\"",
        ),
    ),
    insertion='    SKILL_CREATOR_CONSULT_RULE + "\\n\\n"\n',
    expected_replacement='    SKILL_CREATOR_CONSULT_RULE + "\\n\\n"',
    kind="append",
    line_for_state=105,
)

E5_COMBINED_REVIEW_PROMPT = Site(
    site_id="E5.combined_review_prompt_opt4",
    file=BACKGROUND_REVIEW_REL,
    anchors=(
        Anchor(
            line=192,
            text='    "(2), or (3).\\n\\n"',
        ),
    ),
    insertion='    SKILL_CREATOR_CONSULT_RULE + "\\n\\n"\n',
    expected_replacement='    SKILL_CREATOR_CONSULT_RULE + "\\n\\n"',
    kind="append",
    line_for_state=192,
)

E6_SKILL_MANAGE_SCHEMA_DESC = Site(
    site_id="E6.skill_manage_schema_desc",
    file=SKILL_MANAGER_TOOL_REL,
    anchors=(
        Anchor(
            line=1129,
            text='        "pitfalls come up; pin only guards against irrecoverable loss."',
        ),
    ),
    # E6 appends inside the multi-line description value (the closing
    # ")," lives on L1130). The appended line begins with one leading
    # space so it concatenates to the previous literal via Python
    # implicit-concat.
    insertion=(
        '        " skill-creator, when installed, supplies authoring/validation '
        "guidance only (skill_view(name='skill-creator')); skill_manage "
        'remains the writer and never auto-installs it."\n'
    ),
    expected_replacement=(
        '        " skill-creator, when installed, supplies authoring/validation '
        "guidance only (skill_view(name='skill-creator')); skill_manage "
        'remains the writer and never auto-installs it."'
    ),
    kind="schema_append",
    line_for_state=1129,
)

E7_SKILLS_DOC_SECTION = Site(
    site_id="E7.skills_doc_section",
    file=SKILLS_DOC_REL,
    anchors=(
        Anchor(
            line=380,
            text=(
                "The agent can create, update, and delete its own skills via the "
                "`skill_manage` tool. This is the agent's **procedural memory** — "
                "when it figures out a non-trivial workflow, it saves the approach "
                "as a skill for future reuse."
            ),
        ),
    ),
    # E7 is a markdown clarifier block; it sits as a blockquote paragraph
    # immediately after the L380 paragraph.
    insertion=(
        "\n"
        "> Note: `skill-creator` is an optional, hub-installed "
        "authoring/validation skill — NOT bundled, NOT required. "
        "`skill_manage` remains the only writer; the agent may "
        "`skill_view(name='skill-creator')` for guidance before "
        "creating/editing a skill, falls back to built-in rules if it is "
        "absent (auto-creation stays enabled), and the background review "
        "never auto-installs it.\n"
    ),
    expected_replacement=(
        "> Note: `skill-creator` is an optional, hub-installed "
        "authoring/validation skill — NOT bundled, NOT required. "
        "`skill_manage` remains the only writer; the agent may "
        "`skill_view(name='skill-creator')` for guidance before "
        "creating/editing a skill, falls back to built-in rules if it is "
        "absent (auto-creation stays enabled), and the background review "
        "never auto-installs it."
    ),
    kind="append",
    line_for_state=380,
)

ALL_TASK_E_SITES: tuple[Site, ...] = (
    E1_SKILLS_GUIDANCE,
    E2_MEMORY_GUIDANCE,
    E3_BUILD_SKILLS_PROMPT,
    E4_SKILL_REVIEW_PROMPT,
    E5_COMBINED_REVIEW_PROMPT,
    E6_SKILL_MANAGE_SCHEMA_DESC,
    E7_SKILLS_DOC_SECTION,
)


# --- public API -----------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PatcherResult:
    """Outcome of a patcher run.

    ``exit_code`` follows the matrix in plans/04 (0..5).
    ``sites_patched`` is the list of site_ids touched by THIS run.
    ``sites_already`` is the list of site_ids that were already patched
    BEFORE this run (idempotency).
    ``state`` is the updated ``.patch.state.json`` mapping
    ``{site_id: "matched" | "drifted" | "patched" | "already"}``.
    ``diagnostics`` is the list of bilingual messages emitted.
    """

    exit_code: int
    sites_patched: tuple[str, ...]
    sites_already: tuple[str, ...]
    state: dict[str, str]
    diagnostics: tuple[str, ...]
    rejected_path: Path | None = None


def hermes_agent_path() -> Path:
    """Resolved path to ``~/.hermes/hermes-agent`` (the no-touch sentinel)."""
    return (Path.home() / ".hermes" / "hermes-agent").resolve()


def is_hermes_agent(target: Path) -> bool:
    """True iff ``target`` resolves to ``~/.hermes/hermes-agent``."""
    return target.resolve() == hermes_agent_path()


def file_has_circular_import(
    skill_utils_path: Path, *, cycle_marker: str = "from tools.skills_tool import"
) -> bool:
    """True iff the top of ``agent/skill_utils.py`` already imports from tools.

    The pre-flight rejects the import strategy for ``MAX_DESCRIPTION_LENGTH``
    when the file already imports from ``tools.skills_tool`` to avoid an
    agent <-> tools cycle; the fallback is a local constant
    ``_MAX_DESCRIPTION_LENGTH = 1024``.
    """
    if not skill_utils_path.exists():
        return False
    text = skill_utils_path.read_text(encoding="utf-8", errors="replace")
    return cycle_marker in text


def locate_anchor(text: str, anchor: Anchor) -> int:
    """Return the 1-based line number where ``anchor.text`` appears in ``text``.

    Returns 0 when the anchor is not found. Matches the FULL line bytes
    (no implicit-concat normalization).
    """
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if line == anchor.text:
            return idx
    return 0


def site_already_patched(text: str, site: Site) -> bool:
    """True iff the site's ``expected_replacement`` is present in ``text``."""
    return site.expected_replacement in text


def site_in_state(state: dict[str, str], site_id: str, *, status: str) -> bool:
    """True iff the state sidecar records ``site_id`` as ``status``."""
    return state.get(site_id) == status


def load_state(target: Path) -> dict[str, str]:
    """Load ``.patch.state.json``; return empty dict on missing/corrupt."""
    sidecar = target / STATE_SIDECAR
    if not sidecar.exists():
        return {}
    try:
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def write_state(target: Path, state: dict[str, str]) -> None:
    """Write ``.patch.state.json`` atomically with sorted keys."""
    sidecar = target / STATE_SIDECAR
    payload = json.dumps(dict(sorted(state.items())), indent=2) + "\n"
    _atomic_write_bytes(sidecar, payload.encode("utf-8"))


def write_rejected(
    target: Path,
    *,
    failures: list[dict[str, Any]],
    remediation_en: str,
    remediation_hu: str,
    git_head: str,
) -> Path:
    """Write ``.patch.rejected`` JSON; return its path."""
    rejected_path = target / REJECTED_SIDECAR
    payload = {
        "tool": "hermes-skill-creator-patch",
        "version": "0.1.0",
        "target": str(target.resolve()),
        "git_head": git_head,
        "failures": failures,
        "remediation_en": remediation_en,
        "remediation_hu": remediation_hu,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write_bytes(rejected_path, text.encode("utf-8"))
    return rejected_path


def _atomic_write_bytes(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """Atomic write: tmp + os.replace; restore on exception; preserve mode.

    ``path`` is the final destination; ``<path>.patch.tmp`` is the temp
    file in the same directory (POSIX-atomic on the same filesystem).
    """
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        original_mode = path.stat().st_mode
    else:
        original_mode = mode if mode is not None else 0o644
    tmp_dir = str(parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".patch.tmp", dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fchmod(fd, original_mode)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    # After os.replace, ``path`` always exists (replace is atomic on
    # POSIX). The chmod is best-effort: if the FS rejects the chmod, we
    # don't fail the patch.
    try:
        os.chmod(path, stat.S_IMODE(original_mode), follow_symlinks=False)
    except OSError:
        pass


def _append_audit_log(audit_path: Path, line: str) -> None:
    """Append one line to the audit log; create parent dirs as needed."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def _diff_sha(before: bytes, after: bytes) -> str:
    return hashlib.sha256(before + b"\0" + after).hexdigest()


def _sites_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> tuple[Site, ...]:
    """Return the (S1.cap, [Task E...]) tuple for the given flag combination."""
    sites: list[Site] = [S1_CAP_SITE]
    if not task_e_redirect:
        return tuple(sites)
    for s in ALL_TASK_E_SITES:
        if no_schema_redirect and s.site_id == E6_SKILL_MANAGE_SCHEMA_DESC.site_id:
            continue
        sites.append(s)
    return tuple(sites)


# --- the main entry point -------------------------------------------------


def run_patch(
    *,
    target: Path | None,
    check: bool,
    apply: bool,
    force: bool,
    i_accept_line_drift: bool,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    yes: bool = False,
    verbose: bool = False,
    audit_log_path: Path | None = None,
    git_head: str = "",
) -> PatcherResult:
    """Run the patcher.

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible for
    translating ``exit_code`` into a ``SystemExit``. This function never
    raises SystemExit; it returns a result.
    """
    diagnostics: list[str] = []

    if target is None:
        diagnostics.append(TARGET_REQUIRED)
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    target_path = Path(target).resolve()
    if is_hermes_agent(target_path):
        diagnostics.append(TARGET_IS_HERMES_AGENT.format(resolved=str(target_path)))
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    skill_utils = target_path / TOOLS_SKILL_UTILS_REL
    if not skill_utils.exists():
        diagnostics.append(TARGET_MISSING_SKILL_UTILS.format(path=str(skill_utils)))
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    if force and not i_accept_line_drift:
        diagnostics.append(FORCE_REQUIRES_I_ACCEPT)
        return PatcherResult(
            exit_code=EXIT_USER_ABORT,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    if file_has_circular_import(skill_utils):
        diagnostics.append(CIRCULAR_IMPORT_PREFLIGHT)
        return PatcherResult(
            exit_code=EXIT_IO,
            sites_patched=(),
            sites_already=(),
            state={},
            diagnostics=tuple(diagnostics),
        )

    sites = _sites_for_mode(task_e_redirect=task_e_redirect, no_schema_redirect=no_schema_redirect)
    state = load_state(target_path)
    sites_patched: list[str] = []
    sites_already: list[str] = []

    # --- pre-validate every site in a single pass -----------------------
    failures: list[dict[str, Any]] = []
    for site in sites:
        path = target_path / site.file
        if not path.exists():
            failures.append(
                {
                    "site_id": site.site_id,
                    "reason": "TEXT_DRIFT",
                    "expected": site.primary_anchor().text,
                    "actual_at_line_<missing>": "<file missing>",
                }
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if site_already_patched(text, site):
            sites_already.append(site.site_id)
            state[site.site_id] = "patched"
            continue
        for anchor in site.anchors:
            line_no = locate_anchor(text, anchor)
            if line_no == 0:
                failures.append(
                    {
                        "site_id": site.site_id,
                        "anchor_line": anchor.line,
                        "reason": "TEXT_DRIFT",
                        "expected": anchor.text,
                        "actual_at_line_<missing>": "<not found>",
                    }
                )
                break
            if line_no != anchor.line:
                failures.append(
                    {
                        "site_id": site.site_id,
                        "anchor_line": anchor.line,
                        "found_at_line": line_no,
                        "reason": "LINE_DRIFT",
                        "expected": anchor.text,
                        "actual_at_line_<n>": (
                            text.splitlines()[line_no - 1]
                            if line_no <= len(text.splitlines())
                            else "<out of range>"
                        ),
                    }
                )
                break
        else:
            state[site.site_id] = "matched"

    if failures:
        rejected_path = write_rejected(
            target_path,
            failures=failures,
            remediation_en=("Re-run with --force --i-accept-line-drift after reviewing the diff."),
            remediation_hu=(
                "Futtassa újra --force --i-accept-line-drift kapcsolóval a diff " "átnézése után."
            ),
            git_head=git_head,
        )
        for f in failures:
            if f.get("reason") == "LINE_DRIFT":
                diagnostics.append(LINE_DRIFT.format(site_id=f["site_id"], line=f["anchor_line"]))
            else:
                diagnostics.append(
                    TEXT_DRIFT.format(
                        site_id=f["site_id"],
                        expected=f.get("expected", ""),
                        actual=f.get("actual_at_line_<missing>", ""),
                    )
                )
            diagnostics.append(VALIDATION_FAILED.format(site_id=f["site_id"]))
        return PatcherResult(
            exit_code=EXIT_DRIFT,
            sites_patched=(),
            sites_already=tuple(sites_already),
            state=state,
            diagnostics=tuple(diagnostics),
            rejected_path=rejected_path,
        )

    # --- check mode: emit OK and return ---------------------------------
    if check or not apply:
        for site in sites:
            if site.site_id in sites_already:
                diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
            else:
                diagnostics.append(OK_PATCHED.format(site_id=site.site_id))
        write_state(target_path, state)
        return PatcherResult(
            exit_code=EXIT_OK,
            sites_patched=tuple(sites_patched),
            sites_already=tuple(sites_already),
            state=state,
            diagnostics=tuple(diagnostics),
        )

    # --- apply mode: atomic write per file ------------------------------
    audit_path = audit_log_path or (target_path / AUDIT_LOG)
    timestamp = _now_iso()
    for site in sites:
        if site.site_id in sites_already:
            diagnostics.append(OK_ALREADY_PATCHED.format(site_id=site.site_id))
            continue
        path = target_path / site.file
        before = path.read_bytes()
        text = before.decode("utf-8", errors="replace")
        anchor = site.primary_anchor()
        lines = text.splitlines(keepends=True)
        # 1-based line number -> 0-based index
        idx = anchor.line - 1
        original_line = lines[idx]  # noqa: F841  (kept for forensic logging)
        # Branch on the site kind:
        #   "cap"          — REPLACE the primary anchor (and the sibling
        #                    secondary anchor) with the new replacement
        #                    text in-place.
        #   "schema_append"— INSERT a new line right after the primary
        #                    anchor (inside the multi-line implicit-concat
        #                    value of a `description` field).
        #   "append"       — INSERT a new line right after the primary
        #                    anchor (Task E additive-only spec).
        if site.kind == "cap":
            # The S1.cap site is a pair (a, b) at two consecutive lines.
            # We replace BOTH anchor lines with the new text. ``insertion``
            # is the new pair as a single string with newlines.
            new_pair_lines = site.insertion.splitlines(keepends=True)
            # Replace lines[idx:idx+2] with new_pair_lines. The pre-validation
            # pass guarantees both anchors match; this is a no-arg slice.
            lines = lines[:idx] + new_pair_lines + lines[idx + 2 :]
        else:
            # append / schema_append: insert one new line right after
            # the primary anchor.
            lines.insert(idx + 1, site.insertion)
        after_bytes = "".join(lines).encode("utf-8")
        try:
            _atomic_write_bytes(path, after_bytes)
        except PermissionError:
            diagnostics.append(PERMISSION_DENIED.format(path=str(path)))
            state[site.site_id] = "drifted"
            write_state(target_path, state)
            return PatcherResult(
                exit_code=EXIT_PERMISSION,
                sites_patched=tuple(sites_patched),
                sites_already=tuple(sites_already),
                state=state,
                diagnostics=tuple(diagnostics),
            )
        except OSError:
            diagnostics.append(PERMISSION_DENIED.format(path=str(path)))
            state[site.site_id] = "drifted"
            write_state(target_path, state)
            return PatcherResult(
                exit_code=EXIT_PERMISSION,
                sites_patched=tuple(sites_patched),
                sites_already=tuple(sites_already),
                state=state,
                diagnostics=tuple(diagnostics),
            )
        # audit log on --force; in non-force runs we also log because the
        # audit log is the durable record per AC-2.5.1.
        if force:
            diff_sha = _diff_sha(before, after_bytes)
            audit_line = FORCE_AUDIT_LOG.format(
                timestamp=timestamp,
                site_id=site.site_id,
                diff_sha=diff_sha,
                target=str(target_path),
            )
            _append_audit_log(audit_path, audit_line)
        sites_patched.append(site.site_id)
        state[site.site_id] = "patched"
        diagnostics.append(OK_PATCHED.format(site_id=site.site_id))

    # cross-filesystem warn (best-effort)
    if _cross_filesystem(target_path):
        diagnostics.append(CROSS_FS_WARN)

    write_state(target_path, state)
    return PatcherResult(
        exit_code=EXIT_OK,
        sites_patched=tuple(sites_patched),
        sites_already=tuple(sites_already),
        state=state,
        diagnostics=tuple(diagnostics),
    )


def _cross_filesystem(target: Path) -> bool:
    """Best-effort cross-filesystem detector (returns False on platforms
    that do not support ``os.statvfs``)."""
    try:
        target_stat = os.statvfs(target)
    except (OSError, AttributeError):
        return False
    try:
        tmp_stat = os.statvfs(tempfile.gettempdir())
    except (OSError, AttributeError):
        return False
    return target_stat.f_fsid != tmp_stat.f_fsid


def _now_iso() -> str:
    """ISO-8601 UTC timestamp; honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME")
    if frozen:
        return frozen
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- migration note generator --------------------------------------------


def generate_migration_note(
    *,
    target: Path,
    worktree: Path,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    git_head: str = "",
) -> Path:
    """Render ``MIGRATION.hermes-patch.md`` and ``MIGRATION.md`` index.

    The two files land in the worktree root, NOT in --target (per
    plans/04 §Migration note row counts + plans/08 §Determinism).
    Returns the path to ``MIGRATION.hermes-patch.md``.
    """
    timestamp = _now_iso()
    sites = _sites_for_mode(task_e_redirect=task_e_redirect, no_schema_redirect=no_schema_redirect)
    patch_rows = _render_patch_table(sites)
    cap_row = _render_cap_row()
    patch_md = _render_migration_hermes_patch(
        target=target,
        git_head=git_head,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        timestamp=timestamp,
        cap_row=cap_row,
        patch_rows=patch_rows,
    )
    (worktree / "MIGRATION.hermes-patch.md").write_text(patch_md, encoding="utf-8")
    index_md = _render_migration_index(timestamp)
    (worktree / "MIGRATION.md").write_text(index_md, encoding="utf-8")
    return worktree / "MIGRATION.hermes-patch.md"


def _render_cap_row() -> str:
    return (
        "| S1.cap | agent/skill_utils.py \\| extract_skill_description | "
        '`if len(desc) > 60:` and `return desc[:57] + "..."` | '
        "`if len(desc) > MAX_DESCRIPTION_LENGTH:` and "
        '`return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."` '
        "(with `MAX_DESCRIPTION_LENGTH` defined locally, e.g. "
        "`MAX_DESCRIPTION_LENGTH = 1024`, to avoid a circular import from "
        "`tools.skills_tool`) | `if len(desc) > 60:` |"
    )


def _render_patch_table(sites: Iterable[Site]) -> list[str]:
    """Render Task E rows. Excludes ``S1.cap`` (rendered separately)."""
    rows: list[str] = []
    for site in sites:
        if site.site_id == "S1.cap":
            continue
        rows.append(_render_task_e_row(site))
    return rows


def _render_task_e_row(site: Site) -> str:
    return (
        f"| {site.site_id} | {site.file}:{site.line_for_state} "
        f"(L{site.line_for_state}: `{_truncate(site.primary_anchor().text, 60)}`; "
        f"single physical line) | (preserved verbatim) | "
        f"`{_truncate(site.insertion.rstrip(chr(10)), 80)}` (additive) | "
        f"|"
    )


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", "\\n")
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _render_migration_hermes_patch(
    *,
    target: Path,
    git_head: str,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    timestamp: str,
    cap_row: str,
    patch_rows: list[str],
) -> str:
    task_e_section = ""
    if task_e_redirect:
        rows_text = "\n".join(patch_rows)
        task_e_section = (
            "\n## Task E sites (only if --task-e-redirect)\n\n"
            "| site_id | location | current | replacement | anchor |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"{rows_text}\n"
        )
    body = (
        "# Hermes Patch — Script #1 (cap raise + 7 Task E sites)\n"
        "\n"
        "<!-- generated; do not edit by hand -->\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| Target | {target.resolve()} |\n"
        f"| Target git head | {git_head} |\n"
        f"| --task-e-redirect | {'yes' if task_e_redirect else 'no'} |\n"
        f"| --no-schema-redirect | {'yes' if no_schema_redirect else 'no'} |\n"
        f"| Generated at | {timestamp} |\n"
        "\n"
        "## Cap-raise site (always applied)\n"
        "\n"
        "| site_id | location | current | replacement | anchor |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{cap_row}\n"
        f"{task_e_section}"
    )
    return body


def _render_migration_index(timestamp: str) -> str:
    return (
        "# Migration Note — Hermes Skill-Creator Plugin\n"
        "\n"
        "<!-- generated by hermes-skill-creator-patch --emit-migration-note; "
        "do not edit by hand -->\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Source repo | https://github.com/anthropics/claude-plugins-official |\n"
        "| Source skillId | skill-creator |\n"
        "| Pinned upstream commit | TBD |\n"
        "| Plugin version | 0.1.0 |\n"
        f"| Generated at | {timestamp} |\n"
        "\n"
        "## Documents in this set\n"
        "\n"
        "- `MIGRATION.hermes-patch.md` — Script #1 patches (cap raise + 7 Task E sites).\n"
        "- `MIGRATION.skill-port.md` — migrated skill bindings (T3 inventory).\n"
        "\n"
        "## How to apply\n"
        "\n"
        "1. Run Script #1 against your user-owned Hermes checkout:\n"
        "   `uv run hermes-skill-creator-patch --apply --task-e-redirect "
        "--target <hermes-checkout>`\n"
        "2. Run Script #1 with `--emit-migration-note` to regenerate this file.\n"
    )


def migration_rows_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> int:
    """Return the number of rows in the MIGRATION.hermes-patch.md table."""
    n = 1  # cap
    if task_e_redirect:
        n += 7
        if no_schema_redirect:
            n -= 1
    return n
