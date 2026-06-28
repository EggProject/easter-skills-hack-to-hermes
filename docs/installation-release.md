# Install — Release artifact

> [Back to Installation](installation.md) · [Verify](installation-verify.md) · [Hermes plugin](installation-hermes.md) · [README](../README.md)

Mode 2: drop a self-contained `.pyz` + three bash wrappers on `PATH`.
No source tree, no `uv`, no `pip`. Use on operator hosts and CI runners
that only need to run the three CLIs.

Last verified: 2026-06-27 against `dist/easter-hermes-sorry-skills-v0.1.0.tar.gz` (HEAD `76b7cc3`).

---

## Why release artifact?

| | Development install | Release artifact |
|---|---|---|
| Layout | Source tree + `.venv/` | Standalone `.pyz` (zipapp) + 3 bash wrappers |
| Runtime deps | Python 3.14 + `uv` + locked venv | Python 3.14 on `PATH` only |
| Edit source | Yes | No |
| File size | `.venv/` ≈ 80 MB | `.pyz` ≈ 5.6 MB |
| Distribution | `git clone` | `curl -L` from GitHub release |

Choose release mode for production hosts and operator workstations.
Choose development mode
([installation.md § Mode 1](installation.md#mode-1--development-install))
when you intend to edit the code.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | `>=3.14` | Shebang points to system `python3`; `requires-python = ">=3.14"` (`pyproject.toml:6`) enforced at build time |
| `curl` | any | `wget` works too |
| `tar` + `gzip` | any | `tar -xzf` needs GNU `tar` (BSDs: `gtar`) |
| `PATH` write | `~/bin/`, `/usr/local/bin/`, or similar | `~/bin/` is the single-user default |

The artifact (`dist/easter-hermes-sorry-skills-v0.1.0.tar.gz`)
contains `scripts/*.sh` (15-line bash wrappers that resolve the `.pyz`
next to themselves and `exec` the entry point), `dist/*.pyz` (shiv-built
zipapp embedding Python 3.14 site-packages), and `skills/skill-creator/`
(for mode 3). No `uv`, no `git`, no network at runtime.

---

## Install

```bash
# 1. Download the release artifact
curl -L -o easter-hermes-sorry-skills.tar.gz \
  https://github.com/EggProject/easter-skills-hack-to-hermes/releases/download/v0.1.0/easter-hermes-sorry-skills-v0.1.0.tar.gz

# 2. Extract
tar -xzf easter-hermes-sorry-skills.tar.gz
cd easter-hermes-sorry-skills-v0.1.0

# 3. Symlink the wrapper scripts to ~/bin
mkdir -p ~/bin
for script in scripts/easter-hermes-sorry-skills-*.sh; do
  ln -sf "$(pwd)/${script}" ~/bin/$(basename "${script%.sh}")
done

# 4. Symlink the .pyz so the wrappers resolve ../dist/, ./dist/, or ./
ln -sf "$(pwd)/dist/easter-hermes-sorry-skills.pyz" ~/bin/easter-hermes-sorry-skills.pyz

# 5. Confirm ~/bin is on PATH
case ":${PATH}:" in
  *":${HOME}/bin:"*) ;;
  *) export PATH="${HOME}/bin:${PATH}" ;;
esac
```

The wrappers look for the `.pyz` next to themselves (`../dist/`,
`./dist/`, then `./`). Putting the symlink in `~/bin/` next to the
wrapper symlinks preserves that contract. For a system-wide install:

```bash
sudo cp easter-hermes-sorry-skills-v0.1.0/scripts/easter-hermes-sorry-skills-*.sh /usr/local/bin/
sudo cp easter-hermes-sorry-skills-v0.1.0/dist/easter-hermes-sorry-skills.pyz /usr/local/bin/
```

`chmod +x` is not required: `.sh` files ship with the executable bit
set, and the `.pyz` runs via its Python shebang.

---

## Verify

```bash
# 1. The wrapper resolves the .pyz and exits 0
easter-hermes-sorry-skills-patch-hermes --version
easter-hermes-sorry-skills-report --version

# 2. Bilingual help prints both EN and HU sections
easter-hermes-sorry-skills-patch-hermes --help --lang en
easter-hermes-sorry-skills-patch-hermes --help --lang hu

# 3. The .pyz is a valid zipapp and runs standalone
python3 -m zipfile -l dist/easter-hermes-sorry-skills.pyz | head
./dist/easter-hermes-sorry-skills.pyz -c "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__name__)"
```

A clean install prints `easter-hermes-sorry-skills 0.1.0` from each
`--version`, both `[en]` and `[hu]` blocks from `--help --lang en`, and
the package name from the `-c` invocation. Full smoke battery:
[installation-verify.md](installation-verify.md).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: dist/easter-hermes-sorry-skills.pyz: No such file or directory` | Wrapper cannot resolve the `.pyz` next to itself | Symlink the `.pyz` into `~/bin/` (step 4); or copy both `scripts/*.sh` and `dist/*.pyz` to the same target directory |
| `zipfile.BadZipFile: File is not a zip file` | The `.pyz` is truncated or the download was incomplete | `rm easter-hermes-sorry-skills.pyz` and re-run step 1 with `-L`; verify size with `wc -c` |
| `ModuleNotFoundError: easter_hermes_sorry_skills` (direct `.pyz` invocation) | The `.pyz` was rebuilt against the wrong entry point | Use the wrappers (they pin the right `-c` snippet); or rebuild via `scripts/build-release.sh --only-shiv` |
| `Python 3.13 or older is not supported` | `python3` on `PATH` resolves to < 3.14 | Install Python 3.14 and re-export `PATH`; do not bypass via `--break-system-packages` |
| `shiv: command not found` (build machine only) | `shiv>=1.0,<2.0` was not installed into the venv | `uv sync --locked --all-extras --dev` once on the dev machine; build-only, does NOT touch the release artifact |

The `shiv` row is the only failure that belongs to the build machine.
Operators running mode 2 do not need `shiv`, `uv`, or `git`.

---

Last verified: 2026-06-27 against HEAD `76b7cc3`.
Back to [Installation](installation.md) · [Verify](installation-verify.md) · [Hermes plugin](installation-hermes.md)
