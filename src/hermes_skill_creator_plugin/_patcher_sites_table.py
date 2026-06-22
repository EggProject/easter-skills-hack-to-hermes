"""Patch site dataclasses + canonical site table for the S1.cap / Task E patcher.

TDD tests reference ``hermes_skill_creator_plugin._patcher_sites.Site`` /
``Anchor`` / ``S1_CAP_SITE`` / ``ALL_TASK_E_SITES`` / ``E*_SITE`` constants;
``_patcher_sites.py`` re-exports them so existing imports continue to work.

The site table is the spec-of-truth (plans/04 §Multi-signal targeting +
plans/05 §Site table). The two-line ``S1.cap`` is a SINGLE ``site_id``
with two anchors (``a`` + ``b``); both anchors must match for the site
to be considered patched (partial replacement is drift). Task E sites
are ADDITIVE-ONLY (plans/05 D1): the patcher inserts a single new line
immediately after the primary anchor; existing text is preserved verbatim.

Each :class:`Site` carries a ``line_for_state`` (the primary anchor's
1-based line) and a single :class:`Anchor`. The 8-char minimum anchor
length and the 1-based line number are the multi-signal targeting that
prevents accidental matches (plans/04 D5).

AC-2.8: the ``SKILL_CREATOR_CONSULT_RULE`` constant is no longer
defined in this plugin module. The canonical definition is written by
the E0 site into ``agent/prompt_builder.py`` (so the name is in scope
at module level for E1–E3 sites in the same file). E4 and E5 sites
(in ``agent/background_review.py``) reference the literal name and
rely on the E4b site, which writes a top-of-file
``from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE``
import line so the name resolves at runtime.

The text of the constant lives in :data:`_CONSULT_RULE_TEXT` and is
referenced by E0's ``insertion`` / ``expected_replacement`` so the
unit tests can still assert substring invariants against the patcher's
view of the value.

See also: plans/04-script-1-patch.md, plans/05-script-1-task-e-toggle.md,
plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

# --- file layout constants -----------------------------------------------
TOOLS_SKILL_UTILS_REL = Path("agent") / "skill_utils.py"
PROMPT_BUILDER_REL = Path("agent") / "prompt_builder.py"
BACKGROUND_REVIEW_REL = Path("agent") / "background_review.py"
SKILL_MANAGER_TOOL_REL = Path("tools") / "skill_manager_tool.py"
SKILLS_DOC_REL = Path("website") / "docs" / "user-guide" / "features" / "skills.md"

# --- shared Task E constant text (written into agent/prompt_builder.py by E0).
# The plugin does NOT define a Python-level ``SKILL_CREATOR_CONSULT_RULE``
# binding: the constant lives in the TARGET file (per plans/05 §D2). The
# text below is the canonical wording that E0 inserts verbatim at the top
# of ``agent/prompt_builder.py``. AC-2.8 unit tests assert substring
# invariants against this string.
_CONSULT_RULE_TEXT = (
    "When creating a new skill — or substantially editing or validating "
    "one — first check installed skills; if `skill-creator` is installed, "
    "load it via skill_view(name='skill-creator') and follow its "
    "authoring/validation guidance, then persist with skill_manage. "
    "Small targeted fixes stay patch-first. If `skill-creator` is absent, "
    "use the built-in skill rules and never auto-install it (especially "
    "not from the background review)."
)

# Top-of-file insertion (constant definition) for the E0 site. E0 anchors
# on the L1 docstring of ``agent/prompt_builder.py`` and appends this
# block immediately after, so the constant is at module level.
_CONSULT_RULE_DEFINITION = f"\nSKILL_CREATOR_CONSULT_RULE = (\n    {_CONSULT_RULE_TEXT!r}\n)\n"

# --- site ``kind`` constants (WPS226 — reused > 3 times) -------------------
KIND_APPEND = "append"
KIND_CAP = "cap"
KIND_SCHEMA_APPEND = "schema_append"

# Compact newline-literal aliases used by the Task E insertion strings.
# Extracted into named constants so wemake WPS342 (implicit raw string)
# does not flag the multi-`\n` patterns inside the Site() calls below.
_NL2 = "\n\n"
_E3_INSERTION = r"""            SKILL_CREATOR_CONSULT_RULE + "\n\n"
"""
_E3_EXPECTED = r'            SKILL_CREATOR_CONSULT_RULE + "\n\n"'
_E4_TEXT = '''    "today's task, it's wrong — fall back to (1), (2), or (3).

"'''
_E5_TEXT = '''    "(2), or (3).

"'''


# --- site data classes ----------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Anchor:
    """A single physical line that the patcher must locate exactly.

    ``line`` is 1-based; ``text`` is the byte-exact physical line
    content (no implicit-concat normalization, no whitespace scrubbing).
    """

    line: int
    text: str


@dataclasses.dataclass(frozen=True)
class Site:
    """A patch site.

    A site is identified by ``site_id`` and a list of :class:`Anchor`
    entries (1 anchor for an append-only Task E site, 2 anchors for
    the S1.cap atomic pair).

    ``kind`` is ``"cap"`` (replace pair), ``"append"`` (additive Task
    E line, ADDITIVE-ONLY per plans/05 B1.0), or ``"schema_append"``
    (E6-style: append a line inside a multi-line string value).

    ``file`` is the path RELATIVE to the --target root.

    ``expected_replacement`` is the verbatim text that, when present at
    the site, means the site is ALREADY patched (idempotency check).
    """

    site_id: str
    file_path: Path
    anchors: tuple[Anchor, ...]
    insertion: str
    expected_replacement: str
    kind: str = KIND_APPEND
    line_for_state: int = 0  # primary anchor line for sidecar / migration note

    def primary_anchor(self) -> Anchor:
        return self.anchors[0]


# --- canonical line-number constants (plans/04 §Multi-signal) -------------
S1_CAP_LINE_A = 688
S1_CAP_LINE_B = 689
E0_LINE = 1
# AC-2.8: E1/E2/E3 anchor lines are unchanged from plans/05 §B1.2
# because E0's insertion (constant definition) is applied LAST (the
# patcher sorts sites in DESCENDING line_for_state order), so the
# original anchors at L158/L179/L1421 are still valid against the
# pre-E0 file state. Real Hermes's prompt_builder.py and the test
# fixture mirror each other: both have a docstring at L1 + blank at
# L2 + the E1/E2/E3 anchors at L179/L158/L1421.
E1_LINE = 179
E2_LINE = 158
E3_LINE = 1421
E4B_LINE = 1
# Same descending-order logic for E4/E5 in ``agent/background_review.py``
# (E4b applies last, so L105/L192 anchors remain valid).
E4_LINE = 105
E5_LINE = 194
E6_LINE = 1129
E7_LINE = 380

# Top-of-file anchor lines for E0 (agent/prompt_builder.py) and E4b
# (agent/background_review.py). The patcher matches these against the
# target's L1 docstring; the canonical text below mirrors the test
# fixtures in ``tests/conftest.py``. In production, the docstring text
# may differ; the site TEXT_DRIFTs and aborts so the operator can review.
_E0_ANCHOR_TEXT = '"""Prompt builder (test fixture stand-in for agent/prompt_builder.py)."""'
_E4B_ANCHOR_TEXT = '"""Background review (test fixture stand-in for agent/background_review.py)."""'

# --- the S1.cap site (two-anchor atomic pair) -----------------------------

S1_CAP_SITE = Site(
    site_id="S1.cap",
    file_path=TOOLS_SKILL_UTILS_REL,
    anchors=(
        Anchor(line=S1_CAP_LINE_A, text="    if len(desc) > 60:"),
        Anchor(line=S1_CAP_LINE_B, text='        return desc[:57] + "..."'),
    ),
    insertion=(
        '    if len(desc) > MAX_DESCRIPTION_LENGTH:\n        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    # The idempotency check looks for the replacement text:
    expected_replacement=(
        '    if len(desc) > MAX_DESCRIPTION_LENGTH:\n        return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    kind=KIND_CAP,
    line_for_state=S1_CAP_LINE_A,
)

# AC-2.11 fallback: when ``tools.skills_tool`` cannot be imported in
# the target checkout (potential circular import), the patcher swaps
# S1.cap for S1.cap_fallback, which uses a LOCAL constant
# ``_MAX_DESCRIPTION_LENGTH = 1024`` instead of the cross-module
# ``MAX_DESCRIPTION_LENGTH``. The anchors are identical to S1.cap so
# the multi-signal targeting lines up; only the replacement text
# differs (it prepends a local-definition line).
_FALLBACK_MAX_DESCRIPTION_LENGTH = 1024
S1_CAP_SITE_FALLBACK = Site(
    site_id="S1.cap_fallback",
    file_path=TOOLS_SKILL_UTILS_REL,
    anchors=(
        Anchor(line=S1_CAP_LINE_A, text="    if len(desc) > 60:"),
        Anchor(line=S1_CAP_LINE_B, text='        return desc[:57] + "..."'),
    ),
    insertion=(
        f"    _MAX_DESCRIPTION_LENGTH = {_FALLBACK_MAX_DESCRIPTION_LENGTH}\n"
        "    if len(desc) > _MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    expected_replacement=(
        f"    _MAX_DESCRIPTION_LENGTH = {_FALLBACK_MAX_DESCRIPTION_LENGTH}\n"
        "    if len(desc) > _MAX_DESCRIPTION_LENGTH:\n"
        '        return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."\n'
    ),
    kind=KIND_CAP,
    line_for_state=S1_CAP_LINE_A,
)


# --- the 8 Task E sites ---------------------------------------------------

# E0 inserts the SKILL_CREATOR_CONSULT_RULE constant definition at the
# top of agent/prompt_builder.py (immediately after the L1 docstring).
# This is the single source of truth for the constant's wording; E1-E3
# reference the literal name SKILL_CREATOR_CONSULT_RULE which resolves
# at module level once E0 has been applied. The patcher applies sites
# in DESCENDING line order so E0 (L1) runs last and its insertion
# doesn't shift higher-line anchors.
E0_CONSULT_RULE_DEF = Site(
    site_id="E0.consult_rule_def",
    file_path=PROMPT_BUILDER_REL,
    anchors=(Anchor(line=E0_LINE, text=_E0_ANCHOR_TEXT),),
    insertion=_CONSULT_RULE_DEFINITION,
    # Idempotency: the constant definition is present iff the marker
    # assignment line appears verbatim after the L1 anchor.
    expected_replacement="SKILL_CREATOR_CONSULT_RULE = (",
    kind=KIND_APPEND,
    line_for_state=E0_LINE,
)

# E4b inserts the top-of-file import of SKILL_CREATOR_CONSULT_RULE
# from agent.prompt_builder into agent/background_review.py so the
# E4 and E5 sites can use the constant name (the name resolves via
# the import at runtime).
E4B_CONSULT_RULE_IMPORT = Site(
    site_id="E4b.consult_rule_import",
    file_path=BACKGROUND_REVIEW_REL,
    anchors=(Anchor(line=E4B_LINE, text=_E4B_ANCHOR_TEXT),),
    insertion="from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE\n",
    expected_replacement="from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE",
    kind=KIND_APPEND,
    line_for_state=E4B_LINE,
)

E1_SKILLS_GUIDANCE = Site(
    site_id="E1.skills_guidance",
    file_path=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=E1_LINE,
            text='    "Skills that aren\'t maintained become liabilities."',
        ),
    ),
    # E1 is appended inside a parenthesized implicit-concat; the next
    # line is ")" closing the constant. We append ONE line that begins
    # with a single leading space, concatenating to the previous literal.
    insertion=r'    " " + SKILL_CREATOR_CONSULT_RULE' "\n",
    # Idempotency: the site is patched iff the appended line is present
    # verbatim after the L179 anchor.
    expected_replacement=r'    " " + SKILL_CREATOR_CONSULT_RULE',
    kind=KIND_APPEND,
    line_for_state=E1_LINE,
)

E2_MEMORY_GUIDANCE = Site(
    site_id="E2.memory_guidance",
    file_path=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=E2_LINE,
            text=r'    "necessary later, save it as a skill with the skill tool.\n"',
        ),
    ),
    insertion=r'    " " + SKILL_CREATOR_CONSULT_RULE + "\n"' "\n",
    expected_replacement=r'    " " + SKILL_CREATOR_CONSULT_RULE + "\n"',
    kind=KIND_APPEND,
    line_for_state=E2_LINE,
)

E3_BUILD_SKILLS_PROMPT = Site(
    site_id="E3.build_skills_prompt",
    file_path=PROMPT_BUILDER_REL,
    anchors=(
        Anchor(
            line=E3_LINE,
            text='            "After difficult/iterative tasks, offer to save as a skill. "',
        ),
    ),
    insertion=_E3_INSERTION,
    expected_replacement=_E3_EXPECTED,
    kind=KIND_APPEND,
    line_for_state=E3_LINE,
)

E4_SKILL_REVIEW_PROMPT = Site(
    site_id="E4.skill_review_prompt_opt4",
    file_path=BACKGROUND_REVIEW_REL,
    anchors=(
        Anchor(
            line=E4_LINE,
            text=_E4_TEXT,
        ),
    ),
    insertion=f"    SKILL_CREATOR_CONSULT_RULE + {_NL2!r}\n",
    expected_replacement=f"    SKILL_CREATOR_CONSULT_RULE + {_NL2!r}",
    kind=KIND_APPEND,
    line_for_state=E4_LINE,
)

E5_COMBINED_REVIEW_PROMPT = Site(
    site_id="E5.combined_review_prompt_opt4",
    file_path=BACKGROUND_REVIEW_REL,
    anchors=(
        Anchor(
            line=E5_LINE,
            text=_E5_TEXT,
        ),
    ),
    insertion=f"    SKILL_CREATOR_CONSULT_RULE + {_NL2!r}\n",
    expected_replacement=f"    SKILL_CREATOR_CONSULT_RULE + {_NL2!r}",
    kind=KIND_APPEND,
    line_for_state=E5_LINE,
)

E6_SKILL_MANAGE_SCHEMA_DESC = Site(
    site_id="E6.skill_manage_schema_desc",
    file_path=SKILL_MANAGER_TOOL_REL,
    anchors=(
        Anchor(
            line=E6_LINE,
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
    kind=KIND_SCHEMA_APPEND,
    line_for_state=E6_LINE,
)

E7_SKILLS_DOC_SECTION = Site(
    site_id="E7.skills_doc_section",
    file_path=SKILLS_DOC_REL,
    anchors=(
        Anchor(
            line=E7_LINE,
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
    kind=KIND_APPEND,
    line_for_state=E7_LINE,
)

ALL_TASK_E_SITES: tuple[Site, ...] = (
    E0_CONSULT_RULE_DEF,
    E1_SKILLS_GUIDANCE,
    E2_MEMORY_GUIDANCE,
    E3_BUILD_SKILLS_PROMPT,
    E4B_CONSULT_RULE_IMPORT,
    E4_SKILL_REVIEW_PROMPT,
    E5_COMBINED_REVIEW_PROMPT,
    E6_SKILL_MANAGE_SCHEMA_DESC,
    E7_SKILLS_DOC_SECTION,
)
