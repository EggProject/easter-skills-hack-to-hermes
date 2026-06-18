"""Script #1 patch sites: the S1.cap two-anchor atomic pair + 7 Task E sites.

The site table is the spec-of-truth (plans/04 §Multi-signal targeting +
plans/05 §Site table). The two-line ``S1.cap`` is a SINGLE ``site_id``
with two anchors (``a`` + ``b``); both anchors must match for the site to
be considered patched (partial replacement is drift). Task E sites are
ADDITIVE-ONLY (plans/05 D1): the patcher inserts a single new line
immediately after the primary anchor; existing text is preserved verbatim.

Each :class:`Site` carries a ``line_for_state`` (the primary anchor's
1-based line) and a single :class:`Anchor`. The 8-char minimum anchor
length and the 1-based line number are the multi-signal targeting that
prevents accidental matches (plans/04 D5).

The shared ``SKILL_CREATOR_CONSULT_RULE`` constant lives in this module
so that all 5 Task E prompt sites import the SAME text (plans/05 D2).
E4 and E5 (in ``agent/background_review.py``) MUST import this constant
from ``agent.prompt_builder`` at runtime; the patcher only writes the
LITERAL of the constant next to the anchor — drift is prevented by the
shared definition here.

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


def sites_for_mode(*, task_e_redirect: bool, no_schema_redirect: bool) -> tuple[Site, ...]:
    """Return the (S1.cap, [Task E...]) tuple for the given flag combination."""
    sites: list[Site] = [S1_CAP_SITE]
    if not task_e_redirect:
        return tuple(sites)
    for s in ALL_TASK_E_SITES:
        if no_schema_redirect and s.site_id == E6_SKILL_MANAGE_SCHEMA_DESC.site_id:
            continue
        sites.append(s)
    return tuple(sites)
