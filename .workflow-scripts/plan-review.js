export const meta = {
  name: 'plan-review-only',
  description: 'Phase 5 elotti 4-lencses adversarial review a 13 tervfajlra (completeness, testability, safety, migration-fidelity)',
  phases: [{ title: 'Review4Lenses' }],
}

const PLAN_DIR = '/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/hermes-skills-dev/plans'
const LENSES = ['completeness-vs-brief', 'testability-and-coverage', 'safety-and-non-execution', 'migration-fidelity']

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['lens', 'overallVerdict', 'blockers', 'findings'],
  additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    overallVerdict: { type: 'string', enum: ['approve', 'request-changes', 'block'] },
    blockers: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['planFile', 'section', 'concern', 'suggestedFix'],
        properties: {
          planFile: { type: 'string' },
          section: { type: 'string' },
          concern: { type: 'string' },
          suggestedFix: { type: 'string' },
        },
      },
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['severity', 'planFile', 'section', 'concern', 'suggestedFix'],
        properties: {
          severity: { type: 'string', enum: ['nit', 'minor', 'major', 'blocker'] },
          planFile: { type: 'string' },
          section: { type: 'string' },
          concern: { type: 'string' },
          suggestedFix: { type: 'string' },
        },
      },
    },
  },
}

const PROMPT = `You are an adversarial plan reviewer. Your lens: {LENS}.

PLAN FILES: read all 13 files in ${PLAN_DIR}/ (00-index.md, 01-overview.md, 02-architecture.md, 03-plugin-spec.md, 04-script-1-patch.md, 05-script-1-task-e-toggle.md, 06-script-2-profiles.md, 07-skill-creator-migration.md, 08-migration-note-format.md, 09-test-strategy.md, 10-toolchain-and-conventions.md, 11-sub-agent-delegation-map.md, 12-risks-and-open-questions.md). Total ~2088 lines.

SUPPORTING ARTEFACTS — consult when needed (read these files, do NOT trust V1 review blindly):
- ${PLAN_DIR}/_diagnose.md (Diagnose output: 10 confirmed, 13 refuted, 4 revised, 9 blocker fix list, 9 open questions)
- ${PLAN_DIR}/_research/*.json (6 research topics: truncation, anthropicCreator, hermesSkillConventions, pluginAuthoring, profileSystem, taskECandidates)
- ${PLAN_DIR}/_plan_reviews.md (V1 review from PlanRepair V1 — 9 blockers should be FIXED in V2; verify the fixes landed)
- ${PLAN_DIR}/_synthesis.md (Synthesized research brief)
- /Users/kiscsicska/projects/easter-skills-hack-to-hermes-2/.claude/worktrees/hermes-skills-dev/docs/maybe-patch-points.md (Task E spec; 7 sites)

EVIDENCE OF TRUTH (use Read on these when verifying plan claims):
- Hermes install (READ-ONLY, NEVER modify): /Users/kiscsicska/.hermes/hermes-agent (NousResearch/hermes-agent v0.16.0, commit 368fcf1ff)
- Truncation site: agent/skill_utils.py lines 644-655 (function def + 57+3 truncation)
- Truncation call site: agent/prompt_builder.py line 1090
- Truncation cap also at: tools/skills_tool.py line 95 (MAX_DESCRIPTION_LENGTH = 1024)
- GitHub issue: https://github.com/NousResearch/hermes-agent/issues/46005
- Anthropic upstream: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator
- Anthropic pinned commit: 2a40fd2e7c52207aa903bd33fc4c65716126966e

YOUR LENS-SPECIFIC CHECKS:
- completeness-vs-brief: Every Sec 5.1..5.7 + Sec 6.A..6.E + Sec 8 + Sec 10 acceptance criterion in the brief is covered with implementation-level detail in the plan.
- testability-and-coverage: Every code file has a TDD test list that achieves 100% code + 100% logic coverage WITHOUT running scripts against ~/.hermes/hermes-agent. Tests use tmp_path HERMES_HOME fixtures.
- safety-and-non-execution: No plan step ever modifies ~/.hermes/hermes-agent. The cap raise is Script #1 only, with --target REQUIRED. The runtime monkey-patch is GONE. The migration note is 3 files, source-controlled. The plugin is advisory-only.
- migration-fidelity: Every Claude-specific invocation in the T3 inventory is mapped to a Hermes equivalent with a test-id. The T3 inventory is enumerated. Tool names match hermesSkillConventions.json. Nesting-guard var is HERMES_SESSION per E1.

INSTRUCTIONS:
- Read the plan files with the Read tool. Verify every claim against the research JSONs.
- Find concrete gaps. Tie each finding to a specific plan file + section.
- Severity: nit / minor / major / blocker. A 'blocker' must justify why Phase 5 cannot start.
- If the plan addresses the V1 blockers (in _plan_reviews.md), note that as a positive; if it does NOT, file a blocker.
- DO NOT trust the plan. Re-derive each claim from the research JSONs.
- DO NOT modify any file — read-only.

OUTPUT: JSON matching REVIEW_SCHEMA. blockers[] is REQUIRED even if empty (distinguish from findings[]).`

phase('Review4Lenses')
const reviews = await parallel(LENSES.map(lens => () => agent(PROMPT.replace('{LENS}', lens), {
  label: 'review:' + lens, phase: 'Review4Lenses', agentType: 'Explore', schema: REVIEW_SCHEMA,
})))

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

return {
  reviews,
  summary: {
    reviewsCount: reviews.length,
    blockersCount: allBlockers.length,
    findingsCount: allFindings.length,
    overallVerdict,
  },
  allBlockers,
  allFindings,
}
