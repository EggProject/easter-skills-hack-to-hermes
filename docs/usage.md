# Usage

> [Back to README](../README.md)

The operator-facing surface of `easter-hermes-sorry-skills` after install:
the four-step quick start, the three CLIs at a glance, and the migrated
`skill-creator` skill. Deeper reference lives in the linked pages — this
file points at them instead of duplicating.

Read [docs/installation.md](installation.md) first if the CLIs are not on
`PATH`. Flag reference: [scripts.md](scripts.md). Patcher internals:
[patches.md](patches.md). The skill: [skill-creator.md](skill-creator.md).
Workflows: [workflows.md](workflows.md).

Last verified: 2026-06-27 against `pyproject.toml` (HEAD `76b7cc3`).

---

## Quick start

Four operator commands. Steps 1-2 are read-only; step 3 writes; step 4
verifies.

```bash
# 1. Install (development or release artifact)
#    See docs/installation.md

# 2. Patch audit (dry-run) — what would the patcher change?
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run \
    --target /path/to/user-hermes

# 3. Patch apply — write the 8 patches
uv run --locked easter-hermes-sorry-skills-patch-hermes \
    --target /path/to/user-hermes

# 4. Smoke test — verify the skill is visible to Hermes
uv run --locked easter-hermes-sorry-skills-install-profiles
uv run --locked easter-hermes-sorry-skills-report
```

If step 2 reports any site as `drifted`, abort and consult the
[Troubleshooting](workflows.md#troubleshooting) section before re-running
step 3. Step 3 is atomic per file (writes go through `<file>.patch.tmp` +
`os.replace`), so a crash mid-run leaves the original untouched. Step 4
is read-only and safe to repeat.

After step 4, restart Hermes and invoke `/skill skill-creator` — see
[The migrated skill-creator skill](#the-migrated-skill-creator-skill).

---

## The three CLIs at a glance

All three are declared as console-script entry points in
`pyproject.toml:33-36` and print bilingual `--help` (English + Hungarian;
switch with `--lang en|hu`). Flag-by-flag tables, exit codes, and the
shell-wrapper contract live in [docs/scripts.md](scripts.md).

- `easter-hermes-sorry-skills-patch-hermes` — Applies the 8 patches
  (S1.cap + 5 Task E sites + skills-cache purge) to a user-owned Hermes
  checkout. Writes by default; pass `--dry-run` to audit only. Refuses
  to touch `~/.hermes/hermes-agent` (the upstream repo).
- `easter-hermes-sorry-skills-install-profiles` — Read-only per-profile
  audit of the migrated `skill-creator` skill across every Hermes
  profile. Rich text tables by default; pass `--json` for
  machine-readable output.
- `easter-hermes-sorry-skills-report` — Read-only operator view: enabled
  skills per profile with token estimates, use counts, and last-used
  timestamps. NO writes except an operator-chosen `--json PATH`;
  NO config flips.

---

## The migrated `skill-creator` skill

Installed flat into the user's Hermes skills directory by installation
mode 3 — it is NOT bundled inside the plugin. Inside Hermes:

```text
/skill skill-creator
```

Or with a request inline from the CLI:

```text
hermes chat -p "Use skill-creator to create a skill that wraps 'git status'."
```

The skill walks the model through capture intent → interview → draft
`SKILL.md` → run evals → grade → iterate → package as `.zip`. Source:
`skills/skill-creator/SKILL.md`. Full per-step contract, eval-harness
details, and the leaf agents (`analyzer`, `comparator`, `grader`):
[docs/skill-creator.md](skill-creator.md).

---

## See only

- [docs/installation.md](installation.md) — three install modes + smoke test
- [docs/scripts.md](scripts.md) — flag-by-flag reference for the three CLIs
- [docs/skill-creator.md](skill-creator.md) — the migrated `skill-creator` skill
- [docs/patches.md](patches.md) — the eight patch sites (S1.cap + 5 Task E sites) and rollback mechanics
- [docs/workflows.md](workflows.md) — common workflows + troubleshooting
- [docs/development.md](development.md) — test, lint, CI, and the worktree + PR workflow

---

Last verified: 2026-06-27.
Back to [README](../README.md).