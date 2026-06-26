# Install — Hermes plugin

> [Back to Installation](installation.md) · [Verify](installation-verify.md) · [Release artifact](installation-release.md) · [README](../README.md)

Mode 3 wires the migrated `skill-creator` skill into a Hermes runtime
so the agent can discover and invoke it. Independent of modes 1 and 2:
patch a remote Hermes checkout without running the CLIs locally, or
install the CLIs without exposing the skill to the agent.

Last verified: 2026-06-27 against `skills/skill-creator/SKILL.md` (HEAD `76b7cc3`).

---

## Why Hermes plugin?

Modes 1 and 2 install the **CLIs**. Mode 3 makes the migrated
**skill** visible to a Hermes agent. The skill ships as a flat tree
under `skills/skill-creator/` and is exposed by symlinking it into
the user's skills directory (`~/.hermes/skills/` by convention).

- The skill is loaded at Hermes startup; the agent can call `/skill skill-creator`
- Upgrades are a single `git pull` in this repo (the symlink preserves the path)
- Mode 3 alone does not patch the Hermes source. To apply the 8 patches, run `easter-hermes-sorry-skills-patch-hermes --target /path/to/user-hermes` from mode 1 or 2.

Skip mode 3 if you do not need the skill at runtime (operator-only).

---

## Prerequisites

- A user-owned Hermes checkout (the patcher refuses the canonical `~/.hermes/hermes-agent` with exit code 4; see [docs/patches.md](patches.md))
- `easter-hermes-sorry-skills` already installed via mode 1 or mode 2 (mode 3 only wires the skill)
- `~/.hermes/skills/` writable
- `skills/skill-creator/` present in the repo (always shipped; no rebuild)

Clone your own working copy of the upstream Hermes repo and pass that
as `--target` to the patcher.

---

## Install

```bash
# 1. Symlink the skill-creator skill to ~/.hermes/skills/
mkdir -p ~/.hermes/skills
ln -sf "$(pwd)/skills/skill-creator" ~/.hermes/skills/skill-creator

# 2. Verify Hermes picks it up
~/.hermes/hermes-agent --list-skills | grep skill-creator

# 3. (Optional) Make the plugin importable for hermes_cli.plugins discovery
uv pip install --target ~/.hermes/python-extras .
```

Step 1 makes `skill-creator` discoverable to the runtime. The symlink
preserves the absolute repo path, so `git pull` here upgrades the
skill in place.

Step 3 puts `easter_hermes_sorry_skills` on the Python path Hermes
uses (`src/easter_hermes_sorry_skills/_register.py:33-37`). After the
next Hermes restart, the one-time bilingual advisory fires unless the
`S1.cap` patch was applied; the marker
`~/.hermes/.easter_hermes_sorry_skills_advisory_seen` suppresses it.

If your Hermes checkout reads user config from
`~/.hermes/hermes-agent.yaml`, add a `skills_dirs` entry pointing at
`~/.hermes/skills`. The exact key is runtime-specific.

---

## Verify

```bash
# 1. The symlink resolves to a real directory
readlink -f ~/.hermes/skills/skill-creator

# 2. The skill manifest is readable
head -20 ~/.hermes/skills/skill-creator/SKILL.md

# 3. Inside Hermes, invoke the skill
~/.hermes/hermes-agent --list-skills | grep skill-creator
~/.hermes/hermes-agent --prompt "/skill skill-creator"
```

A clean install prints the absolute repo path from `readlink -f`,
shows the SKILL.md frontmatter (`compatibility: hermes` line), and
`--list-skills` includes `skill-creator`. Full smoke battery:
[installation-verify.md](installation-verify.md).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ln: failed to create symbolic link ... File exists` | A previous symlink or real `skill-creator` directory is already at the target | `rm ~/.hermes/skills/skill-creator` and re-run step 1; verify with `ls -la ~/.hermes/skills/` |
| `Skill not found` from `~/.hermes/hermes-agent` | Broken symlink or missing `skills_dirs` config | `readlink -f ~/.hermes/skills/skill-creator` should resolve; add `skills_dirs: [~/.hermes/skills]` to `~/.hermes/hermes-agent.yaml` |
| `Permission denied` on `~/.hermes/skills/` | Directory owned by another user or read-only | `chown -R "${USER}": "${HOME}/.hermes/skills"`; the patcher refuses writes to unreadable user files (exit 3) |
| `~/.hermes/hermes-agent.yaml: parse error` | Manual edit dropped a quote or a key | `python3 -c "import yaml; yaml.safe_load(open('${HOME}/.hermes/hermes-agent.yaml'))"`; restore from backup |
| Bilingual advisory fires repeatedly | Marker file deleted or `S1.cap` not applied | Let the advisory fire once and re-create the marker, or apply S1.cap via the patcher |

---

Last verified: 2026-06-27 against HEAD `76b7cc3`.
Back to [Installation](installation.md) · [Verify](installation-verify.md) · [Release artifact](installation-release.md)
