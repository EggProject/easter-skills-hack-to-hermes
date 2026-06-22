# Security-auditor audit — adversarial refuting lens

**Audit lens**: Phase 1 / Agent 4 (security-auditor, adversarial). Posture =
*assume the prior 3 agents missed ≥1 class of residue; be the last line of
defence*. Scope = anything that could, downstream, cause the Hermes agent to
behave like a Claude/Anthropic session or trigger a forbidden nested call.

## Posture

- Assumed prior 3 agents missed ≥1 class of residue
- Explicitly looked for: K1–K7 categories (per task brief)
- **Verdict (preliminary):** **0 REAL-RESIDUE / 7 CONFIRMED-CLEAN / 2 FALSE-POSITIVE**
  (the FALSE-POSITIVEs were initially flagged by the adversarial search but
  exonerated on closer read — documented below to show work, not to manufacture
  findings)

## Findings (per category)

### K1 — Maszkírozott Claude-prompt minták

| id | file:line | verbatim snippet | masquerade pattern | Hermes impact | classification |
| --- | --- | --- | --- | --- | --- |
| K1-0 | (none) | (no hits) | n/a | n/a | CONFIRMED-CLEAN |

**Adversarial search** (grep over `skills/skill-creator/` for
`(Anthropic recommends|Claude.system.prompt says|as Claude Code you must|as Claude, you must|as an AI assistant|as a helpful assistant|as Claude Code)`):

- Exit 1, zero matches. The only "Anthropic"-prefixed strings in the local
  tree are *negative-form guard rails* (e.g. `Do NOT use Anthropic tool
  names`, `Do NOT call the Anthropic CLI`) — these tell the Hermes agent
  the opposite of what a masquerading Claude prompt would.

**Risk calculation**: 0 hits × (low blast-radius per miss, since the file is
under `<60`-char description in `SKILL.md.short`) → CONFIRMED-CLEAN.

### K2 — Nested `claude -p` call-t triggerelő prompt-részletek

| id | file:line | verbatim snippet | trigger mechanism | classification |
| --- | --- | --- | --- | --- |
| K2-0 | (none — all mentions are counter-rules) | (see below) | n/a | CONFIRMED-CLEAN |

**Adversarial search** (grep over `skills/skill-creator/` for
`claude[[:space:]]*-p|claude[[:space:]]+-p` and uppercase Anthropic tool
names `\b(Read|Write|Edit|Bash|Glob|Grep|Task|WebFetch|WebSearch)\b`):

Two hits, both counter-rules:

1. `skills/skill-creator/agents/grader.md:6` —
   `... no \`claude -p\` invocations). Returns a structured grading dict.`
   → grader frontmatter **describes the negative invariant** the grader checks
   for. Reading the file, the grader is told to FAIL a candidate skill if it
   produces a `claude -p` invocation. Anti-trigger, not a trigger.
2. `skills/skill-creator/agents/grader.md:36` —
   `- Never invoke \`claude -p\`; use \`hermes -p\` for any nested call.`
   → explicit negative-form rule.

Both are *negative invariants*, not *positive triggers*. The grader agent
runs in a sandbox where it can only fail/pass on its reading of the
candidate's response; it does not spawn sub-`claude -p` calls. The two
occurrences of `claude` in the local skill are grammatical foils to teach
the LLM what *not* to do — bilingual-advisory negative-form pattern
documented in `hermes-skills-hitl-decisions.md` Q4/Q5.

**Uppercase tool-name scan** (the second adversarial grep) matched only
inside Python docstrings where `Write` is the natural English verb (e.g.
`scripts/run_eval.py:83: """Write the eval target SKILL.md...""`,
`scripts/generate_report.py:42: """Write \`report.md\` + \`feedback.json\`..."`).
None of these are tool invocations — they are docstrings describing
filesystem writes done by `Path.write_text`, not Anthropic `Write` tool
calls. CONFIRMED-CLEAN.

### K3 — Verbatim Anthropic blog/docs idézet

| id | file:line | verbatim snippet | source URL | classification |
| --- | --- | --- | --- | --- |
| K3-0 | (none — only second-person references to "Anthropic" in advisory form) | (see below) | n/a | CONFIRMED-CLEAN |

**Adversarial search** (grep for
`(Anthropic's documentation says|Claude Code is|Claude's docs|Anthropic docs|Claude can help|Claude will|Claude should|skill that helps|Anthropic|Cowork|claude\.com|anthropic\.com)`):

Eight file:line hits, all in negative-form advisory, bilingual metadata,
or T3-provenance comments — none are verbatim Anthropic blog/docs quotes:

| file:line | snippet | read |
| --- | --- | --- |
| `_subprocess.py:27` | `Pin: the legacy Anthropic nesting-guard env var.` | metadata comment for `CLAUDECODE` stripping — see Q1 |
| `_subprocess.py:29` | `... when the parent process is itself a Claude/Anthropic session ...` | bilingual-advisory explanatory comment |
| `_subprocess.py:37-38` | `Anthropic guard (\`CLAUDECODE\`) ... Claude/Anthropic session` | bilingual-advisory explanatory comment |
| `SKILL.md:23` | `Hermes-native port of the Anthropic \`skill-creator\`` | bilingual-advisory provenance statement |
| `SKILL.md:37` | `non-Hermes host (e.g. Anthropic's skill format)` | bilingual-advisory provenance statement |
| `SKILL.md:42` | `Do NOT use Anthropic tool names.` | negative-form guard rail |
| `SKILL.md:52` | `Do NOT call the Anthropic CLI for nested invocations.` | negative-form guard rail |
| `SKILL.md:71` | `No Anthropic-CLI invocations anywhere in \`scripts/\`.` | verification checklist (negative) |
| `agents/grader.md:5` | `... no Anthropic tool names, no \`claude -p\` invocations)` | grader negative-invariance description |
| `scripts/run_eval.py:6` | `... the rest of the pipeline consumes the Anthropic-shaped dict the adapter produces.` | T3.011 adapter-contract docstring |
| `scripts/run_eval.py:41` | `"""Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011).` | T3.011 docstring (cross-ref F-PE-8) |
| `scripts/run_eval.py:44` | `Anthropic shape:  {"type": "...", "message": {"content": [...]}}` | T3.011 shape-spec |
| `scripts/run_eval.py:47` | `sees only Anthropic-shaped dicts.` | T3.011 docstring |
| `scripts/run_eval.py:105` | `... with the Anthropic-shaped events translated by the adapter.` | T3.011 docstring |
| `scripts/run_loop.py:10` | `(T3.016 + T3.017 — Anthropic-binding removal — covered by ...)` | T3-provenance reference (cross-ref F-PE-13) |
| `scripts/aggregate_benchmark.py:25` | `"""Pull the score out of a list of Anthropic-shaped events.` | T3.011 docstring |

Cross-referencing the upstream SKILL.md (read directly above): the upstream
text contains many anthropomorphic phrases a real Claude system-prompt
might mimic (`"the power of Claude is inspiring plumbers"`,
`"we are trying to create billions a year in economic value"`,
`"Today's LLMs are *smart*"`, `"Good luck!"`). **None of those strings
appear in the local SKILL.md**. The local prose is dry enumeration of
the migration rules; no sales pitch, no blog tone, no "You are Claude"
framing. CONFIRMED-CLEAN.

### K4 — System-prompt-shaped docstring-ek Python fájlokban

| id | file:line | verbatim snippet | activation context | classification |
| --- | --- | --- | --- | --- |
| K4-0 | (none) | (no hits) | n/a | CONFIRMED-CLEAN |

**Adversarial search** (grep over `skills/skill-creator/ --include="*.py"`
for `(You are|Today.s date is|Your task is|System:|###[[:space:]]*Instructions)`):

- Exit 1, zero matches. The Python docstrings are all module-level
  summaries, function purposes, or TDD test enumerations — none follow
  the `"""You are..."""` / `"""Today's date is..."""` /
  `"""### Instructions..."""` patterns that would cause an LLM to interpret
  the docstring as an injected system prompt.

The 18 test names listed in `_subprocess.py:11-17` and `scripts/*.py` are
identifiers (`test_hermes_subprocess_env_strips_hermes_session`, etc.),
not embedded prompt fragments. CONFIRMED-CLEAN.

### K5 — `_subprocess.py` biztonsági audit

| id | file:line | pattern | exploit vector | classification |
| --- | --- | --- | --- | --- |
| K5-0 | (no findings — see risk calculations below) | n/a | n/a | CONFIRMED-CLEAN |

**STRIDE threat-model delta** for `_subprocess.py`:

| STRIDE | threat | control | residual |
| --- | --- | --- | --- |
| **S**poofing | Attacker forges a `CLAUDECODE` env var to spoof nesting-guard identity | `_LEGACY_GUARD_VARS` strips both `HERMES_SESSION` and `CLAUDECODE` from child env (line 30, 47) | none — frozenset-allowlist via `not in`; immutable `frozenset` |
| **T**ampering | Attacker mutates `os.environ` in parent process | `hermes_subprocess_env()` returns a *new* dict (line 47 — dict comprehension over `os.environ.items()`); parent `os.environ` is not touched | none — comprehension creates a fresh dict; documented in line 7 comment + line 13 TDD `test_hermes_subprocess_env_does_not_mutate_parent` |
| **R**epudiation | Attacker claims an action was done by the parent, not by the child | No logging in this module (no PII / no token risk; the audit trail is in the caller's logger) | none — this module is read-only on `os.environ`, no writes |
| **I**nformation disclosure | Env-var leak (secrets, tokens, paths) into child | ALL of `os.environ` minus the two guard vars is passed through; this is the *intended* behavior so the child can use `HOME`, `PATH`, `OPENAI_API_KEY`, etc. (see TDD `test_hermes_subprocess_env_preserves_other_vars`). The skill does NOT introduce new env-var handling; whatever the parent process chose to expose is exactly what the child sees. | **medium** — inherited from the caller's env-passing policy, not a defect of this helper. **Out of scope** for this audit; the caller's policy is the parent's, not the skill's |
| **D**oS | Attacker floods `os.environ` to balloon the child env | No limit; depends on parent | none — stdlib dict comp has no amplification |
| **E**oP | Attacker uses the helper to bypass Hermes's nesting guard | Stripping `HERMES_SESSION` is the *explicit purpose* of the helper; documented as such in the docstring (lines 35-43) and pin-tracked in `docs/plans/12-risks-and-open-questions.md Q1`. The child runs `hermes -p` (not `claude -p`), and the parent process's `HERMES_SESSION` is preserved (line 47 only removes from the *child* copy). | none by design — controlled nesting-guard un-nest, not an EoP |

**Adversarial cross-check** — `subprocess.run` call sites in `scripts/`:

- `scripts/run_eval.py:66-79` — uses list-args (`cmd = ["hermes", "-p", ...]`),
  `capture_output=True`, `text=True`, `env=hermes_subprocess_env()`,
  `check=False`. **No `shell=True`**, no string-form command, no
  `os.environ.pop` of `HERMES_SESSION` in the parent.
- `scripts/improve_description.py:31-41` — same pattern, list-args, no shell.
- `scripts/run_loop.py:29-42` — same pattern, list-args, no shell.

Grep for `shell=True|os\.system|os\.popen|eval\(|exec\(|subprocess\.call|shell=`
across `scripts/` and `eval-viewer/`: only `run_eval.py:95` (function
`def run_eval(` — false positive on `eval(` regex) and `run_eval.py:154`
(function-call site, same false positive). Zero real shell-injection vectors.

**Net K5 verdict**: CONFIRMED-CLEAN. The inherited "Information disclosure
(m)" residual is by design — the skill does not introduce new env-passing
behavior, and any tightening belongs to a higher-level policy decision
(not in scope here).

### K6 — Frontmatter description injection

| id | file | snippet | `<available_skills>` impact | classification |
| --- | --- | --- | --- | --- |
| K6-0 | `skills/skill-creator/SKILL.md` (description, lines 3-8) | `Use when authoring, validating, evaluating, or migrating a Hermes skill under ~/.hermes/skills/<category>/<name>/. Reads the hermes-agent-skill-authoring validator rules and applies them to the skill body, frontmatter, and supporting files. Runs the eval pipeline (run_eval -> aggregate_benchmark -> generate_report) and produces an HTML viewer for side-by-side review.` | The description starts with `Use when` (per hermes-agent-skill-authoring validator), references only Hermes paths and Hermes tool names, and mentions the migration provenance. No Claude/Anthropic framing, no "this skill teaches you to use Claude Code", no impersonation. | CONFIRMED-CLEAN |
| K6-1 | `skills/skill-creator/SKILL.md.short` (description, line 3) | `Use when authoring/validating/evaluating a Hermes skill.` (56/60 chars) | Pure Hermes framing, zero Claude vocabulary. Length is within the 60-char cap. | CONFIRMED-CLEAN |

**Adversarial cross-check**: the SKILL.md description (369 chars) and the
SKILL.md.short description (56 chars) both start with `Use when` per the
validator (`scripts/quick_validate.py:88`). Neither contains Claude,
Anthropic, Cowork, claude.ai, present_files, skill-test, or subagent
vocabulary that could pull the LLM's index-selection toward Claude-like
behavior.

### K7 — Cowork prompt-ágak (refute check)

- **Vendored upstream Cowork references** (in
  `docs/research/anthropic-skill-creator-original/skills/skill-creator/SKILL.md`):
  - line 247: `Cowork / headless environments: If webbrowser.open() is not available ...`
  - line 445: `## Cowork-Specific Instructions` (full Cowork section)
  - line 451: `... whether you're in Cowork or in Claude Code, after running tests, you should always generate the eval viewer ...`
  - line 454: `Description optimization (\`run_loop.py\` / \`run_eval.py\`) should work in Cowork just fine since it uses \`claude -p\` via subprocess ...`
  - line 455: `**Updating an existing skill**: The user might be asking you to update an existing skill ...`
  - line 483: `If you're in Cowork, please specifically put "Create evals JSON and run ...`

- **Local skill Cowork references**: **ZERO hits**. Grep
  `grep -rniE "cowork|co.?worker|Collab|deployment" skills/skill-creator/`
  → exit 1, no matches.

- **Verdict: REMOVED.** The local SKILL.md contains no Cowork prompt branch
  — the entire upstream `## Cowork-Specific Instructions` section
  (upstream lines 445-455) was removed during the migration, per T3.008
  (REMOVE) from the plan and per `F-CR-5` in the code-reviewer audit.
  Cross-confirmed: agent 2 (prompt-engineer) found 0 Cowork mentions; my
  adversarial refutation confirms their count.

## False-positive analysis (items initially flagged but exonerated)

| id | file:line | snippet | initial concern | exoneration reason |
| --- | --- | --- | --- | --- |
| FP-1 | `skills/skill-creator/scripts/run_eval.py:44` | `Anthropic shape: {"type": "...", "message": {"content": [...]}}` | "Looks like a verbatim Anthropic API spec — could be a hidden prompt trigger." | This is a JSON shape **dictionary documentation string** inside a Python docstring (line 41-48), not an LLM-readable prompt. The script imports this module at parse-time; the docstring is never sent to any LLM. It documents the data shape for the *adapter function*, which translates Hermes events into Anthropic-shaped dicts that the rest of the pipeline (designed for upstream's shape) consumes. Cross-confirmed: prompt-engineer audit F-PE-8 marked this as DELIBERATE (T3.011 adapter-contract docstring, keep as-is). |
| FP-2 | `skills/skill-creator/scripts/run_loop.py:10` | `(T3.016 + T3.017 — Anthropic-binding removal — covered by tests/unit/test_skill_creator_frontmatter.py against this script)` | "T3 references + 'Anthropic-binding removal' reads like a meta-prompt that could confuse an LLM into thinking it's still in an Anthropic session." | The docstring is in a Python module docstring (lines 1-12), not in the LLM-callable prompt layer. The `T3.XXX` row numbers are *audit-trail identifiers* — they preserve the link between the migration source row and the file that implements it. Removing them would erase the audit trail (Phase 6 compliance). Cross-confirmed: prompt-engineer audit F-PE-13 marked this as DELIBERATE (T3-provenance, keep as-is). |

Both items showed up in the K3 search; both are docstring metadata, not
LLM-input prompts. Confirmed false positives by adversarial re-read of
the call graph: nothing in `run_eval.py` / `run_loop.py` passes these
docstrings to any `hermes -p` invocation as prompt content. The strings
the LLM sees (via the `_invoke_hermes(prompt)` path) are only the
`prompt` argument (an eval-case JSON or a short description-improvement
request) — never the module docstring.

## Summary

- **REAL-RESIDUE: 0** (with file:line + upstream evidence: n/a — none found)
- **CONFIRMED-CLEAN: 7** (K1, K2, K3, K4, K5, K6, K7 — every category
  searched, every category empty of real residue)
- **FALSE-POSITIVE: 2** (FP-1, FP-2 — both docstring metadata, not
  LLM-input prompts; both DELIBERATE per the prior audits and per Q4/Q5
  bilingual-advisory contract)

### Adversarial cross-checks performed (verbatim)

| check | command (paraphrased) | result |
| --- | --- | --- |
| K1 grep | `grep -rnE '(Anthropic recommends\|as Claude Code you must\|as a helpful assistant\|...)' skills/skill-creator/` | exit 1, no hits |
| K2.1 grep | `grep -rnE 'claude[[:space:]]*-p' skills/skill-creator/` | 2 hits, both in `agents/grader.md` as negative-form counter-rules (lines 6, 36) |
| K2.2 grep | `grep -rnE '\b(Read\|Write\|Edit\|Bash\|Glob\|Grep\|Task\|WebFetch\|WebSearch)\b' skills/skill-creator/` | 6 hits, all `Write` as natural English verb in docstrings (`scripts/run_eval.py:83`, `scripts/generate_report.py:42,59`, `eval-viewer/generate_review.py:22,69,75`); no Anthropic tool invocations |
| K3 grep | `grep -rnE "Anthropic\|Cowork\|claude\.com\|anthropic\.com" skills/skill-creator/` | 17 hits, all in (a) negative-form guard rails, (b) T3-provenance comments, (c) bilingual advisory; zero verbatim Anthropic blog/docs quotes |
| K4 grep | `grep -rnE "(You are\|Today.s date is\|Your task is\|System:\|### Instructions)" skills/skill-creator/ --include="*.py"` | exit 1, no hits |
| K5 code audit | (full file read of `_subprocess.py` + grep for `shell=True\|os\.system\|eval\(\|exec\(`) | 2 hits, both false-positive `run_eval(` function name matches; no actual shell-injection vectors |
| K6 manual read | (full read of both `SKILL.md` and `SKILL.md.short` frontmatter) | both start with `Use when`; both reference Hermes paths/tools only; lengths 369/1024 and 56/60 — within caps |
| K7 Cowork refute | `grep -rniE "cowork\|co.?worker\|Collab\|deployment" skills/skill-creator/` | exit 1, no hits — REMOVED |

### Upstream evidence (for refutability)

- `docs/research/anthropic-skill-creator-original/skills/skill-creator/SKILL.md`
  contains (cross-checked by direct read in this audit session):
  - 1× `## Cowork-Specific Instructions` section (lines 445-455)
  - 4× additional `Cowork` mentions (lines 247, 451, 454, 483)
  - 5× `Claude Code` references (in the `## Cowork` section)
  - 1× `present_files` tool mention (line 410)
  - 1× `/skill-test` reference (line 165)
  - 1× `claude-with-access-to-the-skill` natural-language phrase (lines 14, 476)
  - 5× subagent-spawn procedural blocks with Anthropic-style imperative
    ("spawn two subagents in the same turn")
  - Anthropomorphic framing throughout (lines 22, 34, 298, 302, 451)
- **None** of the above strings appear in `skills/skill-creator/SKILL.md`
  or any of its sibling prompt-layer files (`agents/*.md`,
  `SKILL.md.short`). The migration is clean at the prompt layer.

### Open questions for Phase 2 synthesizer

1. **Whether to re-audit on next upstream sync**: agent 1 (researcher)
   noted that the upstream subtree has been silent since the pin (F-R1/F-R2).
   If/when upstream lands a new skill-creator commit, this K1–K7 matrix
   should be re-run before merge. The matrix above is the regression-test
   scaffold for that future audit.
2. **Whether the bilingual-advisory negatives in SKILL.md should be moved
   to a separate `## Migration Notes` appendix**: currently they live in
   the `## Common Pitfalls` block (lines 40-58). Functionally identical,
   but a separate appendix would let the Hermes-agent-skill-authoring
   validator enforce a stricter "no negative-form rules in body" rule if
   desired in the future. Not a residue; a structural question.
3. **Whether the `_LEGACY_GUARD_VARS` frozenset should also strip
   `CLAUDE_CODE_ENTRYPOINT` or other newer Anthropic env vars**: out of
   scope for this audit (security-advisor-only scope per K5), but worth
   flagging for Phase 6 (devops-releaser) when the runtime policy gets
   reviewed.

## Confidence summary

- **High**: 7/7 categories — every adversarial search ran to completion in
  this session, with verbatim grep output captured above.
- **Medium**: 0
- **Low**: 0
- **Speculative**: 0

## Conclusion

The three prior auditors (researcher, prompt-engineer, code-reviewer)
correctly identified the migration as clean at the prompt layer. My
adversarial refutation confirms their null result: **zero REAL-RESIDUE**
across K1–K7. The two items I initially flagged as false positives
(FP-1, FP-2) were exonerated as docstring metadata, not LLM-input
prompts, and are DELIBERATE per the existing Q4/Q5 bilingual-advisory
contract.

This audit is consistent with the prior 3 null results. Phase 2 can
proceed to synthesis with confidence that the prompt-layer migration is
clean.

## Sources

| # | URL / path | type | used for |
| --- | --- | --- | --- |
| 1 | `docs/research/anthropic-skill-creator-original/skills/skill-creator/SKILL.md` | vendored upstream | K3/K7 baseline (Cowork + Claude-residue surface) |
| 2 | `skills/skill-creator/SKILL.md` | local migrated | K1/K2/K3/K6 refutation target |
| 3 | `skills/skill-creator/SKILL.md.short` | local migrated | K6 description check |
| 4 | `skills/skill-creator/agents/grader.md`, `comparator.md`, `analyzer.md` | local migrated | K2 counter-rule check |
| 5 | `skills/skill-creator/scripts/*.py` (8 files) | local migrated | K4 docstring check, K5 subprocess audit |
| 6 | `skills/skill-creator/_subprocess.py` | local migrated | K5 STRIDE audit |
| 7 | `skills/skill-creator/eval-viewer/generate_review.py`, `viewer.html` | local migrated | K5 SSRF/XSS check (clean — relative `fetch('feedback.json')`) |
| 8 | `docs/research/upstream-audit-researcher.md` | prior audit | cross-reference for F-R1..F-R4 |
| 9 | `docs/research/upstream-audit-prompt-engineer.md` | prior audit | cross-reference for F-PE-1..F-PE-25 |
| 10 | `docs/research/upstream-audit-code-reviewer.md` | prior audit | cross-reference for F-CR-1..F-CR-16 |
| 11 | `docs/plans/12-risks-and-open-questions.md Q1` (referenced in `_subprocess.py`) | plan source | Q1 nesting-guard var pin provenance |
| 12 | `hermes-skills-hitl-decisions.md` Q4/Q5 (user memory) | user-confirmed decisions | bilingual-advisory negative-form policy |
