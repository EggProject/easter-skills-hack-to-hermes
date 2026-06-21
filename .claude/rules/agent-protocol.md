# Agent Communication Protocol

## Response Schema (agent-to-agent)

### Base schema (all agents)
```yaml
status: ok | error | blocked | needs_input
summary: "<1-2 sentences>"
files_changed: ["<path>"]
files_created: ["<path>"]
errors:
  - file: "<path>"
    line: <number>
    msg: "<description>"
warnings: ["<text>"]
next_action: "<recommended next step>"
spec_task_id: "<task ID>"
attempt_number: <integer>
```

### Additional REQUIRED fields for code-modifying agents
```yaml
# Verification evidence — MANDATORY for code changes
build_exit_code: <number>       # 0 = clean, non-zero = errors
lint_exit_code: <number>      # 0 = clean, non-zero = errors
build_output: "<first 5 lines>" # exact command output
lint_output: "<first 5 lines>" # exact command output

# TypeScript validation evidence — MANDATORY for any .ts/.tsx file change
files_ts_lsp_checked:
  - path: "<file>"
    unresolved_symbols: 0
    duplicate_declarations: 0
    unused_locals: 0
```

**Orchestrator validation**: Missing `build_exit_code` or `lint_exit_code` = automatic REJECT.
Exit codes override status field: `build_exit_code: 2` + `status: ok` → treated as `status: error`.

## Delegation Rules
- Never paste raw code in delegation prompts (reference by file:line)
- Keep delegation prompts under 200 words
- Extract only status/summary/errors from previous agent output
- Each agent operates in isolated fork (no shared context)

## Worker Invocation

### Permission mode (KÖTELEZŐ `acceptEdits`)
- `mode: "acceptEdits"` MINDEN worker subagent-nél — Edit/Write/Read autonóm, de minden Bash parancsot (pnpm, nx, git, gh, docker, rm stb.) a user interaktívan engedélyez.
- `mode: "default"` elkerülendő: triviális Read-et is kérdezi → túl zajos.
- `mode: "bypassPermissions"` TILOS automatikusan. CSAK a user EXPLICIT engedélyével, indoklással (pl. CI non-interactive futás). Automatikus használata elveszi a user kontrollját a veszélyes parancsok felett.
- Ha egy worker Bash permission-re blokkolódik → `SendMessage`-szel folytasd, NE írd át a mode-ot bypass-re.
- **⚠️ Foreground vs background KRITIKUS limitáció (Claude Code bug, 2026-04)**: `acceptEdits` + background → Bash prompt NEM jelenik meg a user-nek → minden Bash automatikusan denied. Ha a worker hosszú Bash pipeline-t futtat, VAGY foreground-ban kell maradnia, VAGY `bypassPermissions` explicit user engedéllyel. Settings allowlist NEM megoldás (subagent nem örökli — issues #22665, #18950, #14714, #28584, #37730).

### Worktree kiosztás
- **ÚJ worktree** (koordinátor cwd = main workspace): `Agent(subagent_type, isolation: "worktree", mode: "acceptEdits", ...)`. Nx worktree generálódik a `.claude/worktrees/agent-*` alatt.
- **MEGLÉVŐ worktree-ben folytatás** (koordinátor cwd = `.claude/worktrees/agent-*`, pl. resume vagy egymást követő subagent ugyanazon a munkán): NINCS `isolation` paraméter — a subagent örökli a koordinátor cwd-jét, ugyanabban a worktree-ben dolgozik, nem hoz létre újat. `mode: "acceptEdits"` marad.
- Koordinátor cwd ellenőrzés indulás előtt: `pwd` → ha `.claude/worktrees/agent-*` alatt áll, folytatás módot indíts (NINCS `isolation`). Ha a fő workspace-ben → új worktree-t hozzál létre (`isolation: "worktree"`).

### Egyéb
- Ha létezik specializált `.claude/agents/` vagy `.claude/skills/` → azt használd
- Worker merge előtt: `/code-review xhigh --fix` EGYENKÉNT minden worker fájlcsoportjára (NE összevonva)
- DA review PASS = 0 finding (CRITICAL + WARNING + INFO + NOTE mind 0). Bármilyen finding → AskUserQuestion

## Review Execution
- ALWAYS sequential: review -> fix -> re-review
- NEVER parallel reviews
- Minimum 2 consecutive clean reviews to pass
- If issues in reviews #1-#3: reviews #4 and #5 mandatory
