# Code-reviewer audit — 07 plan decisions in prompt layer

**Audit lens**: Phase 1 / Agent 3 (code-reviewer). Scope = consistency between
the 07 plan's D2/D5/D6/D7 decisions and the prompt-layer artefacts
(`SKILL.md` body, `SKILL.md.short`, `agents/*.md`, `scripts/*.py` docstrings,
`_subprocess.py` docstring). Out of scope = Python implementation (already
covered by code-modifying agents), vendored upstream diff (covered by
researcher), Claude-specific prompt-language residues (covered by
prompt-engineer).

## Plan source

- `docs/plans/07-skill-creator-migration.md` (D2, D5, D6, D7)
- `MIGRATION.skill-port.md` — T3 inventory (canonical, 18 rows)
- Local prompt-layer files audited:
  - `skills/skill-creator/SKILL.md` (75 lines)
  - `skills/skill-creator/SKILL.md.short` (12 lines)
  - `skills/skill-creator/agents/grader.md` (38 lines)
  - `skills/skill-creator/agents/analyzer.md` (38 lines)
  - `skills/skill-creator/agents/comparator.md` (36 lines)
  - `skills/skill-creator/scripts/run_eval.py` (168 lines)
  - `skills/skill-creator/scripts/improve_description.py` (85 lines)
  - `skills/skill-creator/scripts/run_loop.py` (75 lines)
  - `skills/skill-creator/scripts/aggregate_benchmark.py` (113 lines)
  - `skills/skill-creator/scripts/generate_report.py` (86 lines)
  - `skills/skill-creator/scripts/quick_validate.py` (146 lines)
  - `skills/skill-creator/scripts/package_skill.py` (56 lines)
  - `skills/skill-creator/scripts/utils.py` (29 lines)
  - `skills/skill-creator/_subprocess.py` (51 lines)

## Decision-by-decision review

### D2 — T3 inventory (18 rows) consistency

**T3 inventory rows mapped to prompt-layer:**

| T3 row | path | claude-binding | prompt-layer coverage |
| --- | --- | --- | --- |
| T3.001 | `scripts/improve_description.py` | `claude -p` | `scripts/improve_description.py:31` — `cmd = ["hermes", "-p", ...]` (replaced; docstring line 1 mentions "propose a new SKILL.md description", docstring lines 9-13 enumerate TDD tests, line 6 references "Hermes orchestrator"). REMOVED. |
| T3.002 | `scripts/improve_description.py` | env-strip block | `_subprocess.py:30` (`_LEGACY_GUARD_VARS` includes `CLAUDECODE`) + `_subprocess.py:33-47` (helper). REMOVED. |
| T3.003 | `scripts/run_eval.py` | `claude -p` invocation | `scripts/run_eval.py:66` — `cmd = ["hermes", "-p", ...]`. REMOVED. |
| T3.004 | `scripts/run_eval.py` | env-strip | `scripts/run_eval.py:74` — `env=hermes_subprocess_env()`. REMOVED. |
| T3.005 | `scripts/run_eval.py` | `.claude/commands/<target>.md` fabrication | `scripts/run_eval.py:82-92` — `_ensure_eval_target()` writes to `<hermes_home>/skills/<cat>/<target>/SKILL.md` (Hermes flat path; `.claude/commands` removed). The constant `EVAL_TARGET_TEMPLATE = "{hermes_home}/skills/{category}/{target}/SKILL.md"` at `scripts/run_eval.py:37` documents the new path. REMOVED. |
| T3.006 | `scripts/run_eval.py` | `--model claude-...` flag | `scripts/run_eval.py:144` — `--model` help text: "Hermes model id (or omit)". REMOVED. |
| T3.007 | `SKILL.md` | `claude.ai` URL reference | No `claude.ai` URL present in SKILL.md body (verified: `grep -nE "claude\.ai|claude\.com|anthropic\.com" skills/skill-creator/SKILL.md` → empty). The migration-note line is "nousresearch.com/hermes (or remove the URL)" — the URL was REMOVED, not rewritten. **Decision-or-marker**: SKILL.md body does NOT mention `nousresearch.com/hermes` either. |
| T3.008 | `SKILL.md` | `## Cowork-Specific Instructions` header | Section header absent in `SKILL.md` (verified: `grep -nE "Cowork" skills/skill-creator/SKILL.md` → empty). REMOVED. |
| T3.009 | `SKILL.md` | "If you're in Cowork, please specifically put..." TodoList fallback | Phrase absent in `SKILL.md`. REMOVED. |
| T3.010 | `SKILL.md` | `if not webbrowser.open(...)` Cowork browser auto-open | `grep -nE "webbrowser"` over all prompt-layer files → empty. REMOVED. |
| T3.011 | `scripts/run_eval.py` | event-shape translator (`if tool_name in ("Skill", "Read"):`) | `scripts/run_eval.py:40-57` — `_hermes_event_to_anthropic()` adapter; docstring at line 41: `"""Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011)."""`. REMOVED from upstream shape. |
| T3.012 | `agents/grader.md` | `# Grader Agent` (Anthropic subagent YAML) | `agents/grader.md:10` — `# Grader Subagent` (Hermes rewrite; uses `agent_name:` + `toolsets:` frontmatter, not Anthropic `name:`/`model:`). REMOVED. |
| T3.013 | `agents/analyzer.md` | `# Post-hoc Analyzer Agent` | `agents/analyzer.md:11` — `# Post-hoc Analyzer Subagent`. REMOVED. |
| T3.014 | `agents/comparator.md` | `# Blind Comparator Agent` | `agents/comparator.md:11` — `# Blind Comparator Subagent`. REMOVED. |
| T3.015 | `eval-viewer/generate_review.py` | host-agnostic; no Claude binding | Preserved unchanged (out of prompt-layer scope; not reviewed here). |
| T3.016 | `scripts/run_loop.py` | module docstring `claude -p` | `scripts/run_loop.py:3` — `"""Hermes-native port. Invokes the Hermes orchestrator (\`hermes -p\`);..."""`. REMOVED. |
| T3.017 | `scripts/run_loop.py` | other `claude`/`CLAUDECODE` invocations in loop body | `scripts/run_loop.py:10` docstring: `(T3.016 + T3.017 — Anthropic-binding removal — covered by tests/unit/test_skill_creator_frontmatter.py against this script)`. VERIFIED absent in loop body. |
| T3.018 | `scripts/improve_description.py` | `RuntimeError(f"claude -p exited {rc}\n…")` | `scripts/improve_description.py:40` — `raise RuntimeError(f"hermes -p exited {proc.returncode}\n{proc.stderr}")`. REMOVED. |

**Missing prompt-coverage for T3 rows:**

- None of the 18 rows is missing its binding replacement. Every binding is
  present in the form the migration requires. T3.007 was REMOVED rather than
  rewritten, which is one of the two options the plan allows ("nousresearch.com/hermes (or remove the URL)").

**Prompt-layer Claude mentions NOT in T3 inventory (T3-extension candidates):**

| file:line | snippet | T3 mapping |
| --- | --- | --- |
| `SKILL.md:23` | `The skill is the Hermes-native port of the Anthropic \`skill-creator\`` | Bilingual advisory / provenance — explicitly allowed by `bilingual-advisory contract` (Q4/Q5 in `hermes-skills-hitl-decisions.md`). |
| `SKILL.md:25` | `every Claude-specific invocation has been replaced with the Hermes equivalent per the T3 inventory (18 rows; see \`MIGRATION.skill-port.md\` for the per-binding table)` | Provenance / T3 cross-reference. |
| `SKILL.md:37` | `migrate a skill that was originally written for a non-Hermes host (e.g. Anthropic's skill format) to Hermes's tool-name and nesting-guard conventions` | "When to Use" bullet; bilingual advisory. |
| `SKILL.md:42` | `**Do NOT use Anthropic tool names.** Hermes tool names are lowercase:` | Negative-form guard rail (bilingual advisory contract). |
| `SKILL.md:52` | `**Do NOT call the Anthropic CLI for nested invocations.** Use the Hermes CLI for any nested call.` | Negative-form guard rail (D7 enforcement in body prose). |
| `SKILL.md:71` | `- [ ] No Anthropic-CLI invocations anywhere in \`scripts/\`.` | Verification-checklist guard rail (D7 enforcement). |
| `agents/grader.md:5` | `tool-name compliance, no Anthropic tool names, no \`claude -p\` invocations` | Rubric-axis guard rail. |
| `agents/grader.md:6` | `tool names, no \`claude -p\` invocations). Returns a structured grading dict.` | Same rubric-axis guard rail (continuation of line 5). |
| `agents/grader.md:36` | `- Never invoke \`claude -p\`; use \`hermes -p\` for any nested call.` | Negative-form guard rail. |
| `scripts/run_eval.py:1,6` | `Hermes-native port. The migration provenance ... in \`MIGRATION.skill-port.md\` (see docs/plans/07 §T3 inventory). The Hermes event-shape adapter is local; the rest of the pipeline consumes the Anthropic-shaped dict the adapter produces.` | Adapter-contract documentation (D4) — describes translation target, not Claude-prompt language. |
| `scripts/run_eval.py:41-47` | `"""Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011). Hermes shape: {"event": "...", "role": "...", "content": ...} Anthropic shape: {"type": "...", "message": {"content": [...]}} The adapter is the single point of translation; the rest of the pipeline sees only Anthropic-shaped dicts.` | Adapter-contract docstring (D4) — same rationale. |
| `scripts/run_eval.py:105` | `Returns a list of per-case result dicts with the Anthropic-shaped events translated by the adapter.` | Adapter-contract docstring (D4). |
| `scripts/aggregate_benchmark.py:25` | `"""Pull the score out of a list of Anthropic-shaped events.` | Adapter-consumer docstring (D4). |
| `scripts/run_loop.py:10` | `(T3.016 + T3.017 — Anthropic-binding removal — covered by tests/unit/test_skill_creator_frontmatter.py against this script)` | T3-provenance reference in test docstring. |
| `_subprocess.py:27,29,34,37-38,42` | `# Pin: the legacy Anthropic nesting-guard env var. ... is itself a Claude/Anthropic session (e.g. during Phase 5 eval)` + `"""Return os.environ minus the nesting-guard vars (Hermes + legacy Claude). ... Anthropic guard (\`CLAUDECODE\`) so a migrated \`hermes -p\` subprocess can run cleanly even when the parent process is itself a Claude/Anthropic session` | Bilingual advisory (legacy `CLAUDECODE` env-var explanation; D3). |
| `SKILL.md:56` | `A skill that fails frontmatter validation will not appear in the \`<available_skills>\` system-prompt index.` | `<available_skills>` is Hermes's convention (per `metadata.hermes` validator), not Claude's. |
| `scripts/improve_description.py:61,63` | `the <available_skills> system-prompt index` / `<available_skills> rendszerprompt-index szamara` | Same as above. |

**Classification of all 18 rows + prompt-layer mentions:** Every T3 binding
has been replaced in the form the plan enumerates. The Claude/Anthropic
mentions that remain in the prompt-layer are EITHER:

1. **T3 cross-references** (provenance pointing at `MIGRATION.skill-port.md`
   or naming the binding row, e.g. `agents/grader.md:5` rubric, `_subprocess.py`
   legacy var rationale) — DELIBERATE.
2. **Negative-form guard rails** (D6 + D7 enforcement in body prose,
   explicitly opposing Claude-CLI usage) — DELIBERATE.
3. **Adapter-contract docstrings** (D4 — the adapter translates FROM Hermes
   shape TO Anthropic shape so the rest of the pipeline is unchanged; the
   prose describes the contract) — DELIBERATE.

None of these are T3-extension "new residue" — they are all part of the
documented migration narrative (Q4/Q5 bilingual advisory contract).

**Verdict: OK** — Every T3 row's binding has been removed from the
prompt-layer; the Claude/Anthropic mentions that remain are all explicitly
allowed bilingual-advisory / provenance / adapter-contract / negative-form
guard-rail content.

### D5 — Two frontmatter variants

**Frontmatter description lengths (verified via Python regex parse):**

- `SKILL.md` description: **369 chars** (plan cap: ≤1024) — **PASS**
- `SKILL.md.short` description: **56 chars** (plan cap: ≤60) — **PASS**
  (description text: `Use when authoring/validating/evaluating a Hermes skill.`)

**Other fields consistent (verified):**

- `name`: both = `skill-creator` — consistent
- `version`: both = `0.1.0` — consistent
- `author`: both = `kiscsicska` — consistent
- `license`: both = `MIT` — consistent
- `metadata.hermes.tags`: both = `[authoring, validation, eval, migration]` — consistent
- `metadata.hermes.related_skills`: both = `[hermes-agent-skill-authoring]` — consistent

**Installer logic documented in prompt:**

- `SKILL.md:63-64` documents the active-cap check:
  `- [ ] Description length <= 60 (in \`SKILL.md.short\`) or <= 1024 (in \`SKILL.md\`) per the active cap.`
  The phrase "active cap" is the D5 installer's selector term (per 07 plan §D5). PASS — partial doc; the body explains WHAT the cap is but NOT HOW the installer selects (`SKILL.md` vs `SKILL.md.short`).

**Verdict: OK** (with one DOC-GAP observation; see findings table).

### D6 — `tool_name.lower() in (...)` matching

**Uppercase tool names in body (outside code fences):**

- None found. Verified via regex sweep across all prompt-layer files for
  `\b(Read|Write|Edit|Glob|Grep|Bash|Task|Skill|AskUserQuestion|WebSearch|WebFetch|TodoWrite)\b`
  (per 07 §TDD test `test_no_uppercase_tool_names_in_body_outside_fences`).
  Zero hits in body prose.

**Lowercase Hermes names enumerated in prompt:**

- `SKILL.md:42-46` enumerates 22 lowercase Hermes tool names:
  `read_file`, `write_file`, `patch`, `search_files`, `terminal`,
  `read_terminal`, `execute_code`, `skill_manage`, `skill_view`,
  `skills_list`, `delegate_task`, `mixture_of_agents`, `clarify`, `cronjob`,
  `todo`, `web_search`, `web_extract`, `vision_analyze`, `memory`,
  `process`, `session_search`, `send_message`.
- `agents/grader.md:7` enumerates 5 Hermes toolsets:
  `[read_file, search_files, terminal, skill_view, skill_manage]`.
- `agents/analyzer.md:8` and `agents/comparator.md:7` similarly enumerate
  lowercase toolset lists.
- Plan §TDD test `test_lowercase_tool_names_present` requires: `skill_manage`,
  `skill_view`, `skills_list`, `read_file`, `write_file`, `patch`,
  `search_files`, `terminal`, `delegate_task`, `clarify`, `web_search`,
  `web_extract`, `todo`, `cronjob`. All 14 required names are present in
  SKILL.md (verified via count = 8 unique lines; per-file enum list above).

**`tool_name.lower()` pattern taught:**

- `SKILL.md:47` — `Match case-insensitively with \`tool_name.lower() in (...)\`.`
- `SKILL.md:69` (verification checklist) — `Body uses \`tool_name.lower()\` when matching tool names.`
- `agents/grader.md:35` — `Tool names are lowercase. Match with \`tool_name.lower() in (...)\`.`
- `agents/analyzer.md:35` and `agents/comparator.md:34` — `Lowercase tool names only.`

**Verdict: OK** — D6 is enforced three times in the body (SKILL.md:42-47,
SKILL.md:69, agents/grader.md:35) and the lowercase Hermes name inventory
is comprehensive (22 names in SKILL.md, covering every required name from
the TDD test list).

### D7 — `hermes -p` vs `claude -p`

**`claude -p` mentions in prompt-layer (T3-excluded):**

- `agents/grader.md:6` — `tool names, no \`claude -p\` invocations). Returns a structured grading dict.` — rubric-axis guard rail (explicitly opposing Claude-CLI).
- `agents/grader.md:36` — `- Never invoke \`claude -p\`; use \`hermes -p\` for any nested call.` — negative-form guard rail (explicitly opposing Claude-CLI).

These two mentions are NEGATIVE-FORM guard rails (D7 enforcement in agent
body). They are required by the plan's "Common Pitfalls" pattern and the
grader's rubric axis `no \`claude -p\` invocations`.

**`hermes -p` mentions in prompt-layer (verified):**

- `SKILL.md:53` (implied via "Hermes CLI") — `Use the Hermes CLI for any nested call. The Hermes CLI matches Hermes's nesting-detection contract.` (mentions "Hermes CLI" but does not literally write `hermes -p`).
- `agents/grader.md:36` — `use \`hermes -p\` for any nested call.` — positive pairing.
- `scripts/run_eval.py:1` — `"""scripts/run_eval.py — invoke hermes -p per eval case.`
- `scripts/run_eval.py:61` — `"""Invoke \`hermes -p\` with the stripped env; return stdout.`
- `scripts/run_eval.py:78` — `raise RuntimeError(f"hermes -p exited {proc.returncode}\n{proc.stderr}")` (T3.018 replacement).
- `scripts/improve_description.py:40` — `raise RuntimeError(f"hermes -p exited {proc.returncode}\n{proc.stderr}")` (T3.018 replacement).
- `scripts/run_loop.py:3` — `Invokes the Hermes orchestrator (\`hermes -p\`);`
- `scripts/run_loop.py:41` — `raise RuntimeError(f"hermes -p exited {proc.returncode}\n{proc.stderr}")` (T3.018 replacement).
- `_subprocess.py:28,37` — bilingual advisory mentioning `hermes -p` as the canonical invocation.

**Verdict: OK** — The two `claude -p` mentions are documented negative-form
guard rails (D7 enforcement); they explicitly OPPOSE Claude-CLI usage. All
positive invocations are `hermes -p` or "Hermes CLI". No `claude -p`
invocation survives in the prompt-layer.

## Findings table

| id | decision | file:line | pattern | classification | proposed action |
| --- | --- | --- | --- | --- | --- |
| F-CR-1 | D2 | `SKILL.md:26-27` | T3 inventory is referenced by name and row count ("18 rows; see `MIGRATION.skill-port.md` for the per-binding table") — establishes the bridge between body and inventory | OK | keep as-is — single source of truth for the 18-row count |
| F-CR-2 | D2 | `SKILL.md:23,25,37,42,52,71`, `agents/grader.md:5,6,36` | Anthropic / Claude / `claude -p` mentions in body | OK (DELIBERATE bilingual advisory / negative-form guard rail / provenance) | keep as-is — required by Q4/Q5 contract |
| F-CR-3 | D2 | `agents/grader.md:5` | rubric axis names "Anthropic tool names" — grader uses this as a check name | OK (DELIBERATE) | keep as-is — the grader's rubric axis IS the migration rule; renaming would erase the audit trail |
| F-CR-4 | D2 | T3.007 | `claude.ai` URL removed (NOT rewritten to `nousresearch.com/hermes`) — per plan, "or remove" is one of two allowed options | OK (plan allows both) | keep as-is — the URL was a vendored cosmetic reference; removal is the cleaner option |
| F-CR-5 | D2 | T3.008-T3.010 | `Cowork` section + browser auto-open removed entirely | OK | keep as-is — Hermes has no Cowork surface |
| F-CR-6 | D5 | `SKILL.md:64` | "per the active cap" — single line in verification checklist documenting the cap-based selection | OK (partial doc) | optional: expand to a one-paragraph explanation of how the installer selects between the two variants (DOC-GAP-1) |
| F-CR-7 | D5 | `SKILL.md:63` | `Description length <= 60 (in \`SKILL.md.short\`) or <= 1024 (in \`SKILL.md\`)` | OK | keep as-is — already documents both caps |
| F-CR-8 | D5 | frontmatter description lengths | SKILL.md: 369 / 1024; SKILL.md.short: 56 / 60 | OK (within cap) | keep as-is |
| F-CR-9 | D6 | `SKILL.md:47`, `SKILL.md:69`, `agents/grader.md:35` | `tool_name.lower() in (...)` pattern taught in three places | OK | keep as-is |
| F-CR-10 | D6 | `SKILL.md:42-46` | 22 lowercase Hermes tool names enumerated | OK | keep as-is — covers all 14 required names from TDD test + 8 additional |
| F-CR-11 | D6 | body prose (all files) | zero uppercase tool names outside code fences | OK | keep as-is — satisfies `test_no_uppercase_tool_names_in_body_outside_fences` |
| F-CR-12 | D7 | `agents/grader.md:6,36` | two `claude -p` mentions | OK (DELIBERATE negative-form guard rail) | keep as-is — D7 enforcement; explicit opposition to Claude-CLI |
| F-CR-13 | D7 | `scripts/run_eval.py:66`, `scripts/improve_description.py:31`, `scripts/run_loop.py:29` | `hermes -p` invocation in code (NOT prompt-layer per se, but the docstring is part of prompt-layer audit) | OK | keep as-is — T3.001/T3.003/T3.016/T3.018 replacements |
| F-CR-14 | D7 | `scripts/run_eval.py:78`, `scripts/improve_description.py:40`, `scripts/run_loop.py:41` | `RuntimeError(f"hermes -p exited {rc}\n…")` — T3.018 replacement | OK | keep as-is |
| F-CR-15 | D7 | `scripts/run_loop.py:10` | T3-provenance reference: `(T3.016 + T3.017 — Anthropic-binding removal — covered by tests/unit/test_skill_creator_frontmatter.py against this script)` | OK (DELIBERATE) | keep as-is — explicit T3 row reference preserves audit trail |
| F-CR-16 | D7 | `_subprocess.py:28,34,37` | bilingual advisory mentioning `hermes -p` as the canonical invocation | OK | keep as-is — D7 enforcement in docstring |
| DOC-GAP-1 | D5 | `SKILL.md` (no line) | The plan's "installer logic" (selecting between `SKILL.md` and `SKILL.md.short` based on the active 60-char vs 1024-char cap) is NOT documented in the body. The verification checklist says "per the active cap" but does not explain HOW the installer selects. | DOC-GAP | optional: add one paragraph to the Overview or Common Pitfalls section explaining "The skill ships two frontmatter variants; the installer selects `SKILL.md.short` for the 60-char system-prompt-index cap and `SKILL.md` for the 1024-char `skill_view` body cap." Not a blocker — the plan documents this in D5 and the constant names (`SKILL.md.short` vs `SKILL.md`) are self-explanatory. |

## Summary by decision

| decision | verdict | blockers | optional |
| --- | --- | --- | --- |
| **D2** (T3 inventory, 18 rows) | OK | 0 | 0 |
| **D5** (two frontmatter variants) | OK | 0 | 1 (DOC-GAP-1) |
| **D6** (`tool_name.lower() in (...)` matching) | OK | 0 | 0 |
| **D7** (`hermes -p` vs `claude -p`) | OK | 0 | 0 |

**Overall: 4/4 decisions OK; 0 blockers; 1 optional DOC-GAP observation.**

The prompt-layer is plan-consistent across all four decisions. The 07 plan
enumerates 18 T3 bindings and every binding has been replaced or removed
in the form the plan allows. The frontmatter ships two variants at the
documented caps; the tool-name matching is taught and the lowercase Hermes
inventory is comprehensive; the `hermes -p` / `claude -p` separation is
enforced via negative-form guard rails rather than silent deletion.

## Open questions for Phase 2 synthesizer

1. **DOC-GAP-1 (D5 installer-selection doc)**: Should the SKILL.md body
   explain that the installer selects between `SKILL.md` and `SKILL.md.short`
   based on the active cap? Currently the verification checklist line
   "`Description length <= 60 (in \`SKILL.md.short\`) or <= 1024 (in
   \`SKILL.md\`) per the active cap.`" implies the two-variant scheme but
   does not state who selects. **Recommendation**: file as a separate
   documentation card (DOC-d5-active-cap); do NOT merge into this audit
   because the prompt-layer is already correct (the caps are met; the
   fields are consistent; the bilingual-advisory contract is preserved).
2. **T3.007 rewrite-vs-remove choice**: The plan allows both rewriting to
   `nousresearch.com/hermes` AND removing the URL entirely. The local
   skill chose REMOVE. Is this consistent with the bilingual-advisory
   contract (Q4/Q5)? **Recommendation**: confirm with the operator — the
   choice is plan-allowed; the auditor flags it for awareness, not for
   remediation.
3. **Negative-form guard rails**: `agents/grader.md:6,36` use the literal
   `claude -p` phrase in negative-form ("Never invoke `claude -p`"). The
   prompt-engineer audit (F-PE-5, F-PE-6) classified these as DELIBERATE.
   The code-reviewer audit concurs. **Recommendation**: no action — these
   are the canonical D7 enforcement pattern and removing them would
   weaken the rubric.
4. **Prompt-engineer cross-link**: The prompt-engineer audit
   (`prompt-engineer.md`) flagged 25 DELIBERATE findings
   (F-PE-1..25). This audit confirms those 25 are all plan-allowed
   (bilingual advisory + negative-form guard rails + adapter-contract
   docstrings + T3-provenance references). **Recommendation**: Phase 2
   synthesizer should merge the two lenses and confirm zero NEW-RESIDUE
   findings across both.
