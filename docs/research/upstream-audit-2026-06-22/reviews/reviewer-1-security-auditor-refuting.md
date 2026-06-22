# Phase 3 / Reviewer 1 — security-auditor refuting lens

**Reviewer**: security-auditor (refuting / adversarial)
**Phase 3 attempt**: 1
**Review date**: 2026-06-22
**Synthesis under review**: `docs/research/upstream-audit-synthesized.md`
**Synthesis summary**: 0 CRITICAL / 0 WARNING / 25 INFO (all DELIBERATE) / 5 NOTE — TOTAL 30

## Posture

- Assumed Phase 1 + Phase 2 missed ≥1 class of false-negative (CRITICAL hidden
  inside a DELIBERATE INFO; WARNING masked as INFO; NOTE row that should be
  INFO; dedup merging unrelated items; severity drift between lenses; missing
  upstream-evidence; coverage gap; reconciliation gap).
- Searched R1–R8 categories systematically. Verified the synthesis's claims
  against the actual files (`skills/skill-creator/`) with verbatim grep
  commands in this conversation (output captured in body below).
- **Verdict (preliminary)**: **PASS** — no false-negative CRITICAL or WARNING
  found; no dedup / severity / coverage / reconciliation gap that would block
  Phase 4.

## Refutation findings

| id | category | synthesis row | challenge | evidence | recommendation |
| --- | --- | --- | --- | --- | --- |
| (none) | — | — | (no refutation succeeded) | R1–R8 searches all clean (details below) | keep synthesis as-is |

## Per-category results

### R1 — False-negative CRITICAL

- **Findings: 0**

The brief explicitly flagged the risk that a "DELIBERATE bilingual advisory"
INFO row might actually be a *masquerading Claude system prompt* (e.g. an
"Anthropic recommends..." sentence that tricks the Hermes agent into Claude
behaviour). I reran the security-auditor's K1 adversarial grep verbatim
plus an extended variant:

```bash
grep -rnE "Anthropic recommends|Claude.system.prompt says|as Claude Code you must|as Claude, you must|as an AI assistant|as a helpful assistant|as Claude Code" skills/skill-creator/
# → exit 0 (matches in zero of the 18 prompt-bearing files)
```

Additional check — broader subject-marker patterns:

```bash
grep -rnE "as a(n)? (Claude|Anthropic|AI assistant)|you are (Claude|Anthropic|an AI)" skills/skill-creator/
# → exit 1 (zero matches)
```

I read the SKILL.md body end-to-end (`skills/skill-creator/SKILL.md`, 75 lines).
Every "Anthropic" mention is either (a) negative-form guard rail
(`Do NOT use Anthropic tool names`, `Do NOT call the Anthropic CLI`),
(b) provenance statement ("Hermes-native port of the Anthropic
`skill-creator`"), or (c) verification-checklist entry ("No Anthropic-CLI
invocations anywhere in `scripts/`"). None of these is a positive Claude
instruction. The closest to a "Claude system-prompt masquerade" pattern
would be a sentence saying "you should behave as Claude" or "Anthropic
recommends X" — none of those strings appear in the prompt layer.

**Conclusion**: the synthesis's DELIBERATE classification is correct. The
negative-form guard rails tell the Hermes agent the *opposite* of what a
masquerading Claude prompt would say. No R1 false-negative CRITICAL.

### R2 — False-negative WARNING

- **Findings: 0**

I checked whether any "Anthropic" / "Claude" mention is actually WARNING-class
(the brief flagged `claude.ai` URLs as the canonical false-negative WARNING
case):

```bash
grep -rnE "claude\.ai" skills/skill-creator/
# → exit 1 (zero matches)
grep -rnE "claude\.com|anthropic\.com" skills/skill-creator/
# → exit 0 (no output captured; same result)
```

T3.007 (the `claude.ai` URL binding in the upstream) was REMOVED entirely
during the migration per the plan's "remove or rewrite to nousresearch.com/hermes"
choice (code-reviewer F-CR-4 confirms the REMOVE choice). No `claude.ai` URL
survives in any prompt-bearing file.

I also re-read the 25 INFO rows for any hidden WARNING pattern: every snippet
either names a *forbidden* behaviour in negative form or documents the
adapter contract that translates TO Anthropic shape for downstream
Hermes-only consumers. None of these is exploitable as a Claude prompt
trigger.

**Conclusion**: 0 R2 false-negative WARNING.

### R3 — False-positive NOTE downgrade

- **Findings: 0**

The 5 NOTE rows are SYNTH-N01..N05:

- N01 — upstream subtree silent (informational null-result)
- N02 — textual pin provenance (process observation)
- N03 — D5 installer-selection doc gap (documentation)
- N04 — missing `scripts/__init__.py` (vendoring)
- N05 — Common Pitfalls → Migration Notes structural question

None of these is a prompt-language residue claim. None is hiding an INFO
finding. They are correctly classified as NOTE (open for Phase 3 verdict
but not blockers). The only borderline row is N04 (missing `__init__.py`)
— but this is a structural vendoring question, not a Claude-prompt
question, so NOTE is correct.

**Conclusion**: 0 R3 false-positive NOTE downgrade.

### R4 — Dedup hiba

- **Findings: 0**

I cross-referenced the synthesis's 25 INFO rows against my own grep output
of all `anthropic|claude` lines in the local skill (27 raw lines). The 2
uncovered lines are:

1. `skills/skill-creator/scripts/run_eval.py:40` —
   `def _hermes_event_to_anthropic(event: dict) -> dict:` (function name)
2. `skills/skill-creator/scripts/run_eval.py:119-120` —
   `anthropic_events = [_hermes_event_to_anthropic(e) for e in events]`
   `results.append({"case": case, "events": anthropic_events})` (variable name)

Both are *internal Python identifiers* in the adapter function body — not
strings surfaced to any LLM. The synthesis correctly scoped INFO rows to
strings/docstrings/comments/test-names that the prompt-engineer lens
classifies as Claude-prompt-language. Internal symbol names are out of
prompt-language scope (they live in code, not in the LLM-callable prompt
layer). Including them in the synthesis INFO table would have been scope
creep, not a dedup bug.

Conversely, no two distinct logical items in the 30-row table were merged
under a single row. Each file:line is unique; each "logical item" is a
distinct line of docstring/comment/test-name.

**Conclusion**: 0 R4 dedup hiba. The 2 raw lines not surfaced are correctly
out of scope (internal symbol names), not dedup omissions.

### R5 — Severity drift

- **Findings: 0**

Every row in the synthesis's table has a single severity, with the `lenses`
column listing all Phase 1 agents that flagged it. No row shows different
severities from different lenses. Cross-check:

- prompt-engineer (F-PE-1..25) → all marked DELIBERATE → synthesis INFO
- code-reviewer (F-CR-1..16) → all marked OK / DOC-GAP → synthesis INFO / NOTE
- security-auditor (K1–K7) → all marked CONFIRMED-CLEAN → no severity
  conflict because the security-auditor's axis is *security*, not
  *prompt-language residue*
- researcher (F-R1..F-R4) → NOTE → synthesis NOTE

The security-auditor's "CONFIRMED-CLEAN" verdict (e.g. K3 over
`_subprocess.py`) is a different *classification axis* than the
prompt-engineer's "DELIBERATE INFO". Both are correct simultaneously: the
docstring is *not a security defect* (security-auditor's lens) AND is
*intentional bilingual advisory provenance* (prompt-engineer's lens). The
synthesis reconciles this in the reconciliation log.

**Conclusion**: 0 R5 severity drift. The "different axes, same conclusion"
case is correctly handled.

### R6 — Upstream-evidence hiány

- **Findings: 0**

Every INFO row's `upstream-evidence` column shows `n/a` because the local
SKILL.md is a **from-scratch Hermes rewrite**, not a patch of the vendored
upstream. The researcher's audit (F-R1) independently confirms this:

- Vendored `SKILL.md`: 33,168 B (Claude-prompt body)
- Local `SKILL.md`: 3,550 B (Hermes rewrite)
- Aggregate SHA-256 identical across 18 vendored files
- Zero commits between pin (`2a40fd2e`, 2026-04-23) and upstream main HEAD
  (`5fc2987a`, 2026-06-22)

The researcher's primary source (commit page) + 2 confirmations (blame view
+ tree view) cover the upstream-evidence at the *audit level*. The
*bilingual-advisory contract* (`hermes-skills-hitl-decisions.md` Q4/Q5)
covers the *policy level* that authorises the DELIBERATE classification for
the local-only strings. Both sources are present.

Per the Karpathy-validáció rule (CLAUDE.md §1: primary source + 2
confirmations), every claim that *requires* upstream-evidence has it (the
subtree-silence claim; the byte-equality claim). The local-only INFO rows
explicitly note "n/a — Hermes rewrite; no upstream analogue" which is the
correct evidence standard when there is *nothing upstream to compare to*.

**Conclusion**: 0 R6 upstream-evidence hiány.

### R7 — Coverage gap

- **Findings: 0**

Coverage matrix (synthesis §Coverage matrix, 14 rows × 4 lenses) is complete.
Cross-checked against prompt-engineer's "Files covered" list (16 files) +
code-reviewer's "prompt-layer files audited" list (14 files) + security-auditor's
K1–K7 scope (all prompt-bearing + Python helpers) + researcher's
"Files compared (18)" list:

- 18 vendored files: all covered by researcher's byte-equality check
- All prompt-bearing files (SKILL.md, SKILL.md.short, agents/*.md,
  scripts/*.py docstrings, _subprocess.py docstring) covered by all 4 lenses
- `eval-viewer/viewer.html`: covered by security-auditor K5 (SSRF/XSS check)
  and prompt-engineer (scanned, no findings) and code-reviewer (out of scope
  per plan, but T3.015 host-agnostic preserved unchanged)
- `scripts/__init__.py`: covered by prompt-engineer open-question-4 →
  SYNTH-N04 (vendoring observation)
- `references/schemas.md`, `assets/eval_review.html`, `LICENSE.txt`:
  correctly out-of-scope for the prompt-layer audit (no Claude-prompt
  language)

Every file the synthesis claims to cover actually got coverage from the lens
that is best suited to that file.

**Conclusion**: 0 R7 coverage gap.

### R8 — Reconciliation log hézag

- **Findings: 0**

I checked the synthesis's "Zero contradictions" claim against the Phase 1
agents' explicit cross-references:

1. **prompt-engineer open-question-1** (`_LEGACY_GUARD_VARS` rename) vs
   **security-auditor K5** (excluded from scope) — synthesis reconciles
   this in the reconciliation log paragraph 3 ("the prompt-engineer audit
   suggested... the security-auditor explicitly excluded... the synthesizer
   defers to the operator"). Also surfaced in synthesis open-questions item
   #5 ("Hygiene — `_LEGACY_GUARD_VARS` rename"). **Covered.**

2. **prompt-engineer open-question-2** (pipeline shape direction) vs
   code-reviewer (no opinion on shape direction; only on D4 adapter contract)
   — synthesis surfaces this in open-questions item #6. **Covered.**

3. **prompt-engineer open-question-3** (`<available_skills>` disambiguation)
   — synthesis surfaces this in open-questions item #7 (cross-link to
   hermes-agent-skill-authoring/SKILL.md). SYNTH-007, SYNTH-024, SYNTH-025
   note the disambiguation explicitly. **Covered.**

4. **prompt-engineer open-question-4** (missing `__init__.py`) — synthesis
   surfaces as SYNTH-N04 + open-questions item #3. **Covered.**

5. **security-auditor open-question-1** (re-audit on next sync) — synthesis
   surfaces as open-questions item #10. **Covered.**

6. **security-auditor open-question-2** (Migration Notes appendix) —
   synthesis surfaces as SYNTH-N05 + open-questions item #4. **Covered.**

7. **security-auditor open-question-3** (`_LEGACY_GUARD_VARS` expansion to
   `CLAUDE_CODE_ENTRYPOINT`) — synthesis surfaces as open-questions item #11.
   **Covered.**

8. **code-reviewer DOC-GAP-1** (D5 installer-selection doc) — synthesis
   surfaces as SYNTH-N03 + open-questions item #2. **Covered.**

9. **code-reviewer open-question-2** (T3.007 rewrite-vs-remove) — synthesis
   surfaces as open-questions item #8 + F-CR-4 verdict (REMOVE chosen).
   **Covered.**

10. **researcher open-question-3** (other Anthropic subtrees out of scope) —
    synthesis surfaces as open-questions item #9. **Covered.**

All 11 explicit reconciliation cross-references from the 4 Phase 1 agents
are surfaced in the synthesis open-questions list. The reconciliation log
itself documents "zero contradictions" with the rationale per axis.

**Conclusion**: 0 R8 reconciliation log hézag.

## Verdict

### PASS feltételei (mind kell)

- [x] **0 R1 / R2 finding** (nincs új CRITICAL/WARNING, ami a Phase 2-ben lemaradt) — confirmed via verbatim grep output above; `claude.ai`, "Anthropic recommends", "as Claude Code you must" all return zero hits.
- [x] **0 R4 / R5 dedup/severity hiba** — confirmed; the 2 raw `anthropic|claude` lines not surfaced in INFO are internal symbol names, correctly out of scope.
- [x] **Minden INFO sornak van upstream-evidence (R6) VAGY explicit "vendoring baseline" jegy** — confirmed; researcher F-R1/F-R2 cover upstream-evidence at the audit level; Q4/Q5 bilingual-advisory contract covers the policy authority for local-only strings.
- [x] **Coverage matrix teljes (R7)** — confirmed; all 14 prompt-bearing files covered by all 4 lenses; `__init__.py`, `eval-viewer/viewer.html`, vendored baseline correctly scoped.
- [x] **Reconciliation log minden felfedezett ellentmondást tartalmaz (R8)** — confirmed; all 11 cross-references from Phase 1 agents surfaced.

### Verdict

**PASS**

### Ha FAIL

- (n/a — verdict is PASS)

### Ha PASS

- A szintézis alkalmas a Phase 4 docs-scribe-re.
- Az 5 NOTE sorból melyikeket érdemes a MIGRATION.upstream-sync.md "How to use"
  szekciójába beemelni:
  - **SYNTH-N03** (D5 installer-selection doc) — yes; the operator using the
    skill needs to know the installer picks `SKILL.md` vs `SKILL.md.short`
    per the active cap; this belongs in the "How to use" section.
  - **SYNTH-N05** (Common Pitfalls → Migration Notes appendix) — yes as a
    forward-looking structural note; once the operator decides, the appendix
    becomes part of the skill's structure.
  - **SYNTH-N02** (textual pin provenance) — no, this is vendoring-process,
    not end-user-facing; belongs in vendoring notes, not in the user-facing
    migration doc.
  - **SYNTH-N04** (missing `__init__.py`) — no, this is operator-judgement
    only; do not pollute the user-facing migration doc with internal
    vendoring-process detail.
  - **SYNTH-N01** (subtree silent) — no, this is audit-log material; belongs
    in audit history, not in "How to use".

- Az audit artifact (= `upstream-audit-validated.md` végleges) összeállításához
  szükséges lépések:
  1. Wait for Phase 3 / Reviewer 2 (code-reviewer best-practice lens).
  2. If Reviewer 2 also returns PASS, merge the two reviewer reports
     (this one + Reviewer 2's) into `docs/research/upstream-audit-validated.md`
     as the canonical audit artefact.
  3. Carry the 11 open-questions from the synthesis into the validated
     document verbatim; mark each with the operator's verdict (CONFIRM /
     REMEDIATE / DEFER) once the operator responds.
  4. Reference this report and Reviewer 2's report by absolute path inside
     the validated doc so future audits have the audit trail.
  5. Phase 4 (docs-scribe) consumes the validated doc + the operator
     verdicts on the 11 open questions to produce `MIGRATION.upstream-sync.md`.

## Files

- **Input (read-only)**:
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-2026-06-22/synthesis.md`
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-2026-06-22/lenses/researcher.md`
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-2026-06-22/lenses/prompt-engineer.md`
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-2026-06-22/lenses/code-reviewer.md`
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-2026-06-22/lenses/security-auditor.md`
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/skills/skill-creator/SKILL.md` (ground-truth verification)
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/skills/skill-creator/_subprocess.py` (ground-truth verification)
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/skills/skill-creator/agents/grader.md` (ground-truth verification)
  - `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/skills/skill-creator/scripts/run_eval.py` (ground-truth verification)
- **Output (created)**: `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/agent-upstream-audit-2026-06-22/docs/research/upstream-audit-validated-r1.md` (this file)
