export const meta = {
  name: 'hermes-skills-plan-repair',
  description: 'Phase 3a: diagnose 11/12 refuted claims, repair 4 flawed + write 9 missing plan files, adversarial verify 4 lenses',
  phases: [
    { title: 'Diagnose' },
    { title: 'PlanRepair' },
    { title: 'VerifyPlanV2' },
  ],
}

const CONTEXT = `
PROJECT CONTEXT (every agent must respect):
- Project workdir: /Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/hermes-skills-dev
- Hermes install (READ-ONLY, NEVER modify): /Users/kiscsicska/.hermes/hermes-agent
- Hermes is NousResearch/hermes-agent v0.16.0 at commit 368fcf1ff
- Anthropic official skill-creator upstream: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator
  Local cache (NOT a git checkout): /Users/kiscsicska/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/
  Pinned upstream commit: 2a40fd2e7c52207aa903bd33fc4c65716126966e
- docs/maybe-patch-points.md is the spec for the OPT-IN Task E built-in-prompt redirect (separate from the 60->1024 limit raise).
- CRITICAL SAFETY: NEVER run any patch script. NEVER modify ~/.hermes/hermes-agent. Read-only inspection only.
- Existing research artefacts live in <workdir>/plans/_research/*.json (6 topic JSONs + _verify_results.json). DO NOT recompute these -- READ them.
- Existing plan files live in <workdir>/plans/00-index.md, 01-overview.md, 02-architecture.md, 03-plugin-spec.md. These CONTAIN BLOCKERS (see plans/_plan_reviews.md) -- they MUST be rewritten, not patched on top of.
- Existing plan reviews live in <workdir>/plans/_plan_reviews.md -- read the blockers and incorporate fixes.
- TDD mandatory; 100% code+logic coverage; uv+pre-commit+ruff+black+mypy+wemake; bilingual EN+HU console/log + --help; worktree+PR.
- HITL: do NOT write any code. This workflow is PLAN-ONLY.
`

const DIAGNOSE_SCHEMA = {
  type: 'object',
  required: ['confirmedFacts', 'refutedClaims', 'revisedClaims', 'blockerFixList', 'openQuestionsForHITL', 'proposedPlanLayout'],
  additionalProperties: false,
  properties: {
    confirmedFacts: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['fact', 'evidencePath', 'confidence'], properties: { fact: { type: 'string' }, evidencePath: { type: 'string' }, confidence: { type: 'string' } } } },
    refutedClaims: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['wasClaimed', 'actualFact', 'correctFix'], properties: { wasClaimed: { type: 'string' }, actualFact: { type: 'string' }, correctFix: { type: 'string' } } } },
    revisedClaims: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['claim', 'nuance', 'revisedStatement'], properties: { claim: { type: 'string' }, nuance: { type: 'string' }, revisedStatement: { type: 'string' } } } },
    blockerFixList: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['blocker', 'fix', 'planFile'], properties: { blocker: { type: 'string' }, fix: { type: 'string' }, planFile: { type: 'string' } } } },
    openQuestionsForHITL: { type: 'array', items: { type: 'string' } },
    proposedPlanLayout: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['filename', 'title', 'lineBudget'], properties: { filename: { type: 'string' }, title: { type: 'string' }, lineBudget: { type: 'integer' } } } },
  },
}

const PLAN_FILES_SCHEMA = {
  type: 'object',
  required: ['files', 'summary', 'openQuestionsForHITL', 'fixLedger'],
  additionalProperties: false,
  properties: {
    files: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['filename', 'title', 'content', 'lineCount'], properties: { filename: { type: 'string' }, title: { type: 'string' }, content: { type: 'string' }, lineCount: { type: 'integer' } } } },
    summary: { type: 'string' },
    openQuestionsForHITL: { type: 'array', items: { type: 'string' } },
    fixLedger: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['blocker', 'fixedIn', 'how'], properties: { blocker: { type: 'string' }, fixedIn: { type: 'string' }, how: { type: 'string' } } } },
  },
}

const PLAN_REVIEW_SCHEMA = {
  type: 'object',
  required: ['lens', 'overallVerdict', 'blockers', 'findings'],
  additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    overallVerdict: { type: 'string', enum: ['approve', 'request-changes', 'block'] },
    blockers: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['planFile', 'section', 'concern', 'suggestedFix'], properties: { planFile: { type: 'string' }, section: { type: 'string' }, concern: { type: 'string' }, suggestedFix: { type: 'string' } } } },
    findings: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['severity', 'planFile', 'section', 'concern', 'suggestedFix'], properties: { severity: { type: 'string', enum: ['nit', 'minor', 'major', 'blocker'] }, planFile: { type: 'string' }, section: { type: 'string' }, concern: { type: 'string' }, suggestedFix: { type: 'string' } } } },
  },
}

// ---------- Phase 1: Diagnose ----------
phase('Diagnose')
const diagnose = await agent(`${CONTEXT}

You are the Diagnose agent. Read the following artefacts and produce a diagnosis JSON.

READ FIRST (do NOT re-run any research):
- <workdir>/plans/_research/truncation.json (lines 644-655 of agent/skill_utils.py, line 1090 of agent/prompt_builder.py, GitHub issue #46005)
- <workdir>/plans/_research/anthropicCreator.json (pinned commit 2a40fd2e7c52207aa903bd33fc4c65716126966e, fileList[21], claudeSpecificInvocations[50], localCopyPath, claudeStrengthsToPreserve)
- <workdir>/plans/_research/hermesSkillConventions.json (skillDirectoryLayout, manifestFields, allowedAndForbiddenInvocations, authoringValidatorRules, descriptionLengthLimitCurrent, descriptionLengthLimitAfterPatch)
- <workdir>/plans/_research/pluginAuthoring.json (pluginAnatomy, requiredManifestFields, extensionPoints, patchHookMechanism)
- <workdir>/plans/_research/profileSystem.json (profileStorage, defaultProfileMechanism, skillEnableDisableMechanism, auditApproach, relevantCliCommands, relevantSourceFiles)
- <workdir>/plans/_research/taskECandidates.json (independentCandidates[7], mayPatchPointsCandidates[7], reconciledFinalSet[8])
- <workdir>/plans/_research/_verify_results.json (12 verify verdicts with refuted + counterEvidence)
- <workdir>/plans/_plan_reviews.md (4 lenses, ~80 findings, 9 blockers)
- <workdir>/plans/00-index.md, 01-overview.md, 02-architecture.md, 03-plugin-spec.md (READ only, do not modify)
- <workdir>/docs/maybe-patch-points.md (source of truth for Task E)

DELIVERABLE: JSON object matching DIAGNOSE_SCHEMA with:
- confirmedFacts[] (facts that survive verification)
- refutedClaims[] (what was claimed, what is correct, the correction)
- revisedClaims[] (nuances)
- blockerFixList[] (the 9 blockers ranked + 1-line fix per blocker)
- openQuestionsForHITL[] (what the user must decide)
- proposedPlanLayout[] (the 13 plan files with per-file line budget; sum < 4500)

REASONING RULES:
- Default to confirming the underlying fact even if a verify verdict says refuted; most refutes are nuances, not core refutes. Use the counterEvidence text to refine, not to discard.
- The truncation site's core fact (60-char cap, function at skill_utils.py:647, called at prompt_builder.py:1090, GitHub issue #46005) is CONFIRMED. Refinements: the call at :1090 uses the function's return value verbatim; patching the function alone is sufficient.
- The Anthropic creator's pinned commit is CONFIRMED via GitHub API. The local cache at <marketplaces> is NOT a git checkout -- canonical source is the upstream URL only.
- The profile system's high-level shape is CONFIRMED (HERMES_HOME isolation, named profiles under ~/.hermes/profiles/<name>/, default = ~/.hermes itself), but specific API claims (e.g. hermes_cli.config.load_config(path=...)) are REFUTED -- the API takes no path kwarg.
- Task E candidate count is 7 sites (per docs/maybe-patch-points.md), not 8. Drop system_prompt.py from reconciled (not in the doc).
- The plugin authoring finding "NO clean plugin hook for monkey-patching a hardcoded constant" is CONFIRMED. The plugin must NOT monkey-patch in-process. The cap raise happens ONLY via Script #1 against a user-owned Hermes checkout. The plugin's role: register the migrated skill + emit a one-time bilingual advisory if the cap is detected un-raised (via static AST read of the user's hermes-agent checkout -- NOT a runtime setattr).

HARD CONSTRAINTS for the upcoming PlanRepair phase (include in your proposedPlanLayout as contract):
- EVERY plan file <= 500 lines. Per-file line budget table required.
- NO runtime monkey-patch anywhere.
- Script #1 --target is REQUIRED, defaults to NONE, refuses to run if --target equals ~/.hermes/hermes-agent, refuses if --target is missing agent/skill_utils.py.
- Script #1 cap-raise site: the SINGLE function agent/skill_utils.py:extract_skill_description (lines 644-655), with text+line anchor signature.
- The migration note is split: MIGRATION.hermes-patch.md (Script #1's cap-raise + 7 Task E sites) + MIGRATION.skill-port.md (per Claude-binding replacement in the migrated skill) + MIGRATION.md (top-level index). All three are source-controlled at <workdir>/, regenerated by --emit-migration-note.
- The migrated skill's description is <= 60 chars unless the patch is applied, in which case it can be up to 1024 chars. The installer MUST detect the active cap and refuse the install with a bilingual error if the description exceeds the active cap.
- Tool-name mapping table: read from hermesSkillConventions.json allowedAndForbiddenInvocations.
- Nesting-guard var: read from hermesSkillConventions.json or scan the upstream scripts. Commit to a specific name.
- Script #2 uses a single context manager with hermes_home_scope(path): that calls set_hermes_home_override(path) AND mirrors os.environ['HERMES_HOME'] = str(path); restores both on exit.
- Bilingual format: console messages = single line "[en] text / [hu] szoveg"; --help = two sections "Usage (English)" and "Hasznalat (magyar)" with mirrored content.
- The plugin's installer is interactive by default (TTY confirmation) and refuses to run against the real ~/.hermes unless --yes is passed; integration tests use a tmp_path HERMES_HOME.

OUTPUT: a single JSON object matching DIAGNOSE_SCHEMA.`, {
  label: 'diagnose:refuted-claims-and-blockers', phase: 'Diagnose', agentType: 'general-purpose', schema: DIAGNOSE_SCHEMA,
})

// ---------- Phase 2: PlanRepair ----------
phase('PlanRepair')
const planFiles = await agent(`${CONTEXT}

You are the PlanRepair agent. Your job: produce ALL 13 plan files (<=500 lines each, all under plans/), with the constraints and corrections from the Diagnose output below.

DIAGNOSE OUTPUT:
${JSON.stringify(diagnose, null, 2)}

DELIVERABLE: JSON matching PLAN_FILES_SCHEMA. files[] = ALL 13 plan files (00..12). Every file's content MUST be <=500 lines and lineCount must equal the number of newline-terminated lines in content.

PROPOSED FILE LAYOUT (use unless Diagnose's proposedPlanLayout justifies a change):
  00-index.md -- TOC, file map with line budgets, status legend, hard constraints
  01-overview.md -- mission, deliverables, acceptance criteria per deliverable (use AC-1.1, AC-2.1 etc. format)
  02-architecture.md -- component diagram, data flow, sequence, failure modes, safety
  03-plugin-spec.md -- Sec 5.1 plugin: directory layout, manifest, hooks, register, advisory
  04-script-1-patch.md -- Sec 5.2 + 6.B Script #1: idempotency, multi-signal targeting, all-or-nothing gate, --force (--i-accept-line-drift), exit code matrix, atomic write protocol, TDD test list
  05-script-1-task-e-toggle.md -- Sec 6.E opt-in --task-e-redirect: 7-site per-site table (file:line, current 8+ char anchor, replacement), how --task-e-redirect composes with the cap-raise site
  06-script-2-profiles.md -- Sec 5.3 + 6.C Script #2: hermes_home_scope context manager, audit-all-profiles flow, disable openai/skills/skill-creator, install/update migrated skill-creator, clear_skills_system_prompt_cache fallback, TDD test list
  07-skill-creator-migration.md -- Sec 5.4 + 6.D migrated skill: frontmatter spec, tool-name mapping table, T3 inventory table (per Claude-binding: path:line | claude-binding | hermes-binding | test-id), nesting-guard helper, eval pipeline + viewer changes, strength-preservation matrix
  08-migration-note-format.md -- Sec 5.5: 3-file split (MIGRATION.md index, MIGRATION.hermes-patch.md, MIGRATION.skill-port.md), generation per --emit-migration-note, determinism, exhaustiveness
  09-test-strategy.md -- TDD methodology, test pyramid, fixture strategy (tmp_path HERMES_HOME), coverage matrix, AST-grep bilingual rule, no-touch-sentinel for ~/.hermes/hermes-agent, snapshot fixtures for --help and migration note
  10-toolchain-and-conventions.md -- pyproject.toml layout, uv venv, pre-commit config (ruff+black+mypy+wemake strictest), commit granularity (1 commit per AC cluster 1.x..6.x), PR template
  11-sub-agent-delegation-map.md -- which sub-agent type does which Phase 5 task; preload skills
  12-risks-and-open-questions.md -- every unresolved question, with proposed default + escalation path

EACH FILE MUST HAVE:
- Front-matter (line 1-3): title, scope, ACs covered
- A "Status" or "Coverage" line listing which acceptance criteria are addressed
- Concrete table-driven specs (no "TBD" -- defaults are OK if justified)
- A "TDD test list" subsection if it specifies code
- A "Fix ledger" line at the bottom citing which _plan_reviews.md blockers it addresses (only for plan files that fix >=1 blocker)
- A line count self-assertion: "<!-- end of file: N lines (budget B) -->"

RULES:
- Every AC, function, hook, exit code, CLI flag, env var, file path, and function signature mentioned in the existing 4 files MUST be re-checked against the research JSON. Do NOT carry over the runtime monkey-patch, the 60-vs-1024 contradiction, the 8-sites Task E count, or the load_config(path=...) API.
- Tool names: read allowedAndForbiddenInvocations from <workdir>/plans/_research/hermesSkillConventions.json -- do NOT guess.
- The cap-raise is ONLY via Script #1, against a user-owned checkout (--target). The plugin emits a read-only advisory; no setattr on agent.skill_utils.
- The migration note is the 3-file split. Pin the location: <workdir>/MIGRATION.md, <workdir>/MIGRATION.hermes-patch.md, <workdir>/MIGRATION.skill-port.md.
- Bilingual rule: console = single line "[en] text / [hu] szoveg"; --help = two sections.
- Test list per code file: enumerate branch-by-branch (happy path, error path, edge case, error propagation, advisory firing, exit code, bilingual format).
- All line counts in the table of contents must match the actual lineCount of the file content. If a file would exceed 500 lines, split it.

OUTPUT: single JSON object matching PLAN_FILES_SCHEMA.`, {
  label: 'plan:repair-13-files', phase: 'PlanRepair', agentType: 'general-purpose', schema: PLAN_FILES_SCHEMA,
})

// ---------- Phase 3: VerifyPlanV2 ----------
phase('VerifyPlanV2')
const PLAN_LENSES = ['completeness-vs-brief', 'testability-and-coverage', 'safety-and-non-execution', 'migration-fidelity']
const reviews = await parallel(PLAN_LENSES.map(lens => () => agent(`${CONTEXT}

You are an adversarial plan reviewer, V2. Your lens: ${lens}.

PLAN (full content -- read from the files in <workdir>/plans/ that PlanRepair just wrote):
${JSON.stringify((planFiles && planFiles.files) || [], null, 2)}

INSTRUCTIONS:
- Re-Read the plan files you need. Verify every claim against the research JSON in <workdir>/plans/_research/.
- Find concrete gaps. Tie each finding to a specific plan file + section.
- Severity: nit / minor / major / blocker. A 'blocker' must justify why execution cannot start.
- If the plan addresses the V1 blockers (in <workdir>/plans/_plan_reviews.md), note that as a positive; if it does not, file a blocker.

Lens-specific checks:
- completeness-vs-brief: every Sec 5.1..5.7 + Sec 6.A..6.E + Sec 8 + Sec 10 acceptance criterion in the brief is covered with implementation-level detail in the plan.
- testability-and-coverage: every code file has a TDD test list that achieves 100% code + 100% logic coverage WITHOUT running scripts against ~/.hermes/hermes-agent. Tests use tmp_path HERMES_HOME fixtures.
- safety-and-non-execution: no plan step ever modifies ~/.hermes/hermes-agent; the cap raise is Script #1 only, with --target REQUIRED; the runtime monkey-patch is gone; the migration note is 3 files, source-controlled.
- migration-fidelity: every Claude-specific invocation in T3 inventory is mapped to a Hermes equivalent with a test-id; the T3 inventory is enumerated in the plan; tool names match hermesSkillConventions.json.

OUTPUT: JSON matching PLAN_REVIEW_SCHEMA. blockers[] is REQUIRED even if empty (distinguish from findings[]).`, {
  label: 'reviewPlanV2:' + lens, phase: 'VerifyPlanV2', agentType: 'general-purpose', schema: PLAN_REVIEW_SCHEMA,
})))

// Extract blockers across lenses -- avoid reduce/filter+spread+literal-=== (TS parser issues)
const allBlockers = []
const allFindings = []
for (const r of (reviews || [])) {
  if (!r) continue
  const bs = r.blockers || []
  for (let i = 0; i < bs.length; i++) {
    const merged = { lens: r.lens }
    const src = bs[i]
    for (const k in src) merged[k] = src[k]
    allBlockers.push(merged)
  }
  const fs = r.findings || []
  for (let i = 0; i < fs.length; i++) {
    const merged = { lens: r.lens }
    const src = fs[i]
    for (const k in src) merged[k] = src[k]
    allFindings.push(merged)
  }
}
let overallVerdict = 'block'
if (allBlockers.length == 0) overallVerdict = 'approved'
else if (allBlockers.length <= 3) overallVerdict = 'request-changes'

let planLineCountTotal = 0
const planFilesOverBudget = []
const pfs = (planFiles && planFiles.files) || []
for (let i = 0; i < pfs.length; i++) {
  const lc = pfs[i].lineCount || 0
  planLineCountTotal += lc
  if (lc > 500) planFilesOverBudget.push(pfs[i].filename + '=' + lc)
}
let nMajor = 0, nMinor = 0, nNit = 0
for (let i = 0; i < allFindings.length; i++) {
  const s = String((allFindings[i] && allFindings[i].severity) || '')
  if (s.indexOf('major') === 0) nMajor += 1
  else if (s.indexOf('minor') === 0) nMinor += 1
  else if (s.indexOf('nit') === 0) nNit += 1
}

return {
  diagnose,
  plan: planFiles,
  reviews,
  summary: {
    diagnoseConfirmed: (diagnose && diagnose.confirmedFacts) ? diagnose.confirmedFacts.length : 0,
    diagnoseRefuted: (diagnose && diagnose.refutedClaims) ? diagnose.refutedClaims.length : 0,
    planFilesCount: pfs.length,
    planLineCountTotal,
    planFilesOverBudget,
    reviewsBlockers: allBlockers.length,
    reviewsMajor: nMajor,
    reviewsMinor: nMinor,
    reviewsNit: nNit,
    overallVerdict,
    openQuestionsForHITL: (planFiles && planFiles.openQuestionsForHITL) || [],
  },
  fixLedger: (planFiles && planFiles.fixLedger) || [],
}
