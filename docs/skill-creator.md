# The skill-creator skill

> [English](skill-creator.md) · [Magyar verzió](skill-creator.hu.md)
> [Back to README](../README.md)

## What it is

`skill-creator` is a port of Anthropic's `claude-plugins-official` skill-creator,
adapted from Claude Code to run inside Hermes. It lives in
`skills/skill-creator/` and is installed **flat** into the user's agent runtime
by installer Script #2 — it is **not** bundled inside the plugin.

The skill guides an agent through the full skill-authoring loop: capture intent,
interview the user, draft `SKILL.md`, run test prompts, evaluate with graders
and benchmarks, and iterate on the description for better triggering.

> Source: `skills/skill-creator/SKILL.md` (447 lines), frontmatter declares
> `compatibility: Compatible with Hermes Agent SDK and Claude Code`.

## Why we need it

Hermes users hit the 60-character `description` cap on skill frontmatter and
have no built-in way to author, validate, or benchmark new skills. Without
`skill-creator`, iteration on a skill's description is a manual guess — and
the skill may silently undertrigger. This skill ships the full eval harness
(`run_eval.py`, `aggregate_benchmark.py`, `improve_description.py`,
`quick_validate.py`, `package_skill.py`) so authors can measure whether a
change actually moves the needle.

## What we modified (high-level)

The port keeps the upstream skill-creator workflow; only the plumbing changes.
For the D4–D24 decision rationale, see [`migration.md`](migration.md).

- **Frontmatter** — added `compatibility: Compatible with Hermes Agent SDK and Claude Code`.
- **Command substitution** — `claude -p` replaced with `hermes chat -q` everywhere (`scripts/run_eval.py:38`, `scripts/improve_description.py:27`).
- **Artifact rename** — packaged skill files are now `.zip` (via `zipfile.ZipFile`, `scripts/package_skill.py:91`) instead of Claude's `.skill` blob.
- **Trigger detection** — replaced the 130-line NDJSON parser with a read of `hermes sessions export --session-id <sid>` ShareGPT-flavored JSONL (`scripts/run_eval.py:80-86`).
- **New helper** — `scripts/_subprocess.py:hermes_subprocess_env(extra_vars_to_strip=None)` returns a sanitized env dict for spawning Hermes subprocesses. Does **not** auto-strip `CLAUDECODE` (Hermes has no Anthropic-specific nesting guard; for nested isolation use `hermes -p <profile>` or `HERMES_HOME`).
- **Walker drop** — the Claude root-walker that recursed into upstream Claude's `.claude/` project-root directory is gone; packaging uses `skill_path.parent` to locate siblings (`scripts/package_skill.py:53`).
- **Surface trim** — Claude.ai and Cowork sections deleted from the upstream body.
- **Leaf agents in YAML** — `agents/analyzer.md`, `agents/comparator.md`, `agents/grader.md` are now wrapped in YAML frontmatter (`name`, `description`, `goal`, `toolsets`, `role: leaf`) and call `delegate_task(goal=..., context=..., toolsets=[...], role="leaf", max_iterations=N)`.
- **Eval-run IDs** — `with_skill|without_skill` renamed to `skill_active|baseline` (`scripts/aggregate_benchmark.py:7,20–33,214–215`).

## File structure

```
skills/skill-creator/
├── SKILL.md                       # top-level prompt (447 lines)
├── LICENSE.txt                    # Anthropic license (201 lines)
├── agents/
│   ├── analyzer.md                # post-hoc blind-comparison analyzer (296 lines)
│   ├── comparator.md              # blind A/B comparator (224 lines)
│   └── grader.md                  # assertion-based grader (245 lines)
├── eval-viewer/
│   ├── generate_review.py         # eval review generator (471 lines)
│   └── viewer.html                # standalone web viewer (1325 lines)
├── references/
│   └── schemas.md                 # ShareGPT / session schemas (430 lines)
├── assets/
│   └── eval_review.html           # eval review template asset
└── scripts/
    ├── _subprocess.py             # hermes_subprocess_env helper (38 lines)
    ├── aggregate_benchmark.py     # benchmark variance + delta (401 lines)
    ├── generate_report.py         # markdown report writer (326 lines)
    ├── improve_description.py     # desc optimizer via hermes chat (245 lines)
    ├── package_skill.py           # skill -> .zip packager (136 lines)
    ├── quick_validate.py          # frontmatter + structure validator (102 lines)
    ├── run_eval.py                # eval harness with hermes sessions export (260 lines)
    ├── run_loop.py                # multi-iteration eval driver (329 lines)
    └── utils.py                   # parse_skill_md + shared helpers (47 lines)
```

## Usage

Validate a draft skill, then package it for distribution. The package helper
returns the absolute path of the resulting `.zip`.

```bash
# 1. Validate frontmatter and folder layout
uv run python skills/skill-creator/scripts/quick_validate.py skills/my-skill

# 2. Package the skill into a distributable .zip
uv run python skills/skill-creator/scripts/package_skill.py \
    skills/my-skill ./dist

# 3. (Optional) Run the eval harness against a test prompt set
uv run python skills/skill-creator/scripts/run_eval.py \
    --skill skills/my-skill \
    --eval-set evals/my-skill/evals.json
```

Each script reads the skill's `SKILL.md` via `parse_skill_md` (in
`scripts/utils.py`) and respects `skill-creator`'s conventions for
`compatibility`, `description`, and folder layout.

## Eval loop

### Eval loop at a glance

1. `quick_validate.py` — gate before any eval run; rejects malformed
   frontmatter or missing required folders.
2. `run_eval.py` — spawns `hermes chat -q` per prompt, captures the session
   via `hermes sessions export --session-id <sid>`, and grades the result.
3. `aggregate_benchmark.py` — folds the per-run JSON into
   `skill_active` vs `baseline` rollups (mean pass rate, time, tokens) and
   the variance that lets you tell signal from noise.
4. `generate_report.py` — renders a human-readable markdown report from the
   aggregated JSON.
5. `improve_description.py` — when the description undertriggers, this script
   proposes a rewrite by asking Hermes to compare the current description
   against the eval transcripts.

The eval web UI (`eval-viewer/viewer.html` + `eval-viewer/generate_review.py`)
is opened by the parent `SKILL.md` workflow so a human can grade the runs
qualitatively.

### Leaf agents

The three leaf agents (`agents/analyzer.md`, `agents/comparator.md`,
`agents/grader.md`) are invoked through `delegate_task` with `role: leaf`.
They are not callable from the shell directly — they participate in the
eval/iterate loop the parent `SKILL.md` orchestrates.

## See also

- [Patches](patches.md) — how the cap-raise unblocks skill descriptions longer than 60 characters.
- [Source skill](../skills/skill-creator/SKILL.md) — the prompt the model actually reads at runtime.
- D4–D24 decision rationale lives in the upstream migration dossier (not in this worktree).