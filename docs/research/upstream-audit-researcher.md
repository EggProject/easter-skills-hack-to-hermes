# Researcher audit — Anthropic upstream Claude-prompt residues

**Audit lens**: Phase 1 / Agent 1 (researcher). Scope = Claude/Anthropic-specific
prompt residues (system scaffolding, YAML description, agent role descriptions,
SKILL.md body text). Out of scope = Python implementation, JSON schemas, CLI
flags, tool-name mappings (those belong to T3 inventory).

## Upstream SHA

- **Latest main commit on `plugins/skill-creator/skills/skill-creator` subtree**:
  `5fc2987a44918a455ef7dc583b51f8faf875c3ed`
- **Method**: `git ls-remote` + sparse-fetch into `/tmp/upstream-foo-2026-06-22/`
- **Confidence**: **high** (primary source reachable, sparse-checkout materialised,
  byte-level checksum diff produced against the vendored tree)
- **Commit message**: `bump(chrome-devtools-mcp): 38dd3468 → 52cf8c40 (#3163)`
  *(not a skill-creator-targeted commit; main HEAD simply landed past the subtree
  while the subtree itself remained untouched)*
- **Primary URL (commit page)**: https://github.com/anthropics/claude-plugins-official/commit/5fc2987a44918a455ef7dc583b51f8faf875c3ed
- **Confirmation 1 (blame view)**: https://github.com/anthropics/claude-plugins-official/blame/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator/SKILL.md
- **Confirmation 2 (tree view)**: https://github.com/anthropics/claude-plugins-official/tree/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator
- **Raw blob (SKILL.md)**: https://raw.githubusercontent.com/anthropics/claude-plugins-official/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator/SKILL.md

## Vendored baseline

- **Local pinned SHA**: `2a40fd2e7c52207aa903bd33fc4c65716126966e`
- **Pin source**: `docs/research/anthropic-skill-creator-original/UPSTREAM_COMMIT.txt`
- **Local path**: `docs/research/anthropic-skill-creator-original/skills/skill-creator/`
- **Vendored history caveat**: the local copy was materialised into the
  worktree as plain files (not a git submodule). The upstream repo object
  `2a40fd2e...` is NOT reachable from the local vendored repo (`git show
  2a40fd2e...` → `fatal: bad object`). The pin SHA is treated as an
  authoritative external reference (verified against upstream via sparse
  fetch), not as a local git object.

## Diff scope

- **Aggregate SHA-256 (sorted, recursive) of vendored tree**:
  `c471bde8ea02f12b9cc490d117e4fa93ac61ab0e79c6e623e5a2e09ff1c5dc39`
- **Aggregate SHA-256 (sorted, recursive) of upstream tree at `5fc2987`**:
  `c471bde8ea02f12b9cc490d117e4fa93ac61ab0e79c6e623e5a2e09ff1c5dc39`
- **`diff -rq` exit code**: `0` (no differences reported)
- **Per-file SHA-256 diff**: empty (byte-equality confirmed)

### Files compared (18)

```
SKILL.md
LICENSE.txt
agents/analyzer.md
agents/comparator.md
agents/grader.md
assets/eval_review.html
eval-viewer/generate_review.py
eval-viewer/viewer.html
references/schemas.md
scripts/__init__.py
scripts/aggregate_benchmark.py
scripts/generate_report.py
scripts/improve_description.py
scripts/package_skill.py
scripts/quick_validate.py
scripts/run_eval.py
scripts/run_loop.py
scripts/utils.py
```

### Files changed since pinned SHA

**None.** The subtree has received zero commits between
`2a40fd2e7c52207aa903bd33fc4c65716126966e` (2026-04-23) and
`5fc2987a44918a455ef7dc583b51f8faf875c3ed` (2026-06-22).

Adversarial verification of that "zero commits" claim:

```
git log --format='%H %ai %s' -- plugins/skill-creator/skills/skill-creator/
2a40fd2e7c52207aa903bd33fc4c65716126966e  2026-04-23  skill-creator: sync from anthropics/skills (drop ANTHROPIC_API_KEY requirement) (#1523)
e05013d229d375d7a8b7c2b39899f40a22828ca7  2026-02-24  chore(skill-creator): update to latest skill-creator
30975e61e36524bebc30c8e05d0b7e719db228d0  2026-02-17  Add skill-creator plugin
```

`5fc2987a...` (current main HEAD) is reachable from `2a40fd2e...` via main
lineage; the subtree file `plugins/skill-creator/skills/skill-creator` is
identical at the two SHAs.

### Files unchanged

All 18 files listed above.

## Findings (Claude/Anthropic prompt residues only)

### F-R1 — Upstream subtree has been silent since the pin

| field | value |
| --- | --- |
| id | F-R1 |
| upstream file | (all 18) |
| current local file | (all 18) |
| upstream snippet | (no diff) |
| current snippet | (no diff) |
| upstream-evidence | `git log --format='%H %ai %s' -- plugins/skill-creator/skills/skill-creator/` shows zero commits between `2a40fd2e` and `5fc2987a` |
| confirmations | commit page (https://github.com/anthropics/claude-plugins-official/commit/5fc2987a44918a455ef7dc583b51f8faf875c3ed) + tree view (https://github.com/anthropics/claude-plugins-official/tree/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator) |
| classification | **DELIBERATE** (upstream drift = none; no residue added by upstream since pin) |
| confidence | high |

This finding rules out *new* upstream drift as a source of Claude-prompt
residues. The dossier therefore reports a null hypothesis: **no new
prompt residues have entered the upstream subtree since the pin**. The
existing residues (if any) live entirely in the local Hermes port and are
governed by the bilingual-advisory contract documented elsewhere
(`hermes-skills-hitl-decisions.md`, Q4/Q5); they are NOT a researcher-lens
problem.

### F-R2 — Aggregate checksum identity proves tree-level equivalence

| field | value |
| --- | --- |
| id | F-R2 |
| upstream file | tree root |
| current local file | tree root |
| upstream snippet | aggregate SHA-256 = `c471bde8ea02f12b9cc490d117e4fa93ac61ab0e79c6e623e5a2e09ff1c5dc39` |
| current snippet | aggregate SHA-256 = `c471bde8ea02f12b9cc490d117e4fa93ac61ab0e79c6e623e5a2e09ff1c5dc39` |
| upstream-evidence | local sparse checkout `/tmp/upstream-foo-2026-06-22/plugins/skill-creator/skills/skill-creator/` |
| confirmations | `diff -rq` exit 0 + per-file SHA-256 diff exit 0 (cross-confirms F-R1) |
| classification | **DELIBERATE** (informational; supports F-R1) |
| confidence | high |

### F-R3 — Pin SHA provenance is preserved only as a text file

| field | value |
| --- | --- |
| id | F-R3 |
| upstream file | n/a |
| current local file | `docs/research/anthropic-skill-creator-original/UPSTREAM_COMMIT.txt` |
| upstream snippet | n/a (this is a *provenance gap*, not a content diff) |
| current snippet | single-line file containing `2a40fd2e7c52207aa903bd33fc4c65716126966e` |
| upstream-evidence | n/a |
| confirmations | n/a (no upstream counterpart — this is a vendored-tree metadata observation) |
| classification | **NOTE** (vendoring-process observation; not a Claude-prompt residue) |
| confidence | medium (relying on filesystem inspection; the file could be regenerated from the upstream commit URL alone) |

Implication: the local copy is "trust the SHA, verify by checksum" — there
is no git-history link back to upstream. Anyone re-running this audit must
re-sparse-fetch from upstream to re-establish the chain.

### F-R4 — No `bump`, `chore`, or `fix` commits landed on this subtree since the pin

| field | value |
| --- | --- |
| id | F-R4 |
| upstream file | n/a (commit-history fact) |
| current local file | n/a |
| upstream snippet | `git log --since=2026-04-23 --until=2026-06-22 -- plugins/skill-creator/skills/skill-creator/` → empty |
| current snippet | n/a |
| upstream-evidence | unshallow fetch into `/tmp/upstream-foo-2026-06-22/` then `git log` filter (above) |
| confirmations | upstream commit page for `5fc2987` + upstream commit page for `2a40fd2e` (both URLs above) — neither references any skill-creator change post-pin |
| classification | **NOTE** (corroborates F-R1 / F-R2) |
| confidence | high |

### Out-of-scope reminders (not findings; passed to T3 inventory)

The following live in the subtree but were intentionally NOT diffed because
they are not Claude-prompt residues:

- `scripts/*.py` — Python implementation, JSON I/O, CLI parsing
- `references/schemas.md` — JSON/YAML schema documentation
- `eval-viewer/generate_review.py` — static-asset generator
- `eval-viewer/viewer.html` — embedded JS/CSS static viewer
- `assets/eval_review.html` — eval-form template
- `LICENSE.txt` — license text (Anthropic proprietary terms; not a residue
  per se, but a separate legal/inheritance question handled by Phase 6)

## Open questions for Phase 2 synthesizer

1. **No-op or scope-mismatch?** Given that the upstream subtree is silent
   since the pin, is this researcher's job best framed as a *re-audit* of
   the existing Hermes-side bilingual-advisory contract (Q4/Q5), or as a
   *new-finding search* that produced a clean null result? The dossier
   asserts the latter; Phase 2 should confirm.
2. **Provenance policy**: should `UPSTREAM_COMMIT.txt` be replaced with a
   git submodule pointing at `anthropics/claude-plugins-official` pinned
   to `2a40fd2e...`, so the pin is *structural* not *textual*? (NOTE,
   not WARNING — this is a tooling choice.)
3. **Other Anthropic subtrees not in scope here**: the upstream repo also
   contains `plugins/feature-dev/`, `plugins/frontend-design/`, etc. If
   Phase 2 wants a broader Claude-prompt residue survey, those need their
   own researcher passes. Out of scope for this dossier.
4. **Skill-creator upstream activity could resume at any time**: the
   silence-since-pin finding is only valid as of `2026-06-22`. A re-run
   before any sync action is recommended.

## Confidence summary

- **High**: 3 (F-R1, F-R2, F-R4)
- **Medium**: 1 (F-R3)
- **Low**: 0
- **Speculative**: 0

## Sources

| # | URL | type | date | used for |
| --- | --- | --- | --- | --- |
| 1 | https://github.com/anthropics/claude-plugins-official | upstream repo | n/a | scope boundary |
| 2 | https://github.com/anthropics/claude-plugins-official/commit/5fc2987a44918a455ef7dc583b51f8faf875c3ed | commit page | 2026-06-22 | upstream main HEAD primary |
| 3 | https://github.com/anthropics/claude-plugins-official/tree/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator | tree view | 2026-06-22 | upstream confirmation 1 |
| 4 | https://github.com/anthropics/claude-plugins-official/blame/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator/SKILL.md | blame view | 2026-06-22 | upstream confirmation 2 |
| 5 | https://raw.githubusercontent.com/anthropics/claude-plugins-official/5fc2987a44918a455ef7dc583b51f8faf875c3ed/plugins/skill-creator/skills/skill-creator/SKILL.md | raw blob | 2026-06-22 | upstream raw content |
| 6 | https://github.com/anthropics/claude-plugins-official/commit/2a40fd2e7c52207aa903bd33fc4c65716126966e | commit page | 2026-04-23 | pin primary |
| 7 | https://github.com/anthropics/claude-plugins-official/blame/2a40fd2e7c52207aa903bd33fc4c65716126966e/plugins/skill-creator/skills/skill-creator/SKILL.md | blame view | 2026-04-23 | pin confirmation |
| 8 | docs/research/anthropic-skill-creator-original/UPSTREAM_COMMIT.txt | local pin file | vendored | pin text reference |
| 9 | `/tmp/upstream-foo-2026-06-22/plugins/skill-creator/skills/skill-creator/` | local sparse checkout | 2026-06-22 | byte-equality verification |
| 10 | `git log` over subtree path (unshallow) | git history | 2026-06-22 | commit-count claim |