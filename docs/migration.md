# Migration: claude-plugins-official → Hermes

> [Magyar verzió](migration.hu.md) · [Back to README](../README.md)
> [Mechanics & dossier](migration-mechanics.md)

## Decision log

Each decision below is one binding in `MIGRATION.md`. Format is
**Problem · Choice · Rationale** so the why is recoverable without
reading the diff. Context, the upstream pin, and the `research/` artifact
map live on the [Mechanics](migration-mechanics.md) page.

### D4 — Artifact rename (`.skill` → `.zip`)

**Problem** — Claude Code packages skills as `.skill` blobs, but the
underlying archive format is plain ZIP. Hermes does not recognize the
`.skill` extension and packages skills as `.zip` directly.

**Choice** — Rename every `.skill` reference in `SKILL.md` and
`scripts/package_skill.py` to `.zip`. The output filename is
`{skill_name}.zip`; the on-disk archive format is unchanged.

**Rationale** — Dropping the Claude-Code-specific extension removes a
host-specific fork risk and makes the artifact portable to any ZIP
reader. The packaging logic (`zipfile.ZipFile(...)` with `ZIP_DEFLATED`)
is unchanged.

### D5 / D11 — `compatibility` frontmatter

**Problem** — Downstream hosts need to know whether a skill supports their runtime without forking the skill or reading its prose.

**Choice** — Add a top-level `compatibility` field to `SKILL.md` frontmatter declaring the runtimes the skill supports. When dual-compatible, this field is the canonical signal — preferred over `claude_compatible`-style sidecar flags.

**Rationale** — A single declarative field is greppable, machine-checkable, and survives runtime upgrades. Current value: `Compatible with Hermes Agent SDK and Claude Code`.

### D15 — Command substitution (`claude -p` → `hermes chat -q`)

**Problem** — `claude -p` is the Claude-Code CLI surface; Hermes has its own equivalent CLI surface that the eval harness must use instead.

**Choice** — Replace every `claude -p <query> --output-format stream-json` invocation with `hermes chat -q <query> --output-format json`. The `--model` argument semantics are preserved (`if model: cmd.extend(["--model", model])`, `scripts/run_eval.py:41-42`).

**Rationale** — `hermes chat -q` keeps the same prompt-in / stdout-out contract and `--model` argument semantics, so the swap is mechanical and the eval harness logic stays intact. The output format switches from NDJSON to JSON because the ShareGPT JSONL session export (D22) replaces the streaming parser.

### D16 — `hermes_subprocess_env()` helper

**Problem** — `claude -p` requires `CLAUDECODE` to be stripped before spawning a nested CLI session (it guards against interactive terminal conflicts). Hermes has no equivalent guard, and the existing `{k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` pattern fragments across scripts.

**Choice** — Introduce `scripts/_subprocess.py:hermes_subprocess_env(extra_vars_to_strip=None)` as the single helper that builds the subprocess env. By default it **preserves all vars** — including `CLAUDECODE`. For nested isolation, use `hermes -p <profile>` or a `HERMES_HOME` override, not env stripping.

**Rationale** — Stripping `CLAUDECODE` for Hermes is a category error: Hermes doesn't read it, and silent stripping hides config bugs. A named helper also gives nested-Hermes callers an obvious escape hatch (`extra_vars_to_strip=...`).

### D17 — `.claude/` project-root walker dropped

> Note: `.claude/` here means upstream Claude's project-root config tree (the thing being removed), not this project's own `.claude/rules/` config files.

**Problem** — `run_eval.py:find_project_root()` walked up from `cwd` looking for a `.claude/` directory to stage command files in. With Hermes, the skill path is the unit of deployment; there is no `.claude/commands/` staging area to discover.

**Choice** — Delete `find_project_root()`. Derive the project root inline as `skill_path.parent` in both `run_eval.py` and `run_loop.py`. Drop the `project_commands_dir = Path(project_root) / ".claude" / "commands"` branch entirely.

**Rationale** — `skill_path.parent` is always correct (the eval runs from the skill's own directory), removes a fragile filesystem walk, and eliminates a category of race conditions where two concurrent eval runs trash each other's staged command files.

### D18 — Claude.ai + Cowork sections deleted

**Problem** — The upstream `SKILL.md` contains two large sections (`## Claude.ai-specific instructions`, `## Cowork-Specific Instructions`) that describe workflows tied to those hosts' toolset and UI. They are noise inside Hermes and refer to mechanics that do not exist here (e.g. Claude.ai's no-subagents regime, Cowork's static-HTML eval viewer).

**Choice** — Delete both sections. Rewrite remaining `claude-with-access-to-the-skill` mentions to `hermes-with-access-to-the-skill`.

**Rationale** — The deleted content is host-specific operational guidance that the Hermes skill-creator workflow does not need. Rewriting the remaining mentions keeps the prose self-consistent.

### D20 — Leaf-agent YAML frontmatter wrapper

**Problem** — Hermes dispatches agents through `delegate_task` with a structured contract (`goal`, `context`, `toolsets`, `role`). Claude Code agents are bare Markdown files with H1 headings.

**Choice** — Wrap each leaf-agent Markdown in YAML frontmatter declaring `name`, `description`, `goal`, `toolsets`, `role: leaf`. Apply to `agents/analyzer.md`, `agents/comparator.md`, `agents/grader.md`.

**Rationale** — A structured frontmatter makes the dispatch contract explicit at the file level and lets `delegate_task` route by metadata rather than prose parsing. The original H1 heading is retained as the agent body so grep-and-read workflows still work.

### D21 / D22 — ShareGPT JSONL session export

**Problem** — The upstream eval harness parses a 130-line NDJSON stream from `claude -p --include-partial-messages`, dispatching on `stream_event`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_stop`, `assistant`, `result`, and accumulating `input_json_delta` to detect a `Skill` or `Read` tool_use before the assistant message arrives. This is fragile, Claude-stream-specific, and adds significant complexity.

**Choice** — Replace the NDJSON parser with two subprocess calls:

1. `hermes chat -q <query> --output-format json` (returns the session id).
2. `hermes sessions export --session-id <sid> <tmp.jsonl>` (writes a ShareGPT-flavored JSONL transcript).

Iterate the JSONL line by line; for each assistant turn, look for a tool_use block whose `arguments.skill` matches the candidate skill name (in the cleaned `skill_name-eval-<id>` form).

**Rationale** — The session export is a single source of truth that Hermes already produces; iterating JSONL is ~70 lines of trivial Python versus 130 lines of stateful stream parsing. The cost is that trigger detection now happens **after** the chat completes, not mid-stream — acceptable because eval throughput is the bottleneck, not tail latency.

### D23 — Eval-run ID rename (`with_skill|without_skill` → `skill_active|baseline`)

**Problem** — The upstream viewer, schemas, aggregate script, and `SKILL.md` prose all key off `with_skill` / `without_skill` (with `new_skill` / `old_skill` aliases for iteration runs). The names encode Claude-Code naming and don't survive into Hermes iteration flows.

**Choice** — Rename across the whole skill surface:

| Old | New |
|---|---|
| `with_skill` | `skill_active` |
| `without_skill` | `baseline` |
| `new_skill` | `skill_iter_n` |
| `old_skill` | `skill_iter_prev` |

Affects `eval-viewer/viewer.html:716` regex, `references/schemas.md:239`, `scripts/aggregate_benchmark.py:7`, `SKILL.md:181` path examples, and `agents/analyzer.md:230`.

**Rationale** — The new names describe what the run **means** (active skill vs baseline; nth iteration vs previous) rather than which host produced them. The viewer stays semantically correct across Hermes iteration runs.

### D24 — `delegate_task` leaf pattern

**Problem** — Hermes dispatches leaf agents through `delegate_task` with a structured signature. The leaf agents need an explicit invocation contract so the dispatcher knows what goal, context, toolsets, and iteration cap to apply.

**Choice** — The canonical leaf invocation is:

```
delegate_task(
    goal="<one-sentence goal>",
    context="<comma-separated bound variable names>",
    toolsets=["<toolset-1>", "<toolset-2>"],
    role="leaf",
    max_iterations=N,
)
```

**Rationale** — A single, named signature makes leaf dispatch auditable. `max_iterations=N` bounds runaway loops; `toolsets=[...]` scopes the agent to the minimum toolset it needs.

## See also

- [Mechanics & dossier](migration-mechanics.md) — context, upstream pin,
  and the `research/` artifact map.
- [Skill-creator](skill-creator.md) — overview of the migrated skill.
- [Patches](patches.md) — the cap-raise + Task E site patches applied to
  the Hermes checkout itself.
- [Source migration dossier](../skills/migration-claude-skill-creator/MIGRATION.md)
  — the generated per-binding table and decision log.
