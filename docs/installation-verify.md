# Install — Verify, update, uninstall

> [Back to Installation](installation.md) · [Release artifact](installation-release.md) · [Hermes plugin](installation-hermes.md) · [README](../README.md)

The smoke test that proves a clean install, the common failure modes
it catches, and the upgrade / uninstall workflow.

Last verified: 2026-06-27 against HEAD `76b7cc3`.

---

## Smoke test

Run the relevant block for each install mode you have. Every command
must exit `0`.

### Development install (mode 1)

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-report --version

uv run --locked pre-commit run --files pyproject.toml
uv run --locked pytest
```

After the pre-commit step, every `git commit` runs the gate defined in
`.pre-commit-config.yaml`.

### Release artifact (mode 2)

```bash
easter-hermes-sorry-skills-patch-hermes --version
easter-hermes-sorry-skills-report --version

easter-hermes-sorry-skills-patch-hermes --help --lang en
easter-hermes-sorry-skills-patch-hermes --help --lang hu
easter-hermes-sorry-skills-report --help --lang en

easter-hermes-sorry-skills-report --format text

python3 -m zipfile -l dist/easter-hermes-sorry-skills.pyz | head
./dist/easter-hermes-sorry-skills.pyz -c "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__name__)"

.venv/bin/python3 -c "from easter_hermes_sorry_skills import cli_patch; cli_patch._main_entry()" -- --help
```

The last line is the same call the wrapper makes under the hood;
running it once proves the wrapper's `exec` contract is intact.

### Hermes plugin (mode 3)

```bash
readlink -f ~/.hermes/skills/skill-creator

~/.hermes/hermes-agent --list-skills | grep skill-creator

~/.hermes/hermes-agent --prompt "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__file__)"
```

A clean install prints the version of each CLI, both EN and HU help
sections, and exits each command with `0`. If any command exits
non-zero or the `.pyz` is missing `site-packages/` in the zip listing,
the install is broken; do NOT proceed to [docs/usage.md](usage.md);
instead go to the troubleshooting table below. The matching `bats`
checks live at `tests/bats/{patch-hermes,report}.bats`.

---

## Troubleshooting

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `error: Python 3.13 or older is not supported` | `requires-python = ">=3.14"` (`pyproject.toml:6`) failed; `python3` resolves to < 3.14 | Install Python 3.14 and re-export `PATH`; or pass `--python 3.14` to `uv sync` |
| 2 | `uv: command not found` | `uv` not on `PATH` (dev mode only) | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh`, then re-source your shell profile |
| 3 | `shiv: command not found` (build machine only; release artifact UNTOUCHED) | `shiv>=1.0,<2.0` was not installed into the venv | `uv sync --locked --all-extras --dev` once on the dev machine; `scripts/build-release.sh` installs `shiv` at build time |
| 4 | `.venv/bin/python3: No such file or directory` | Fresh checkout with no venv bootstrap | `uv sync --locked --all-extras --dev` once; subsequent commands expect `.venv/` to exist |
| 5 | `easter-hermes-sorry-skills-patch-hermes: command not found` (dev install) | Ran the wrapper without `uv run --locked` | Prefix with `uv run --locked`, or use `.venv/bin/easter-hermes-sorry-skills-patch-hermes` directly |
| 6 | `Permission denied` when applying patches to a Hermes checkout | The checkout is read-only or owned by another user | `chown -R "${USER}": /path/to/user-hermes`; the patcher exits with code 3 on permission failures |
| 7 | `Skill not found` from `~/.hermes/hermes-agent` | Symlink broken or `skills_dirs` missing in `~/.hermes/hermes-agent.yaml` | `readlink -f ~/.hermes/skills/skill-creator` should resolve; add `skills_dirs: [~/.hermes/skills]` |
| 8 | `JSON parse error` from `easter-hermes-sorry-skills-report` | `~/.hermes/hermes-agent.yaml` is malformed (manual edit dropped a quote) | `python3 -c "import yaml; yaml.safe_load(open('${HOME}/.hermes/hermes-agent.yaml'))"`; restore from backup |
| 9 | `--lang hu` section is missing or `--help` prints only `[en]` | Custom `--help` override dropped a section, or running on Python 3.13 (3.14 required for bilingual tables) | Regenerate via `uv sync --locked --all-extras --dev`; do NOT hand-edit `messages_en.py` / `messages_hu.py`; verify `python3 --version` reports 3.14.x |

If none of the above matches, capture the full command, its exit code,
and the first 10 lines of stderr, and open an issue.

---

## Updating

A new release follows three steps. Steps 1-2 assume you are tracking
the repo via `git pull`; step 3 is the artifact upgrade.

```bash
# 1. Development: pull and refresh the venv
git pull origin main
uv sync --locked --all-extras --dev

# 2. Release artifact: download the new tarball and replace
curl -L -o easter-hermes-sorry-skills.tar.gz \
  https://github.com/EggProject/easter-skills-hack-to-hermes/releases/download/<NEW_VERSION>/easter-hermes-sorry-skills-<NEW_VERSION>.tar.gz
tar -xzf easter-hermes-sorry-skills.tar.gz --overwrite
cd easter-hermes-sorry-skills-<NEW_VERSION>/
ln -sf "$(pwd)/scripts/easter-hermes-sorry-skills-*.sh" ~/bin/
ln -sf "$(pwd)/dist/easter-hermes-sorry-skills.pyz" ~/bin/

# 3. Hermes plugin: re-create the symlink (it points at the repo, so step 1 covers it)
ln -sf "$(pwd)/skills/skill-creator" ~/.hermes/skills/skill-creator
```

For a system-wide release upgrade:

```bash
sudo cp easter-hermes-sorry-skills-<NEW_VERSION>/scripts/easter-hermes-sorry-skills-*.sh /usr/local/bin/
sudo cp easter-hermes-sorry-skills-<NEW_VERSION>/dist/easter-hermes-sorry-skills.pyz /usr/local/bin/
```

After any update, re-run the [Smoke test](#smoke-test) section. A note
on `pyproject.toml:6` (`requires-python = ">=3.14"`): a release that
bumps the floor will refuse to install on the old interpreter. Check
the release notes first if `uv sync` starts failing on a previously
clean machine.

---

## Uninstalling

```bash
# 1. Development: drop the venv
rm -rf .venv

# 2. Release artifact: drop the wrappers + .pyz
rm -rf ~/bin/easter-hermes-sorry-skills-* ~/bin/easter-hermes-sorry-skills.pyz
# Or, for a system-wide install:
sudo rm -f /usr/local/bin/easter-hermes-sorry-skills.pyz
sudo rm -f /usr/local/bin/easter-hermes-sorry-skills-{patch-hermes,report}.sh

# 3. Hermes plugin: drop the symlink + plugin tree
rm -f  ~/.hermes/skills/skill-creator                                # the symlink
rm -rf ~/.hermes/python-extras/easter_hermes_sorry_skills            # the plugin tree

# 4. Restore ~/.hermes/hermes-agent.yaml (if you modified it)
cp ~/.hermes/hermes-agent.yaml.bak ~/.hermes/hermes-agent.yaml      # if you made a backup

# 5. Revert the 8 patches (Hermes-side; per Hermes checkout)
cd /path/to/user-hermes
git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py
```

Step 5 only matters if you installed in mode 3 against a user-owned
Hermes checkout. Steps 1-4 are the canonical uninstall for modes 1
and 2. The plugin's one-time advisory marker
(`~/.hermes/.easter_hermes_sorry_skills_advisory_seen`) is left in
place on purpose; delete it manually if you want the advisory to
re-fire after a re-install.

To also remove build artifacts from the repo (dev mode only):

```bash
git clean -fdx dist/
```

This drops `dist/*.pyz` and `dist/*.tar.gz`.

---

Last verified: 2026-06-27 against HEAD `76b7cc3`.
Back to [Installation](installation.md) · [Release artifact](installation-release.md) · [Hermes plugin](installation-hermes.md)
