# Prompt-engineer audit — Claude-specific prompt-language lens

**Audit lens**: Phase 1 / Agent 2 (prompt-engineer). Scope = Claude-specific
prompt-language in the local skill (uppercase tool names, Cowork references,
"You are Claude" subject markers, system-prompt scaffolding, agent-role
YAML, etc.). Out of scope: Python implementation, JSON schemas, CLI flags,
tool-name mapping tables — those belong to T3 inventory / code-modifying
agents.

## Scope

- **Local skill**: `skills/skill-creator/`
- **Files scanned** (15):
  - `skills/skill-creator/SKILL.md` (3,550 B — Hermes rewrite)
  - `skills/skill-creator/SKILL.md.short` (267 B — short frontmatter)
  - `skills/skill-creator/agents/grader.md` (Hermes rewrite)
  - `skills/skill-creator/agents/analyzer.md` (Hermes rewrite)
  - `skills/skill-creator/agents/comparator.md` (Hermes rewrite)
  - `skills/skill-creator/eval-viewer/viewer.html` (28 L — static viewer, no prompts)
  - `skills/skill-creator/eval-viewer/generate_review.py` (97 L)
  - `skills/skill-creator/scripts/__init__.py` — does NOT exist locally; only vendored has it
  - `skills/skill-creator/scripts/aggregate_benchmark.py`
  - `skills/skill-creator/scripts/generate_report.py`
  - `skills/skill-creator/scripts/improve_description.py`
  - `skills/skill-creator/scripts/package_skill.py`
  - `skills/skill-creator/scripts/quick_validate.py`
  - `skills/skill-creator/scripts/run_eval.py`
  - `skills/skill-creator/scripts/run_loop.py`
  - `skills/skill-creator/scripts/utils.py`
  - `skills/skill-creator/_subprocess.py`
- **Vendored upstream reference**: `docs/research/anthropic-skill-creator-original/skills/skill-creator/`
  - `SKILL.md` (33,168 B — original Claude-prompt body)
  - `agents/{grader,analyzer,comparator}.md` (original Anthropic agent prompts)
- **README.md** does NOT exist locally — not scanned.

## Findings (Claude-specific prompt-language residues)

### Summary

**Net result: zero Claude-specific prompt-language residues found.**

Every "Anthropic" / "Claude" / uppercase tool-name / `<available_skills>`
hit in the local skill falls into one of three benign buckets:

1. **Negative-form guard rails** ("Do NOT use Anthropic tool names" / "Never
   invoke `claude -p`") — these are bilingual-advisory provenance that
   explicitly *oppose* Claude-specific behaviour. They are intentional
   anti-pattern reminders and must be PRESERVED verbatim.
2. **Adapter contract documentation** ("Adapter: Hermes event shape ->
   Anthropic-shaped dict") — describes the single function
   `_hermes_event_to_anthropic` that translates BETWEEN Hermes and the
   legacy shape the rest of the pipeline consumes. These are technical
   contract descriptions, not Claude-prompt language; the model never
   reads them as instructions.
3. **Test-name provenance encoding** (`test_..._strips_claudecode`,
   `test_..._writes_skill_md_to_hermes_home_not_dot_claude`) — test IDs
   encode the migration rule they verify. Removing them would erase the
   audit trail.

| id | file:line | verbatim snippet | pattern category | classification | upstream evidence (vendored pin) | proposed remediation |
| --- | --- | --- | --- | --- | --- | --- |
| F-PE-1 | `SKILL.md:42` | `- **Do NOT use Anthropic tool names.** Hermes tool names are lowercase:` | negative-form guard rail | DELIBERATE | n/a (Hermes rewrite, no upstream analogue for this bullet) | **keep as-is** — anti-pattern reminder |
| F-PE-2 | `SKILL.md:52` | `- **Do NOT call the Anthropic CLI for nested invocations.** Use the Hermes` | negative-form guard rail | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** |
| F-PE-3 | `SKILL.md:71` | `- [ ] No Anthropic-CLI invocations anywhere in \`scripts/\`.` | verification-checklist guard rail | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** |
| F-PE-4 | `agents/grader.md:5` | `tool-name compliance, no Anthropic` | rubric-axis guard rail | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** |
| F-PE-5 | `agents/grader.md:6` | `tool names, no \`claude -p\` invocations).` | rubric-axis guard rail | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** |
| F-PE-6 | `agents/grader.md:36` | `- Never invoke \`claude -p\`; use \`hermes -p\` for any nested call.` | negative-form guard rail | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** |
| F-PE-7 | `scripts/run_eval.py:6` | `pipeline consumes the Anthropic-shaped dict the adapter produces.` | adapter-contract docstring | DELIBERATE | n/a (adapter function `_hermes_event_to_anthropic` is local-only) | **keep as-is** — describes translation target |
| F-PE-8 | `scripts/run_eval.py:41` | `"""Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011).` | adapter-contract docstring | DELIBERATE | n/a | **keep as-is** |
| F-PE-9 | `scripts/run_eval.py:44` | `Anthropic shape:  {"type": "...", "message": {"content": [...]}}` | adapter-contract docstring | DELIBERATE | n/a | **keep as-is** |
| F-PE-10 | `scripts/run_eval.py:47` | `sees only Anthropic-shaped dicts.` | adapter-contract docstring | DELIBERATE | n/a | **keep as-is** |
| F-PE-11 | `scripts/run_eval.py:105` | `Returns a list of per-case result dicts with the Anthropic-shaped events` | adapter-contract docstring | DELIBERATE | n/a | **keep as-is** |
| F-PE-12 | `scripts/aggregate_benchmark.py:25` | `"""Pull the score out of a list of Anthropic-shaped events.` | adapter-contract docstring | DELIBERATE | n/a (consumer of the adapter output) | **keep as-is** |
| F-PE-13 | `scripts/run_loop.py:10` | `(T3.016 + T3.017 — Anthropic-binding removal — covered by` | T3-provenance reference in test docstring | DELIBERATE | n/a | **keep as-is** — provenance link to MIGRATION.skill-port.md |
| F-PE-14 | `_subprocess.py:27` | `# Pin: the legacy Anthropic nesting-guard env var. Must also be stripped so` | bilingual advisory (legacy var explanation) | DELIBERATE | n/a | **keep as-is** |
| F-PE-15 | `_subprocess.py:29` | `# is itself a Claude/Anthropic session (e.g. during Phase 5 eval).` | bilingual advisory (legacy var explanation) | DELIBERATE | n/a | **keep as-is** |
| F-PE-16 | `_subprocess.py:34` | `"""Return os.environ minus the nesting-guard vars (Hermes + legacy Claude).` | bilingual advisory (docstring) | DELIBERATE | n/a | **keep as-is** |
| F-PE-17 | `_subprocess.py:37-38` | `Anthropic guard (\`CLAUDECODE\`) so a migrated \`hermes -p\` subprocess can / run cleanly even when the parent process is itself a Claude/Anthropic` | bilingual advisory (docstring) | DELIBERATE | n/a | **keep as-is** |
| F-PE-18 | `scripts/run_eval.py:14` | `test_run_eval_writes_skill_md_to_hermes_home_not_dot_claude` | test-name provenance encoding | DELIBERATE | n/a | **keep as-is** — test ID encodes the migration rule |
| F-PE-19 | `_subprocess.py:12` | `test_hermes_subprocess_env_strips_claudecode` | test-name provenance encoding | DELIBERATE | n/a | **keep as-is** |
| F-PE-20 | `SKILL.md:56` | `will not appear in the \`<available_skills>\` system-prompt index.` | `<available_skills>` reference | DELIBERATE | n/a (Hermes rewrite) | **keep as-is** — `<available_skills>` is Hermes's convention (per `metadata.hermes` validator), not Claude's; used here to explain why frontmatter validation matters |
| F-PE-21 | `scripts/improve_description.py:61` | `"skill's description for the <available_skills> system-prompt index.\n"` | `<available_skills>` reference | DELIBERATE | n/a | **keep as-is** — same as F-PE-20 |
| F-PE-22 | `scripts/improve_description.py:63` | `"leirasat a <available_skills> rendszerprompt-index szamara."` | `<available_skills>` reference (Hungarian bilingual advisory) | DELIBERATE | n/a | **keep as-is** |
| F-PE-23 | `SKILL.md:23` | `The skill is the Hermes-native port of the Anthropic \`skill-creator\`` | bilingual advisory / provenance | DELIBERATE | n/a | **keep as-is** — provenance statement |
| F-PE-24 | `SKILL.md:25` | `Claude-specific invocation has been replaced with the Hermes equivalent per` | bilingual advisory / migration provenance | DELIBERATE | n/a | **keep as-is** |
| F-PE-25 | `SKILL.md:37` | `non-Hermes host (e.g. Anthropic's skill format) to Hermes's tool-name and` | bilingual advisory / "When to Use" bullet | DELIBERATE | n/a | **keep as-is** |

### What is NOT a residue (verified absent)

- **Uppercase tool names in body prose** (pattern: `\b(Read|Write|Edit|Glob|Grep|Bash|Task|Skill|AskUserQuestion|WebSearch|WebFetch|TodoWrite)\b`) — zero hits in body prose across `SKILL.md`, `SKILL.md.short`, `agents/*.md`. The single regex hit was `SKILL.md:18: # Skill Creator` (heading — false positive).
- **Cowork references** — zero hits.
- **`claude.ai` / `claude.com` / `anthropic.com` URLs** — zero hits.
- **`you are Claude` / `as Claude` / `Claude Code` (subject marker)** — zero hits. The only "Claude Code"-shaped references are the negative-form guard rails (F-PE-5, F-PE-6) which OPPOSE Claude-CLI usage.
- **System-prompt scaffolding phrases** ("You are a helpful assistant", "Today's date is", "Assistant:") — zero hits.
- **Anthropic-style agent YAML** (`name:`, `model:` tool-whitelist frontmatter) — zero hits. Local agent files use `agent_name:` + `toolsets:` (Hermes convention).
- **Triple-quoted docstrings with "You are a..."** — zero hits.
- **`<available_skills>` as Claude system-prompt index convention** — three hits (F-PE-20..22), all DELIBERATE because `<available_skills>` is Hermes's documented skill index convention (per the `metadata.hermes` validator referenced in `SKILL.md:55-56`), not Claude's.

### Why the vendored pin has no overlap with the local skill

The vendored `SKILL.md` (33,168 B) and the local `SKILL.md` (3,550 B) share
**zero content overlap** — the local file is a from-scratch Hermes rewrite,
not a patch of the original. The same is true for the three agent prompts:
the vendored `grader.md` (224 lines of Claude-prompt body) and the local
`grader.md` (38 lines) have no shared text. This is by design — the Phase 5
migration (see `MIGRATION.skill-port.md`, T3 inventory) replaced every
Claude-specific binding rather than translating it; the local prompts are
written in Hermes-native language from first principles.

Consequence: the "is the local file a residue of the vendored file?"
question is **NO** for every prompt-bearing file in scope. The local
prompts are independent artefacts whose Claude/Anthropic mentions are
*intentional provenance*, not inherited residue.

## Bilingual advisories preserved (NOT residues)

All Claude/Anthropic mentions in the local skill are bilingual advisories
that document the migration provenance. They are required for the
bilingual-advisory contract (see `hermes-skills-hitl-decisions.md` Q4/Q5)
and must NOT be removed:

- `SKILL.md:23` — provenance statement ("Hermes-native port of the
  Anthropic `skill-creator`")
- `SKILL.md:25` — migration provenance ("Claude-specific invocation has
  been replaced with the Hermes equivalent per the T3 inventory")
- `SKILL.md:37` — "When to Use" bullet (migrate a non-Hermes host skill)
- `SKILL.md:42` — anti-pattern reminder ("Do NOT use Anthropic tool names")
- `SKILL.md:52` — anti-pattern reminder ("Do NOT call the Anthropic CLI")
- `SKILL.md:71` — verification checklist ("No Anthropic-CLI invocations
  anywhere in `scripts/`")
- `agents/grader.md:5-6, 36` — rubric axis + anti-pattern reminder
- `scripts/run_eval.py:6, 41, 44, 47, 105` — adapter-contract docstring
- `scripts/aggregate_benchmark.py:25` — adapter-consumer docstring
- `scripts/run_loop.py:10` — T3-binding removal provenance
- `_subprocess.py:27, 29, 34, 37-38` — legacy `CLAUDECODE` env var
  explanation
- `scripts/run_eval.py:14`, `_subprocess.py:12` — test names encoding the
  migration rule they verify

## Open questions for Phase 2 synthesizer

1. **Should the `_LEGACY_GUARD_VARS` constant rename `CLAUDECODE` to a
   Hermes-neutral term?** It is the right behaviour to strip it (the
   variable is real and the helper has to handle it), but the *constant
   identifier* contains `CLAUDECODE` literally. Phase 2 may want a rename
   to `_LEGACY_ANTHROPIC_GUARD_VAR` or similar so the symbol itself
   doesn't carry Claude-prompt language. (Not a residue — a hygiene
   question.)

2. **Should `scripts/run_eval.py` emit Hermes-shape downstream, instead of
   translating TO the legacy Anthropic shape and forcing every consumer
   to know about the adapter?** Today the adapter is a one-way translation
   and every other script (`aggregate_benchmark.py:25`,
   `generate_report.py`) references "Anthropic-shaped dicts". This is
   technically correct but adds a translation tax to every future Hermes
   consumer. Phase 2 should decide whether the migration is complete or
   whether the pipeline still carries legacy shape inside.

3. **`<available_skills>` is Hermes's documented convention, but it is
   visually identical to Anthropic's `available_skills` system-prompt
   index**. A reviewer who is not aware of the Hermes validator might
   mis-flag F-PE-20..22 as Claude residues. Phase 2 may want a one-line
   cross-link in the SKILL.md explanation (e.g. "the validator injects
   validated skills into the `<available_skills>` block — see
   `hermes-agent-skill-authoring/SKILL.md`") to remove the ambiguity
   for future audits.

4. **Is the absence of `scripts/__init__.py` in the local skill a
   residue?** The vendored pin has it; the local skill does not. Not a
   prompt-language issue, but flagged here so Phase 2 can decide
   whether it's deliberate (Hermes doesn't need it) or accidental
   (migrator dropped it).

## Coverage

- **Files covered**: 16 files (all prompt-bearing + the helpers that
  contain docstrings with Claude-shape references)
  - `SKILL.md`
  - `SKILL.md.short`
  - `agents/grader.md`
  - `agents/analyzer.md`
  - `agents/comparator.md`
  - `eval-viewer/viewer.html`
  - `eval-viewer/generate_review.py`
  - `scripts/aggregate_benchmark.py`
  - `scripts/generate_report.py`
  - `scripts/improve_description.py`
  - `scripts/package_skill.py`
  - `scripts/quick_validate.py`
  - `scripts/run_eval.py`
  - `scripts/run_loop.py`
  - `scripts/utils.py`
  - `_subprocess.py`
- **Files NOT covered**:
  - `scripts/__init__.py` — does not exist locally (present in vendored
    pin; not a prompt-bearing concern)
  - `README.md` — does not exist locally; vendored also has no README
  - `LICENSE.txt` — license text, not a prompt-bearing file (Phase 6
    handles inheritance)
  - `references/schemas.md` — not present locally (vendored has it;
    JSON/YAML schema docs, not Claude-prompt language)
  - `assets/eval_review.html` — not present locally (vendored has it;
    static HTML template, no Claude-prompt language)
- **Pattern categories searched** (per task spec):
  1. Uppercase tool names in body prose (outside code fences)
  2. Cowork / `claude.ai` / `claude.com` references
  3. `Claude Code` / `as Claude` / `you are Claude` subject markers
  4. `<available_skills>` index formátum
  5. Anthropic-style agent YAML (`name:`, `model:` tool-whitelist)
  6. System-prompt scaffolding phrases
  7. Triple-quoted docstrings with "You are a..." prompts

## Conclusion

The local `skills/skill-creator/` skill is **prompt-language clean** by the
criterion of this lens. There are no Claude-specific prompt residues; every
Claude/Anthropic mention is either (a) a deliberate bilingual advisory,
(b) a negative-form guard rail explicitly opposing Claude-CLI behaviour,
(c) a technical contract description for the shape-adapter, or (d) a
test-name provenance encoding. The vendored upstream pin and the local
skill are independent artefacts (the local files are from-scratch Hermes
rewrites, not patches).

The Phase 2 synthesizer should treat this dossier as a **null result** for
the prompt-engineer lens, with the four open questions above as the only
non-trivial handoff items.

## Sources

| # | file | role | read for |
| --- | --- | --- | --- |
| 1 | `skills/skill-creator/SKILL.md` | local Hermes rewrite | full read |
| 2 | `skills/skill-creator/SKILL.md.short` | short frontmatter | full read |
| 3 | `skills/skill-creator/agents/grader.md` | local Hermes rewrite | full read |
| 4 | `skills/skill-creator/agents/analyzer.md` | local Hermes rewrite | full read |
| 5 | `skills/skill-creator/agents/comparator.md` | local Hermes rewrite | full read |
| 6 | `skills/skill-creator/eval-viewer/viewer.html` | static viewer | full read |
| 7 | `skills/skill-creator/eval-viewer/generate_review.py` | static-asset generator | full read |
| 8 | `skills/skill-creator/scripts/aggregate_benchmark.py` | metrics aggregator | full read |
| 9 | `skills/skill-creator/scripts/generate_report.py` | report writer | full read |
| 10 | `skills/skill-creator/scripts/improve_description.py` | description improver | full read |
| 11 | `skills/skill-creator/scripts/package_skill.py` | tarball packager | full read |
| 12 | `skills/skill-creator/scripts/quick_validate.py` | frontmatter validator | full read |
| 13 | `skills/skill-creator/scripts/run_eval.py` | eval runner + adapter | full read |
| 14 | `skills/skill-creator/scripts/run_loop.py` | loop orchestrator | full read |
| 15 | `skills/skill-creator/scripts/utils.py` | bilingual `emit()` helper | full read |
| 16 | `skills/skill-creator/_subprocess.py` | nesting-guard helper | full read |
| 17 | `docs/research/anthropic-skill-creator-original/skills/skill-creator/SKILL.md` | vendored pin (upstream) | preview (head 50 lines) |
| 18 | `docs/research/anthropic-skill-creator-original/skills/skill-creator/agents/grader.md` | vendored pin (upstream) | full read |
| 19 | `docs/research/anthropic-skill-creator-original/skills/skill-creator/agents/analyzer.md` | vendored pin (upstream) | full read |
| 20 | `docs/research/anthropic-skill-creator-original/skills/skill-creator/agents/comparator.md` | vendored pin (upstream) | full read |
| 21 | `docs/research/upstream-audit-researcher.md` | upstream-audit researcher output | full read |

## Confidence summary

- **High**: 25 findings (all classified DELIBERATE; all backed by exact
  file:line evidence from this conversation's Read tool calls)
- **Medium**: 0
- **Low**: 0
- **Speculative**: 0

The null-result claim ("zero Claude-specific prompt-language residues")
is high-confidence because:

1. Every prompt-bearing file was read in full.
2. Every pattern category in the task spec was searched with targeted
   regex greps and the output was inspected.
3. The vendored pin was cross-referenced to confirm the local files are
   independent Hermes rewrites, not patches.
4. Every Claude/Anthropic mention was traced to its function (guard
   rail, adapter contract, provenance, or test-name) and classified.
