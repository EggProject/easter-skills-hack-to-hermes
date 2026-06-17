# Task-E prompt edits — authored spec (do NOT let the executing LLM re-derive these)

Authored from the REAL source `NousResearch/hermes-agent` @ `36ae958`, byte-verified (`cat -A`). This replaces
the plan's E1/E2/E4/E6 anchors, which have been paraphrased/joined-across-lines and would TEXT_DRIFT.
Rule: ADDITIVE only — insert one line, never rewrite existing prompt text; never auto-install; graceful
fallback if `skill-creator` is absent; do NOT touch background-review selection logic or decision order.

GOAL of every insertion: point the agent at the `skill-creator` skill for CREATING, MODIFYING, and
VALIDATING/CHECKING skills (small targeted fixes stay patch-first; skill-creator is guidance only —
`skill_manage` stays the writer).

## Canonical shared rule (define once, reuse at E1–E5 so they cannot drift)
Define in `agent/prompt_builder.py`; import into `agent/background_review.py`:
```python
SKILL_CREATOR_CONSULT_RULE = (
    "When creating a new skill — or substantially editing or validating one — first check installed "
    "skills; if `skill-creator` is installed, load it via skill_view(name='skill-creator') and follow its "
    "authoring/validation guidance, then persist with skill_manage. Small targeted fixes stay patch-first. "
    "If `skill-creator` is absent, use the built-in skill rules and never auto-install it (especially not "
    "from the background review)."
)
```

## Per-site anchors + insertion (locator = a REAL contiguous physical line; match that, not a joined string)

| Site | File | Locator line (byte-exact, copy from source) | Insert | Placement |
| --- | --- | --- | --- | --- |
| E1 | agent/prompt_builder.py | L179 `    "Skills that aren't maintained become liabilities."` | `    " " + SKILL_CREATOR_CONSULT_RULE` | new body line AFTER L179, before the `)` on L180 (4-space indent) |
| E2 | agent/prompt_builder.py | L158 `    "necessary later, save it as a skill with the skill tool.\n"` | `    " " + SKILL_CREATOR_CONSULT_RULE + "\n"` | new line immediately AFTER L158 (inside constant, 4-space) |
| E3 | agent/prompt_builder.py (in `build_skills_system_prompt`) | L1421 `            "After difficult/iterative tasks, offer to save as a skill. "` | `            SKILL_CREATOR_CONSULT_RULE + "\n"` | new line AFTER L1421, before L1422; do NOT touch the `<available_skills>` join (L1425-1426), 12-space |
| E4 | agent/background_review.py (`_SKILL_REVIEW_PROMPT`) | L105 `    "today's task, it's wrong — fall back to (1), (2), or (3).\n\n"` | `    SKILL_CREATOR_CONSULT_RULE + "\n\n"` | AFTER L105 (i.e. after the option-4 paragraph closes). Do NOT insert between L100–L105 (splits the sentence). Import the constant. |
| E5 | agent/background_review.py (`_COMBINED_REVIEW_PROMPT`) | L192 `    "(2), or (3).\n\n"` | `    SKILL_CREATOR_CONSULT_RULE + "\n\n"` | AFTER L192 (after option-4 closes). Do NOT insert between L188–L192. |
| E6 (OPTIONAL) | tools/skill_manager_tool.py (`SKILL_MANAGE_SCHEMA`) | L1129 `        "pitfalls come up; pin only guards against irrecoverable loss."` (unique; append at end of the description value) | `        " skill-creator, when installed, supplies authoring/validation guidance only (skill_view(name='skill-creator')); skill_manage remains the writer and never auto-installs it."` | new line AFTER L1129, before the `),` on L1130 (8-space). Do NOT change actions/required/properties. |
| E7 | website/docs/user-guide/features/skills.md | L380 (existing first paragraph under the heading) | `> Note: \`skill-creator\` is an optional, hub-installed authoring/validation skill — NOT bundled, NOT required. \`skill_manage\` remains the only writer; the agent may \`skill_view(name='skill-creator')\` for guidance before creating/editing a skill, falls back to built-in rules if it is absent (auto-creation stays enabled), and the background review never auto-installs it.` | new line AFTER L380, before the blank line preceding `### When the Agent Creates Skills`. Do NOT rename the heading. |

E6 compound symbol locator (the bare `"description": (` is NON-unique — 8 occurrences — so anchor on the 3-line
sequence): L1099 `SKILL_MANAGE_SCHEMA = {` / L1100 `    "name": "skill_manage",` / L1101 `    "description": (`.

## Which round-4 plan anchors are WRONG (replace with the above)
- E6: plan's joined `current_text` "Manage skills … procedural memory — reusable approaches for recurring task types." has 0 source hits — the real string is split across L1102 (`"…your procedural "`) + L1103 (`"memory — reusable approaches…"`). Use a single physical line (L1102 or L1129) or the 3-line symbol locator.
- E1/E2/E4: plan quotes a JOINED sentence (0 single-line hits). Real single-line locators are E1=L179/L176, E2=L158, E4=L100. Use those.
- E3 / E5 / E7: plan anchors are already byte-accurate (L1420-1421, L188, L378). Keep.
