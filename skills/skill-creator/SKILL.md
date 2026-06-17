---
name: skill-creator
description: |
  Use when authoring, validating, evaluating, or migrating a Hermes skill under
  ~/.hermes/skills/<category>/<name>/. Reads the hermes-agent-skill-authoring
  validator rules and applies them to the skill body, frontmatter, and supporting
  files. Runs the eval pipeline (run_eval -> aggregate_benchmark ->
  generate_report) and produces an HTML viewer for side-by-side review.
version: 0.1.0
author: kiscsicska
license: MIT
metadata:
  hermes:
    tags: [authoring, validation, eval, migration]
    related_skills: [hermes-agent-skill-authoring]
---

# Skill Creator

## Overview

Use this skill when you need to author, validate, evaluate, or migrate a Hermes
skill. The skill is the Hermes-native port of the Anthropic `skill-creator`
(pinned upstream commit `2a40fd2e7c52207aa903bd33fc4c65716126966e`); every
Claude-specific invocation has been replaced with the Hermes equivalent per
the T3 inventory (18 rows; see `MIGRATION.skill-port.md` for the per-binding
table).

## When to Use

- The operator asks to author a new skill and put it under `~/.hermes/skills/`.
- The operator asks to validate an existing skill's frontmatter / body / supporting
  files against the hermes-agent-skill-authoring rules.
- The operator asks to evaluate a candidate skill against a benchmark of test
  cases and produce a side-by-side HTML review.
- The operator asks to migrate a skill that was originally written for a
  non-Hermes host (e.g. Anthropic's skill format) to Hermes's tool-name and
  nesting-guard conventions.

## Common Pitfalls

- **Do NOT use Anthropic tool names.** Hermes tool names are lowercase:
  `read_file`, `write_file`, `patch`, `search_files`, `terminal`, `read_terminal`,
  `execute_code`, `skill_manage`, `skill_view`, `skills_list`, `delegate_task`,
  `mixture_of_agents`, `clarify`, `cronjob`, `todo`, `web_search`, `web_extract`,
  `vision_analyze`, `memory`, `process`, `session_search`, `send_message`. Match
  case-insensitively with `tool_name.lower() in (...)`.
- **Do NOT pop `HERMES_SESSION` from the parent process.** Use
  `hermes_subprocess_env()` from `_subprocess.py` (the single source of truth)
  to construct the subprocess env. The parent process's `HERMES_SESSION` is
  always preserved.
- **Do NOT call the Anthropic CLI for nested invocations.** Use the Hermes
  CLI for any nested call. The Hermes CLI matches Hermes's nesting-detection
  contract.
- **Do NOT bypass the validator.** A skill that fails frontmatter validation
  will not appear in the `<available_skills>` system-prompt index.
- **Do NOT auto-install skill-creator.** The plugin's `on_session_start` hook
  emits an advisory only; the operator runs Script #1 + Script #2 explicitly.

## Verification Checklist

- [ ] `skill_manage(action='validate', name='<name>')` exits 0.
- [ ] Description length <= 60 (in `SKILL.md.short`) or <= 1024 (in `SKILL.md`)
      per the active cap.
- [ ] `metadata.hermes.tags` is a non-empty list of lowercase strings.
- [ ] `metadata.hermes.related_skills` resolves to in-repo skills under
      `~/.hermes/skills/`.
- [ ] Body contains no uppercase tool names outside code fences.
- [ ] Body uses `tool_name.lower()` when matching tool names.
- [ ] No `os.environ.pop('HERMES_SESSION', ...)` anywhere in the skill.
- [ ] No Anthropic-CLI invocations anywhere in `scripts/`.
- [ ] Eval pipeline: `run_eval.py` produces `feedback.json`; `generate_review.py`
      produces the HTML viewer with `feedback.json` referenced via a relative
      path under the same dir.
