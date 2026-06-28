# Workflows

> [Back to Usage](usage.md)

Three operator workflows: first-time setup, authoring a new skill through
the migrated `skill-creator`, and the daily usage report. Runtime failures
not in [installation-verify](installation-verify.md) are appended below.

Prereqs: clean install per [installation.md](installation.md) and the
three CLIs on `PATH`.

Last verified: 2026-06-27 against `pyproject.toml` (HEAD `76b7cc3`).

---

## Workflow 1: First-time setup

Bootstrap a fresh machine. 1.1-1.2 read-only; 1.3 writes the 8 patches;
1.4-1.5 verify the migrated skill triggers from Hermes.

```bash
# 1.1  Install (development or release artifact) — see docs/installation.md.

# 1.2  Patch audit — would the patcher change anything?
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run \
    --target ~/work/hermes-fork

# 1.3  Patch apply — write the 8 patches (S1.cap + 5 Task E + cache purge)
uv run --locked easter-hermes-sorry-skills-patch-hermes \
    --target ~/work/hermes-fork

# 1.4  Smoke test — confirm the skill is visible to every Hermes profile
uv run --locked easter-hermes-sorry-skills-report --format text

# 1.5  Restart Hermes, then verify the migrated skill triggers
hermes chat -p "Use skill-creator to scaffold a skill called hello-world."
```

`--dry-run` in step 1.2 prints one bilingual line per site. If any site
reports `drifted`, abort and consult [Troubleshooting](#troubleshooting)
— do not run 1.3 against a drifted target. Step 1.3 is atomic per file;
1.4 is read-only; 1.5 confirms the round-trip end-to-end.

---

## Workflow 2: Developing a new skill

Author, validate, register, smoke-test, then commit.

```bash
# 2.1  Inside Hermes, invoke the migrated skill-creator with the intent
hermes chat -p "Use skill-creator to create a skill that wraps 'git status' \
for our support team. The skill should group changes by working-tree vs \
staged and emit a single concise summary line an operator can paste into a ticket."
#      Walks: capture intent -> interview -> draft SKILL.md -> test prompts
#             -> grade -> iterate -> package as .zip.

# 2.2  Validate the generated skill (read-only, fast gate)
uv run --locked python skills/skill-creator/scripts/quick_validate.py \
    skills/git-status-helper

# 2.3  Register the skill with the operator's Hermes install
mkdir -p "${HOME}/.hermes/skills"
ln -sfn "$(pwd)/skills/git-status-helper" "${HOME}/.hermes/skills/git-status-helper"
#      Symlink (not copy) so a `git pull` upgrades in place.

# 2.4  Smoke-test inside Hermes — confirm the skill triggers on the right phrases
hermes chat -p "Why is my commit not showing up?"

# 2.5  (Optional) Commit the new skill to the host repo
git add skills/git-status-helper/
git commit -m "feat(skills): add git-status-helper scaffold"
```

Step 2.2 is the only gate before 2.4 — `quick_validate.py` surfaces the
specific frontmatter / folder-layout rejection. Full skill-creator
contract: [docs/skill-creator.md](skill-creator.md).

---

## Workflow 3: Daily usage report

Read-only view of "what is on right now, and what does it cost?" Safe to
run on cron; no config flips, no per-skill writes.

```bash
# 3.1  Text summary (operator-friendly, sorted by token estimate)
uv run --locked easter-hermes-sorry-skills-report --format text

# 3.2  JSON to stdout — pipe into jq / dashboards
uv run --locked easter-hermes-sorry-skills-report --format json | jq .

# 3.3  Persist JSON to disk — default path ./skill-report.json
uv run --locked easter-hermes-sorry-skills-report --format json \
    --json ./skill-report.json --sort use_count
#      ^ stable across runs (same input -> same bytes), safe to diff day-over-day.
```

Default sort is `tokens`; `--sort use_count` and `--sort last_used_at` are
also valid (see [docs/scripts.md](scripts.md)). Pair step 3.2 with a cron
entry — minute offset from `:00` so fleets across operators don't collide:

```cron
# minute 17, not :00 — cron-fleet desync
17 7 * * *  ubuntu  cd /opt/easter-hermes-sorry-skills && \
                   uv run --locked easter-hermes-sorry-skills-report --format json \
                   --json /var/lib/easter-hermes/daily-$(date +\%F).json
```

---

## Troubleshooting

Install-time failures (`Permission denied`, `LINE_DRIFT`, no-touch sentinel,
missing symlinks) live in [docs/installation-verify.md](installation-verify.md).
This table covers runtime failures AFTER install — symptoms the on-call
engineer sees on day-2+.

| Symptom | Fix |
|---|---|
| Patches written but cap is still 60 chars at runtime | Patcher purges `~/.hermes/.skills_prompt_snapshot.json` on success; manually `rm -f` it and restart Hermes |
| Patch rollback needed (CI red, upstream overrode the cap) | `git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py`. See [patches.md#rollback](patches.md#rollback) |
| `.venv` corrupt or `uv run --locked` fails with import errors | `rm -rf .venv && uv sync --locked --all-extras --dev`. On `uv.lock` mismatch, `uv lock` and audit first |
| `--lang hu` does not switch the default help section | Release artifact built before `--lang` landed (commit `76b7cc3`, PR #47). Rebuild: `scripts/build-release.sh` |
| `Skill 'X' already exists` when registering via `ln -sfn` | `rm -f "${HOME}/.hermes/skills/X"`, then re-create the symlink |
| `report --json` exits non-zero with `Invalid --sort value` | Valid `--sort`: `tokens`, `use_count`, `last_used_at`. See [scripts.md](scripts.md) |
| Bilingual `[hu]` lines missing from output | `uv sync --locked --all-extras --dev`; do NOT hand-edit `messages_en.py` / `messages_hu.py` |

If none match, capture the full `uv run --locked` command, exit code, and
first 10 lines of stderr, then open an issue. The on-call engineer can
replay the exact CLI against the same Hermes checkout to reproduce.

---

Last verified: 2026-06-27.
Back to [Usage](usage.md).