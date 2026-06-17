# Plan review — ROUND 4 (verification of the round-3 corrections)

CONTEXT: Diffed the new set (plans-c897d934) vs the Round-3 version, checked each Round-3 item (RR1–RR6),
the recurring-error systemic fixes (REC-1/2/3) and the PROCESS DIRECTIVE, re-validated against the real
source (`NousResearch/hermes-agent` @ `36ae958`). 4 subagents + direct spot-checks. No files added/removed;
README untouched; no regressions (B1–B4, M1, M2, R1, R3, R4, R5, R10, R11, R12 all still intact).

WHAT LANDED WELL:
- PROCESS DIRECTIVE adopted across all 14 files — each has a real "Decisions & evidence" block
  (Decision / Rationale / Evidence / Confidence), substantive not padding. #46005 and the Q2 event-shape are
  correctly flagged TBD/inferred. This directive is already paying off: it now makes the wrong calls VISIBLE
  (see S3 — several "verified-from-source" tags are on facts that are actually wrong).
- RR3 FIXED (Q6 no longer "3490"), RR4 FIXED (01:120 now references 00-index), RR5 FIXED (all footers ==
  `wc -l`; 09 now 392; per-file budget cells raised so none breach), RR6 FIXED (09 prose now "C3"),
  REC-2 FIXED (footer generation + `check_line_count.py` extended with footer + total guards — a real spec).

BUT the two DEEPEST recurring problems are STILL not actually fixed — the LLM added tests/claims ASSERTING
they're fixed without achieving them. These are the priority.

================================================================
MUST-FIX
================================================================

S1. [RR1 / REC-1 — 3rd round, run-aborting] Task-E anchor `current_text` values are still NOT real byte
    sequences from the source. The old fabricated E6 string is now correctly quarantined to rationale notes
    (good), BUT the NEW E6 `current_text` — "Manage skills (create, update, delete). Skills are your
    procedural memory — reusable approaches for recurring task types. " — has ZERO byte-for-byte hits in the
    source, because the real description is split across two physical lines via Python implicit string
    concatenation (skill_manager_tool.py:1102 = `"...your procedural "`, :1103 = `"memory — reusable
    approaches for recurring task types. "`). Same defect for E1 (SKILLS_GUIDANCE), E2 (MEMORY_GUIDANCE),
    E4 (`_SKILL_REVIEW_PROMPT` opt-4) — all paraphrased as one logical line but physically wrapped, so all
    have 0 single-line hits. Only E3a/E3b/E5 and the cap site actually match. Script #1 matches `current_text`
    as a literal substring with NO implicit-concat normalization specified (04:96/114), so a default-on
    `--task-e-redirect` run still TEXT_DRIFTs + ABORTS — exactly what RR1 was meant to eliminate.
    The new meta-test `test_task_e_current_text_is_unique_in_source` (09) is ALSO broken: it special-cases E6
    with an ELLIPSIS form ("Manage skills … procedural memory — ...") that dodges the real grep, so the test
    would pass while the operative anchor fails on a real checkout.
    => FIX (pick one, apply to E1,E2,E4,E6 — verify each against the live file): (a) set each `current_text`
       to an ACTUAL single contiguous source line copied byte-for-byte (e.g. E6 → `"Manage skills (create,
       update, delete). Skills are your procedural "`, the real line 1102), OR (b) specify that Script #1
       joins Python implicitly-concatenated string literals before matching and make each `current_text` the
       real joined value. Then make the meta-test grep the OPERATIVE `current_text` (no ellipsis special-case)
       for ALL sites E1–E7 + cap, asserting hit-count == 1 against the pinned checkout. This is the recurring
       root cause: anchors are still hand-typed/paraphrased, not produced by reading the file.
    => AUTHORED FOR YOU: the exact byte-accurate anchors + one-line `skill-creator` insertions + placement for
       ALL 7 sites are in `TASK_E_PROMPT_EDITS.md` (derived from the real source, em-dashes/indent verified).
       Apply those verbatim instead of re-deriving. (E3/E5/E7 plan anchors are already correct; E1/E2/E4/E6 are
       the ones to replace.)

S2. [RR2 / REC-3 — recurs] 00-index totals are still wrong AND there is a new budget-sum contradiction.
    - The Actual column cells sum to 3312 (each cell matches real `wc -l`), but the Total cell (line 37) and
      prose (line 39, "Sum 3206") say 3206 — off by exactly 106 = file 00's own line count (file 00 omitted
      from the total). => Set the Total cell and the "Sum NNNN" prose to 3312.
    - Decision D2 (00-index) claims the Actual column/Total is "auto-generated from `wc -l` … verified-from-
      source", but the Total is hand-typed and wrong — either actually generate it or drop the claim.
    - Budget-sum is stated as "3570 sum" in 00:73, 12:48, 12:161, but the budget column actually sums to 4050
      (and the Total Budget cell correctly says 4050). 3570 matches nothing. => Reconcile to 4050 (or delete
      the standalone number and point to the table). Raising the per-file budgets to clear RR5 desynced 3570.

================================================================
SHOULD-FIX (process-directive accuracy — recurring line-number drift)
================================================================

S3. Several citations are flagged `verified-from-source` but point at the WRONG location (the exact
    "assumption-as-fact" the directive targets — non-fatal because targeting is symbol+anchor, but they
    mislead the reviewer and must be corrected, not trusted):
    - `agent/skill_utils.py:653/654` cited as the cap comparator/slice in 00-index, 03, 04, 07. Real cap is
      at 688/689; lines 653/654 are the docstring of an unrelated function (`Skill config is stored under …`).
    - 09 cites `MAX_DESCRIPTION_LENGTH` at "line 95"; real is `tools/skills_tool.py:98` (line 95 is blank).
      09 DOES already name `tools/skills_tool.py` (matching 04), so the only defect is the line number 95 -> 98.
    - 06 D4 cites `ensure_hub_dirs` at `hermes_cli/skills_hub.py:478`. Real: line 478 is `do_install`;
      `ensure_hub_dirs` is `tools/skills_hub.py:3287`.
    => Re-derive these line numbers from the pinned checkout and fix the citations; downgrade any that can't be
       confirmed from `verified-from-source` to `inferred`/`assumed`.

S4. 05 internal inconsistency: the single genuinely-wrong statement is 05:168 (decision D4) which says the
    description is "opened at 1102". Real: `"description": (` opens at line 1101; line 1102 is the first string
    literal. (05:61/89 correctly say 1101; 05:83/119 are also fine.) Fix 05:168 to 1101.

================================================================
META — why the same classes keep recurring (for the next pass)
================================================================
REC-1 (anchors) and REC-3 (totals) recurred AGAIN this round despite explicit systemic instructions, because
the LLM satisfied them on PAPER — it added a byte-for-byte directive, anchor/uniqueness tests, and an
"auto-generated from wc -l" claim — but the underlying values are still hand-typed/paraphrased (and in the
E6 case the meta-test was even rigged with an ellipsis to pass). The PROCESS DIRECTIVE is working exactly as
intended: we can now SEE that these were marked "verified-from-source" while being wrong. To actually stop the
recurrence, the systemic guards must be MACHINE-RUN, not hand-written: the plan should (1) generate every
`current_text` by literally reading the pinned file (and have CI grep the operative string, hit==1, for all
E1–E7+cap with no special-cases), and (2) generate the 00-index Actual column AND Total AND "Sum" prose from
`wc -l` at commit time. Until a value is produced by running a command rather than typed, it will keep drifting.

================================================================
BRIEF-COMPLIANCE (checked against the original igeny-prompt.md + the new feature) — NEW findings
================================================================
The plan satisfies most of the brief correctly (§5.2, §5.4, §5.5, §6.B, §6.D, §6.E, §8, and the new Script #3
reporter are all covered and code-verified). These are the genuine gaps:

S5. [BLOCKER — §6.C, latent since round 1, now code-confirmed NON-FUNCTIONAL] Script #2 disables the wrong
    thing and, as written, disables NOTHING. Brief §6.C: in every profile where `openai/skills/skill-creator`
    is enabled, DISABLE it and install ours. The plan instead adds the bare string `"openai"` to the disabled
    list (06: `desired_disabled = disabled_now | {"openai"}`; AC-3.2; `test_apply_disables_openai`). Real code:
    disabling is keyed by skill NAME (`tools/skills_tool.py:597` `return name in global_disabled`; `:646`
    `name = frontmatter.get("name", skill_dir.name)`), the factory skill's name is `skill-creator` (the
    `openai/skills/skill-creator` is only the hub INSTALL PATH — `skills_hub.py:1671`), and there is NO skill
    named `openai`. So `disabled=["openai"]` matches nothing → the factory skill-creator stays enabled.
    Note the name collision: disabling `skill-creator` by name would also disable OUR migrated one (same name).
    => The real swap is replacement-IN-PLACE: installing the migrated `skill-creator` into
       `~/.hermes/skills/skill-creator/` overwrites the factory copy (same dir/name). DROP the `"openai"`
       disable step (it's a no-op), rely on the flat-path install to replace the factory skill, and fix
       AC-3.2 + `test_apply_disables_openai` accordingly. The plan never reasons about this name collision —
       it must.

S6. [MAJOR — §5.7 erased] The brief's §5.7 deliverable is the continuously-maintained TODO LIST. The plan
    REASSIGNED the "§5.7" label to the new Script #3 reporter (01 deliverables table; 00-index row 13), so the
    brief's actual §5.7 (Todo list) is no longer mapped to any deliverable. => Give Script #3 its own
    deliverable id (it is an extra-brief feature WE requested, not §5.7), and restore §5.7 = the Todo list.

S7. [HITL note — §5.1 re-scope, likely fine] Brief §5.1 says the plugin "carries the 60->1024 cap-raise logic";
    the plan re-scopes the plugin to ADVISORY-ONLY and moves all patch logic to Script #1. This is defensible
    (a runtime mutation would violate §4; and `register_skill` cannot reach the `<available_skills>` index per
    plugins.py) and was an accepted decision (Q4), but it is a literal deviation from §5.1 — surface it
    explicitly at the HITL gate rather than leaving it as a silent re-scope.

S8. [MINOR] (a) 10's `report_main` sketch contradicts 13: it uses `--sort … last_used` (13 uses `last_used_at`)
    and `--profile required=True` (13 makes it optional). Align 10 to 13. (b) file 12 footer says "budget 200"
    but 00-index row 12 says budget 210 — footer/index budget desync (no breach, but inconsistent). (c)
    README.md is stale ("Produced 4/13 plan files"). (d) §6.A's GitHub issue is still only cited-as-TBD, not
    delivered (consistent with S3/M5 — verify before emitting); §8's "100% coverage = correctness" is
    over-claimed since coverage is fixture-based and hard line numbers (e.g. cap "653") are stale.

================================================================
CONFIRMED-GOOD this round (do NOT re-touch)
================================================================
RR3, RR4, RR5 (footers all == wc -l; no budget breaches), RR6, REC-2 (real check_line_count.py extension);
the process-directive "Decisions & evidence" blocks (structure + most citations correct: save_disabled_skills
@skills_config.py:45, clear_skills_system_prompt_cache @prompt_builder.py:1022, _PROFILE_DIRS @profiles.py:39,
register_skill @plugins.py:1037, plugin.yaml @plugins.py:19, skill_usage fields @skill_usage.py:463-468 — all
verified exact). B1–B4, M1, M2, R1 (02), R3 (no dangling refs), R4, R5, R10, R11, R12 intact. No add/del.
Source pin 36ae958 correct.
