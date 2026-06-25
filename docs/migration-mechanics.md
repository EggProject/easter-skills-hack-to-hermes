# Migration mechanics & dossier

> [Magyar verzió](migration-mechanics.hu.md) · [Back to README](../README.md)
> [Decision log](migration.md)

This page is the mechanics half of the migration story — context, upstream
pin, how to read the generated patch, and the `research/` artifact map.
The per-binding rationale lives on the [Decision log](migration.md).

## Context

The `skills/skill-creator/` tree in this repo is a **port** of Anthropic's
upstream `skill-creator` skill, adapted from Claude Code to run inside Hermes.
The port keeps the upstream workflow; only the plumbing changes.

The migration touches three layers:

1. **Frontmatter contract** — declaring dual-runtime compatibility so the same
   `SKILL.md` works in Hermes Agent SDK and Claude Code.
2. **Subprocess plumbing** — `claude -p` replaced with `hermes chat -q`, and
   the `CLAUDECODE` strip is no longer needed.
3. **Eval pipeline** — NDJSON stream parsing replaced with a read of
   `hermes sessions export` ShareGPT-flavored JSONL.

The full upstream-binding dossier lives at
`skills/migration-claude-skill-creator/`. This page is the readable summary.

## Upstream pin

The port pins to upstream commit
`5fc2987a44918a455ef7dc583b51f8faf875c3ed` of
`anthropics/claude-plugins-official`. Metadata recorded in
`skills/migration-claude-skill-creator/UPSTREAM_COMMIT.txt`:

- **Source tree**: `plugins/skill-creator/skills/skill-creator`
- **Fetched at**: 2026-06-22T17:36:25Z
- **Files**: 18, total 225 004 bytes
- **Per-file SHA-256**: see
  `skills/migration-claude-skill-creator/research/upstream_commit.json`

Pinning by commit SHA (not branch) makes the migration diff reproducible —
`MIGRATION.patch` is a unified diff applied to that exact tree.

## Reading `MIGRATION.patch`

`MIGRATION.patch` (31 529 bytes) is a unified diff between the upstream
tree at the pinned commit and the migrated `skills/skill-creator/` tree.
It is generated, not hand-written — apply the upstream commit and pipe
the patch through `git apply` to reproduce the migration verbatim.

Useful conventions when reading the patch:

- Path prefixes — `upstream-skill-creator-5fc2987/...` (left side) vs the
  worktree path (right side). The right side is what lands in the repo.
- `Only in` markers — denote new files introduced by the migration (e.g.
  `scripts/_subprocess.py`). They do not have a left side.
- Anchor blocks — every binding cites a 5-line anchor (`---` excerpt)
  from the **upstream** side so the binding is recoverable from the diff
  alone, without re-reading the migrated source.

## `research/`

Pre-migration research artifacts live in
`skills/migration-claude-skill-creator/research/`:

- `binding_sites_*.json` — per-language binding-site registries
  (agents, docs, NDJSON parser, Python scripts, validation) cataloguing
  every line that the migration touches.
- `code_review_findings.json` / `code_review_findings_r2.json` — review
  rounds 1 and 2 on the generated patch.
- `hermes_mapping.json` — the upstream-symbol → Hermes-symbol table used
  to drive the substitution.
- `migrations_applied.json` — machine-readable mirror of the per-binding
  table in `MIGRATION.md`.
- `session_inspection_verdict.json` — verdict on whether `hermes sessions
  export` JSONL contains enough structure to replace the NDJSON parser.
- `upstream_commit.json` — full per-file SHA-256 + byte counts for the
  pinned commit.

## See also

- [Decision log](migration.md) — the 10 binding entries
  (D4, D5/D11, D15, D16, D17, D18, D20, D21/D22, D23, D24).
- [Skill-creator](skill-creator.md) — overview of the migrated skill.
- [Patches](patches.md) — the cap-raise + Task E site patches applied to
  the Hermes checkout itself.
- [Source migration dossier](../skills/migration-claude-skill-creator/MIGRATION.md)
  — the generated per-binding table and decision log.
