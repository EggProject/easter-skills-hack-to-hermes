# Upstream audit — CANONICAL VALIDATED

<!-- VALIDATED, attempt #1 — coordinator-assembled from synthesized + validated-r1 + info-evaluation + validated-r2 -->

**Audit date**: 2026-06-22
**Audit scope**: Claude/Anthropic prompt residues only (NOT code, NOT tool-name bindings)
**Pin SHA (last audited)**: `5fc2987a44918a455ef7dc583b51f8faf875c3ed` (Anthropic `main` HEAD on `plugins/skill-creator/skills/skill-creator`)
**Previous pin**: `2a40fd2e7c52207aa903bd33fc4c65716126966e`
**Diff verdict**: byte-identical (aggregate SHA-256 `c471bde8ea02f12b9cc490d117e4fa93ac61ab0e79c6e623e5a2e09ff1c5dc39`); 0 upstream commits on subtree since 2026-04-23

## Verdict

- **CRITICAL: 0** — no Claude/Anthropic prompt residues that would alter downstream agent behavior
- **WARNING: 0** — no outdated or imprecise Claude-prompt content
- **INFO: 25** — all DELIBERATE under Q4/Q5 bilingual-advisory contract (bilingual provenance / negative-form guard rail / adapter-contract docstring / T3-provenance / test-name encoding)
- **NOTE: 5** — structural/process observations + 1 DOC-GAP; non-blocking
- **TOTAL: 30**

## Pipeline summary

| Phase | Agent | Input | Output | Verdict |
| --- | --- | --- | --- | --- |
| 1a | researcher | upstream GitHub fetch | `upstream-audit-researcher.md` | null result (byte-identical) |
| 1b | prompt-engineer | local skill prompt-bearing files | `upstream-audit-prompt-engineer.md` | 25 DELIBERATE, 0 RESIDUE |
| 1c | code-reviewer | 07 plan D2/D5/D6/D7 | `upstream-audit-code-reviewer.md` | 16 OK + 1 DOC-GAP |
| 1d | security-auditor | K1–K7 adversarial | `upstream-audit-security-auditor.md` | 0 REAL-RESIDUE + 7 CONFIRMED-CLEAN |
| 2 | architect (synth) | 4 Phase 1 MDs | `upstream-audit-synthesized.md` | 0 CRITICAL / 0 WARNING / 25 INFO / 5 NOTE |
| 3-R1 | security-auditor (refute) | synthesized MD | `upstream-audit-validated-r1.md` | PASS (0 R1–R8 finding) |
| 3.5 | prompt-engineer (INFO re-eval) | 25 INFO sor | `upstream-audit-info-evaluation.md` | 25/25 KEEP, 0 FIX |
| 3-R2 | code-reviewer (best-practice) | synthesized + r1 + info-eval | `upstream-audit-validated-r2.md` | PASS (0 BP1–BP6 finding) |
| 3.7 | docs-scribe (assembly) | 4 input MDs | **`upstream-audit-validated.md` (this file)** | — |

## Findings table (canonical, 30 rows)

| id | file:line | symbol/snippet | severity | lenses | classification | upstream-evidence | proposed-action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SYNTH-001 | `SKILL.md:42` | `- **Do NOT use Anthropic tool names.** Hermes tool names are lowercase:` | INFO | prompt-engineer F-PE-1; code-reviewer F-CR-2 (D7 enforcement) | DELIBERATE — negative-form guard rail (bilingual advisory contract Q4/Q5) | n/a (Hermes rewrite; no upstream analogue for this bullet) | **keep as-is** |
| SYNTH-002 | `SKILL.md:52` | `- **Do NOT call the Anthropic CLI for nested invocations.** Use the Hermes` | INFO | prompt-engineer F-PE-2; code-reviewer F-CR-2 (D7 enforcement) | DELIBERATE — negative-form guard rail | n/a | **keep as-is** |
| SYNTH-003 | `SKILL.md:71` | `- [ ] No Anthropic-CLI invocations anywhere in \`scripts/\`.` | INFO | prompt-engineer F-PE-3; code-reviewer F-CR-2 | DELIBERATE — verification-checklist guard rail | n/a | **keep as-is** |
| SYNTH-004 | `SKILL.md:23` | `The skill is the Hermes-native port of the Anthropic \`skill-creator\`` | INFO | prompt-engineer F-PE-23; code-reviewer F-CR-2 | DELIBERATE — bilingual advisory / provenance statement (Q4/Q5) | n/a | **keep as-is** |
| SYNTH-005 | `SKILL.md:25` | `every Claude-specific invocation has been replaced with the Hermes equivalent per the T3 inventory` | INFO | prompt-engineer F-PE-24; code-reviewer F-CR-2 | DELIBERATE — migration provenance | n/a | **keep as-is** |
| SYNTH-006 | `SKILL.md:37` | `migrate a skill that was originally written for a non-Hermes host (e.g. Anthropic's skill format)` | INFO | prompt-engineer F-PE-25; code-reviewer F-CR-2 | DELIBERATE — bilingual advisory / "When to Use" bullet | n/a | **keep as-is** |
| SYNTH-007 | `SKILL.md:56` | `will not appear in the \`<available_skills>\` system-prompt index.` | INFO | prompt-engineer F-PE-20; code-reviewer F-CR-2 (note: `<available_skills>` is Hermes's convention per `metadata.hermes` validator, NOT Claude's `available_skills`) | DELIBERATE — Hermes convention reference | n/a | **keep as-is** |
| SYNTH-008 | `agents/grader.md:5` | `tool-name compliance, no Anthropic tool names, no \`claude -p\` invocations` | INFO | prompt-engineer F-PE-4; code-reviewer F-CR-2, F-CR-3 (rubric axis) | DELIBERATE — rubric-axis guard rail; grader's rubric IS the migration rule | n/a | **keep as-is** |
| SYNTH-009 | `agents/grader.md:6` | `tool names, no \`claude -p\` invocations). Returns a structured grading dict.` | INFO | prompt-engineer F-PE-5; code-reviewer F-CR-12 (D7); security-auditor K2 (counter-rule) | DELIBERATE — negative-form guard rail (D7 enforcement in agent body) | n/a | **keep as-is** |
| SYNTH-010 | `agents/grader.md:36` | `- Never invoke \`claude -p\`; use \`hermes -p\` for any nested call.` | INFO | prompt-engineer F-PE-6; code-reviewer F-CR-12 (D7); security-auditor K2 (counter-rule) | DELIBERATE — negative-form guard rail (D7 enforcement) | n/a | **keep as-is** |
| SYNTH-011 | `scripts/run_eval.py:6` | `pipeline consumes the Anthropic-shaped dict the adapter produces.` | INFO | prompt-engineer F-PE-7; code-reviewer F-CR-2 (D4 adapter-contract) | DELIBERATE — adapter-contract docstring (T3.011) | n/a (adapter function `_hermes_event_to_anthropic` is local-only) | **keep as-is** |
| SYNTH-012 | `scripts/run_eval.py:41` | `"""Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011).` | INFO | prompt-engineer F-PE-8; code-reviewer F-CR-2 (D4); security-auditor FP-1 (exonerated) | DELIBERATE — adapter-contract docstring (T3.011) | n/a | **keep as-is** |
| SYNTH-013 | `scripts/run_eval.py:44` | `Anthropic shape:  {"type": "...", "message": {"content": [...]}}` | INFO | prompt-engineer F-PE-9; code-reviewer F-CR-2 (D4); security-auditor FP-1 (exonerated) | DELIBERATE — adapter-contract shape spec | n/a | **keep as-is** |
| SYNTH-014 | `scripts/run_eval.py:47` | `sees only Anthropic-shaped dicts.` | INFO | prompt-engineer F-PE-10; code-reviewer F-CR-2 (D4) | DELIBERATE — adapter-contract docstring | n/a | **keep as-is** |
| SYNTH-015 | `scripts/run_eval.py:105` | `Returns a list of per-case result dicts with the Anthropic-shaped events` | INFO | prompt-engineer F-PE-11; code-reviewer F-CR-2 (D4) | DELIBERATE — adapter-consumer docstring | n/a | **keep as-is** |
| SYNTH-016 | `scripts/aggregate_benchmark.py:25` | `"""Pull the score out of a list of Anthropic-shaped events.` | INFO | prompt-engineer F-PE-12; code-reviewer F-CR-2 (D4) | DELIBERATE — adapter-consumer docstring | n/a | **keep as-is** |
| SYNTH-017 | `scripts/run_loop.py:10` | `(T3.016 + T3.017 — Anthropic-binding removal — covered by` | INFO | prompt-engineer F-PE-13; code-reviewer F-CR-15 (T3-provenance); security-auditor FP-2 (exonerated) | DELIBERATE — T3-provenance reference in test docstring (audit trail) | n/a | **keep as-is** |
| SYNTH-018 | `_subprocess.py:27` | `# Pin: the legacy Anthropic nesting-guard env var. Must also be stripped so` | INFO | prompt-engineer F-PE-14; security-auditor K3 (bilingual advisory explanation); cross-ref `docs/plans/12-risks-and-open-questions.md` Q1 | DELIBERATE — bilingual advisory (legacy `CLAUDECODE` env-var explanation) | n/a | **keep as-is** |
| SYNTH-019 | `_subprocess.py:29` | `# is itself a Claude/Anthropic session (e.g. during Phase 5 eval).` | INFO | prompt-engineer F-PE-15; security-auditor K3 | DELIBERATE — bilingual advisory (legacy var explanation) | n/a | **keep as-is** |
| SYNTH-020 | `_subprocess.py:34` | `"""Return os.environ minus the nesting-guard vars (Hermes + legacy Claude).` | INFO | prompt-engineer F-PE-16; security-auditor K5 (docstring of STRIDE-audited helper) | DELIBERATE — bilingual advisory (docstring) | n/a | **keep as-is** |
| SYNTH-021 | `_subprocess.py:37-38` | `Anthropic guard (\`CLAUDECODE\`) so a migrated \`hermes -p\` subprocess can / run cleanly even when the parent process is itself a Claude/Anthropic` | INFO | prompt-engineer F-PE-17; security-auditor K3, K5 | DELIBERATE — bilingual advisory (docstring) | n/a | **keep as-is** |
| SYNTH-022 | `scripts/run_eval.py:14` | `test_run_eval_writes_skill_md_to_hermes_home_not_dot_claude` | INFO | prompt-engineer F-PE-18 | DELIBERATE — test-name provenance encoding (audit trail) | n/a | **keep as-is** — test ID encodes the migration rule |
| SYNTH-023 | `_subprocess.py:12` | `test_hermes_subprocess_env_strips_claudecode` | INFO | prompt-engineer F-PE-19 | DELIBERATE — test-name provenance encoding (audit trail) | n/a | **keep as-is** — test ID encodes the migration rule |
| SYNTH-024 | `scripts/improve_description.py:61` | `"skill's description for the <available_skills> system-prompt index.\n"` | INFO | prompt-engineer F-PE-21 | DELIBERATE — Hermes convention reference | n/a | **keep as-is** |
| SYNTH-025 | `scripts/improve_description.py:63` | `"leirasat a <available_skills> rendszerprompt-index szamara."` | INFO | prompt-engineer F-PE-22 | DELIBERATE — Hungarian bilingual advisory (Hermes convention) | n/a | **keep as-is** |
| SYNTH-N01 | (all 18 vendored files; metadata) | Upstream subtree silent since pin: zero commits between `2a40fd2e` (2026-04-23) and `5fc2987a` (2026-06-22). Aggregate SHA-256 identical at both SHAs. `diff -rq` exit 0. Per-file SHA-256 diff empty. | NOTE | researcher F-R1 + F-R2 + F-R4 | DELIBERATE — null-result confirmation; rules out new upstream drift | `git log --format='%H %ai %s' -- plugins/skill-creator/skills/skill-creator/` returns only the 3 pre-pin commits | **keep as-is** — no action; re-audit on next upstream sync |
| SYNTH-N02 | `docs/research/anthropic-skill-creator-original/UPSTREAM_COMMIT.txt` | Single-line file containing `2a40fd2e7c52207aa903bd33fc4c65716126966e` | NOTE | researcher F-R3 | Vendoring-process observation: pin is *textual*, not *structural*. The upstream repo object `2a40fd2e...` is NOT reachable from the local vendored repo (`git show 2a40fd2e...` → `fatal: bad object`). Pin is treated as authoritative external reference, not as a local git object. | n/a (provenance gap, not a content diff) | Phase 3 verdict — replace with git submodule OR keep textual pin with documented re-sparse-fetch protocol |
| SYNTH-N03 | `SKILL.md` (no specific line — Overview / Common Pitfalls section) | The plan's "installer logic" (selecting between `SKILL.md` and `SKILL.md.short` based on the active 60-char vs 1024-char cap) is NOT documented in the body. The verification checklist line "per the active cap" implies the two-variant scheme but does not state WHO selects. | NOTE | code-reviewer DOC-GAP-1 (D5) | DOC-GAP — plan-allowed (caps met; fields consistent); body could optionally expand with one paragraph explaining the installer-selection contract | n/a (plan D5 source: `docs/plans/07-skill-creator-migration.md`) | Phase 3 verdict — open as separate DOC-d5-active-cap card; NOT a blocker |
| SYNTH-N04 | `scripts/__init__.py` (vendored has it; local does not) | Vendored pin has `scripts/__init__.py`; local skill does NOT. Not a prompt-language issue. | NOTE | prompt-engineer open question 4 | Vendoring-process observation: possible deliberate (Hermes doesn't need it) OR accidental (migrator dropped it). Requires operator judgement. | vendored pin has it; local copy does not | Phase 3 verdict — operator to confirm intent; if deliberate, document WHY in vendoring notes; if accidental, restore |
| SYNTH-N05 | (structural / cross-cut) | Whether to move SKILL.md's bilingual-advisory negatives into a separate `## Migration Notes` appendix (currently they live in `## Common Pitfalls` block, lines 40-58). Functionally identical; structural question. | NOTE | security-auditor open question 2 | Structural — would let the `hermes-agent-skill-authoring` validator enforce a stricter "no negative-form rules in body" rule if desired. Not a residue. | n/a | Phase 3 verdict — operator to decide; no functional impact today |

## Reconciliation log

**Zero contradictions across all 4 Phase 1 lenses.**

Every Phase 1 agent converged on the null hypothesis for new Claude/Anthropic
prompt residues. Specifically:

- **researcher** (F-R1, F-R2): upstream subtree is byte-identical at the pin
  and at upstream main HEAD. There is no new drift to audit.
- **prompt-engineer** (F-PE-1..25): all 25 Claude/Anthropic mentions in the
  local skill fall into benign buckets (negative-form guard rails, adapter
  contract documentation, test-name provenance, bilingual advisory
  statements). All classified DELIBERATE per Q4/Q5.
- **code-reviewer** (F-CR-1..16): every T3 inventory row has been replaced or
  removed in the form the plan allows; all four plan decisions (D2/D5/D6/D7)
  are OK; one optional DOC-GAP observation (DOC-GAP-1).
- **security-auditor** (K1–K7): 0 REAL-RESIDUE; 7 CONFIRMED-CLEAN categories;
  2 FALSE-POSITIVEs exonerated on closer read (FP-1 and FP-2 are docstring
  metadata never sent to any LLM, confirmed DELIBERATE per Q4/Q5).

The two lenses that overlap most heavily (prompt-engineer and code-reviewer)
both classify the same `<available_skills>` references, `claude -p`
counter-rules, and adapter-contract docstrings as DELIBERATE — no
contradiction.

The security-auditor's K5 STRIDE audit independently confirms the
`_subprocess.py` env-strip helper is the controlled, documented behaviour
that allows `hermes -p` subprocesses to run cleanly under a parent
`HERMES_SESSION` (and also strips the legacy `CLAUDECODE` for backwards
compatibility). The "Information disclosure (medium)" residual is inherited
from the caller's env-passing policy, not a defect of this helper — out of
scope for the skill-level audit.

The only minor lens-divergence worth noting: the prompt-engineer audit
suggested `_LEGACY_GUARD_VARS` could be renamed to `_LEGACY_ANTHROPIC_GUARD_VAR`
as a hygiene improvement (so the symbol itself doesn't carry Claude-prompt
language). The security-auditor explicitly excluded this from scope. The
synthesizer defers to the operator (Phase 3 verdict) rather than picking a
side — both positions are defensible.

## Reviewer 1 (security-auditor refuting) verdict

- R1 (false-negative CRITICAL): 0 finding
- R2 (false-negative WARNING): 0 finding
- R3 (false-positive NOTE downgrade): 0 finding
- R4 (dedup hiba): 0 finding
- R5 (severity drift): 0 finding
- R6 (upstream-evidence hiány): 0 finding
- R7 (coverage gap): 0 finding
- R8 (reconciliation log hézag): 0 finding
- **Verdict: PASS** (artifact: `upstream-audit-validated-r1.md`)

## Reviewer 2 (code-reviewer best-practice) verdict

- BP1 (URL validity): 0 finding (8 URLs inspected, all valid; SHAs verified)
- BP2 (D2/D5/D6/D7 severity consistency): 0 finding
- BP3 (file:line accuracy): 0 finding (25 INFO citations verified verbatim)
- BP4 (Phase 3.5 KEEP validation): 0 finding (5/5 spot-checks hold)
- BP5 (coverage matrix): 0 finding (14 files covered, out-of-scope correctly scoped)
- BP6 (reconciliation + open questions): 0 finding
- **Verdict: PASS** (artifact: `upstream-audit-validated-r2.md`)

## Phase 3.5 (INFO re-evaluation) verdict

- KEEP: 25 / FIX: 0 / TOTAL: 25
- Minden INFO sor DELIBERATE bilingual advisory / negative-form guard / adapter-contract / T3-provenance / test-name encoding
- **Verdict: no fixes needed** (artifact: `upstream-audit-info-evaluation.md`)

## Open questions for Phase 4 docs-scribe / Phase 5 GitHub issue

1. **SYNTH-N02 (pin provenance)**: Should `UPSTREAM_COMMIT.txt` be replaced
   with a git submodule pointing at `anthropics/claude-plugins-official`
   pinned to `2a40fd2e...`, so the pin is *structural* not *textual*?
   (researcher F-R3 — tooling choice; current textual pin + re-sparse-fetch
   protocol is functional.)

2. **SYNTH-N03 (D5 installer-selection doc)**: Should the SKILL.md body
   explain that the installer selects between `SKILL.md` and `SKILL.md.short`
   based on the active cap? Currently the verification checklist implies it
   but doesn't state who selects. (code-reviewer DOC-GAP-1; not a blocker.)

3. **SYNTH-N04 (scripts/__init__.py missing)**: Is the absence of
   `scripts/__init__.py` in the local skill deliberate (Hermes doesn't need
   it) or accidental (migrator dropped it)? (prompt-engineer open question 4.)

4. **SYNTH-N05 (Common Pitfalls → Migration Notes appendix)**: Should the
   bilingual-advisory negatives move into a separate `## Migration Notes`
   appendix? Functionally identical; structural. (security-auditor open
   question 2.)

5. **Hygiene — `_LEGACY_GUARD_VARS` rename**: Should the constant rename
   `CLAUDECODE` to a Hermes-neutral term (e.g. `_LEGACY_ANTHROPIC_GUARD_VAR`)
   so the symbol itself doesn't carry Claude-prompt language? Both positions
   are defensible; defer to operator. (prompt-engineer open question 1.)

6. **Hygiene — pipeline shape direction**: Should `scripts/run_eval.py` emit
   Hermes-shape downstream, instead of translating TO the legacy Anthropic
   shape and forcing every consumer (`aggregate_benchmark.py:25`,
   `generate_report.py`) to reference "Anthropic-shaped dicts"? The adapter
   works correctly today; this is a future-cleanup question. (prompt-engineer
   open question 2.)

7. **Cross-link — `<available_skills>` convention**: A reviewer who is not
   aware of the Hermes `metadata.hermes` validator might mis-flag the three
   `<available_skills>` references (SYNTH-007, SYNTH-024, SYNTH-025) as
   Claude residues. Should SKILL.md add a one-line cross-link explaining
   that the validator injects validated skills into the `<available_skills>`
   block — pointing at `hermes-agent-skill-authoring/SKILL.md`? (prompt-engineer
   open question 3; structural disambiguation.)

8. **T3.007 (URL rewrite-vs-remove)**: The plan allows BOTH rewriting the
   `claude.ai` URL to `nousresearch.com/hermes` AND removing it entirely.
   The local skill chose REMOVE. Is this consistent with the bilingual-advisory
   contract (Q4/Q5)? (code-reviewer open question 2; plan-allowed either way.)

9. **Other Anthropic subtrees not in scope**: the upstream repo also
   contains `plugins/feature-dev/`, `plugins/frontend-design/`, etc. If a
   broader Claude-prompt residue survey is wanted, those need their own
   researcher passes. (researcher open question 3; out of scope for this
   audit.)

10. **Re-audit on next upstream sync**: agent 1 confirmed the upstream
    subtree has been silent since the pin. If/when upstream lands a new
    skill-creator commit, the K1–K7 matrix (security-auditor) should be
    re-run before merge. (security-auditor open question 1; the K1–K7
    matrix is the regression-test scaffold.)

11. **Future `_LEGACY_GUARD_VARS` expansion**: Should the frozenset also
    strip `CLAUDE_CODE_ENTRYPOINT` or other newer Anthropic env vars?
    Out of scope for this audit (K5 security-auditor scope); flagged for
    Phase 6 (devops-releaser). (security-auditor open question 3.)

## Coverage matrix

| file | researcher | prompt-engineer | code-reviewer | security-auditor |
| --- | --- | --- | --- | --- |
| `SKILL.md` | (covered by upstream byte-identical diff) | F-PE-1,2,3,20,23,24,25 → SYNTH-001..007 | F-CR-1,2,7,9,10,11 + DOC-GAP-1 → SYNTH-007, SYNTH-N03 | K1–K7 + K6 — all CONFIRMED-CLEAN |
| `SKILL.md.short` | (covered by upstream byte-identical diff) | (scanned, no findings) | F-CR-8 — OK (description length 56/60) | K6-1 — CONFIRMED-CLEAN |
| `agents/grader.md` | (covered by upstream byte-identical diff) | F-PE-4,5,6 → SYNTH-008..010 | F-CR-2,3,9,12 — OK | K2 (counter-rule) — CONFIRMED-CLEAN |
| `agents/analyzer.md` | (covered by upstream byte-identical diff) | (scanned, no findings) | F-CR-9 — OK | K3 — CONFIRMED-CLEAN |
| `agents/comparator.md` | (covered by upstream byte-identical diff) | (scanned, no findings) | F-CR-9 — OK | K3 — CONFIRMED-CLEAN |
| `eval-viewer/viewer.html` | (out of scope — static viewer) | (scanned, no findings) | (out of scope per plan) | K5 — SSRF/XSS check clean (relative `fetch('feedback.json')`) |
| `eval-viewer/generate_review.py` | (out of scope — static-asset generator) | (scanned, no findings) | T3.015 host-agnostic — preserved unchanged | K5 — clean |
| `scripts/*.py` (8 files) | (out of scope — Python implementation) | F-PE-7..19,21,22 → SYNTH-011..017,022,024,025 | F-CR-13..16 — OK | K4 (system-prompt docstrings) — CONFIRMED-CLEAN |
| `_subprocess.py` | (out of scope — Python implementation) | F-PE-14..17,19 → SYNTH-018..021,023 | F-CR-16 — OK | K5 — STRIDE audit CONFIRMED-CLEAN |
| `scripts/__init__.py` | (out of scope — Python) | open question 4 → SYNTH-N04 (vendored has it; local does not) | (out of scope per plan) | (out of scope per K4) |
| `references/schemas.md` | (out of scope — schema docs) | (out of scope — not a prompt file) | (out of scope per plan) | (out of scope per K4) |
| `assets/eval_review.html` | (out of scope — eval-form template) | (out of scope — not present locally) | (out of scope per plan) | (out of scope per K4) |
| `LICENSE.txt` | (out of scope — license text, legal question) | (out of scope — not a prompt file) | (out of scope per plan) | (out of scope per K4) |
| `docs/research/anthropic-skill-creator-original/UPSTREAM_COMMIT.txt` | F-R3 → SYNTH-N02 (textual pin provenance) | (not a prompt file) | (not a prompt file) | (not a prompt file) |

## Recommendation to Phase 4 (docs-scribe)

A `MIGRATION.upstream-sync.md` legyen DESCRIPTION-ONLY a 07-es tervvel összhangban:
- NE frissítse a `skills/skill-creator/*` tartalmát
- NE bumpolja a `MIGRATION.md` pin mezőjét (operator policy)
- A pin mező (`Pinned upstream commit (last audited)`) legyen az új SHA: `5fc2987a...`
- A "Previous pin" mező: `2a40fd2e...`
- A "Headline" szekció: "0 CRITICAL, 0 WARNING, 25 INFO, 5 NOTE — upstream subtree silent since pin"
- A "Per-residue changes (would-apply, NOT applied)" táblázat: 0 sor (nincs új reziduum)
- A "Reconciliation against previous MIGRATION set" szekció: a `MIGRATION.md` pin mezője CSAK operator-döntés után bumpolódik
- A "How to use on next upstream sync" szekció: a 11 nyitott kérdésből összeállítva (operatori judgement itemenként)

## Files

- Input (read-only):
  - `docs/research/upstream-audit-synthesized.md`
  - `docs/research/upstream-audit-validated-r1.md`
  - `docs/research/upstream-audit-info-evaluation.md`
  - `docs/research/upstream-audit-validated-r2.md`
- Output (this file): `docs/research/upstream-audit-validated.md`
- Downstream consumer: Phase 4 docs-scribe → `MIGRATION.upstream-sync.md`
