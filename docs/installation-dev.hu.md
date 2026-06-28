# Telepítés — development mód (magyar)

> [English](installation-dev.md) · [Magyar verzió](installation-dev.hu.md)
> [Vissza a Telepítéshez](installation.hu.md)

A development telepítés a single source of truth telepítés: ezt futtatják a maintainerek, ezt futtatja a CI, és erre van szükséged, ha a forrást szeretnéd szerkeszteni, a tesztkészletet futtatni, vagy a release artifactet újraépíteni. Egy zárolt `.venv`-et bootstrappel `uv`-vel, és beköti az egyesített pre-commit kaput (ruff + black + mypy + wemake + flake8 + pytest + bats + shellcheck).

Utoljára ellenőrizve: 2026-06-27 a `pyproject.toml` (HEAD `76b7cc3`) alapján.

---

## Miért a development telepítés?

A release artifact telepítés (lásd [installation-release.hu.md](installation-release.hu.md)) egyetlen `.pyz`-t és három bash wrapper-t szállít — gyors, de build időben fagyott. A development telepítés ennek a fordított trade-offja:

| Szempont | Development telepítés | Release artifact telepítés |
|---|---|---|
| Forráskód + tesztek + lint | igen (teljes git checkout) | nem (csak a `.pyz`) |
| A `.pyz` újraépítése | igen (`scripts/build-release.sh`) | nem |
| Lemezigény | ~500 MB (`.venv` + `.git`) | ~30 MB (`.pyz` + wrapper-ek) |
| Idő a kész állapotig | ~2 perc meleg `uv` cache mellett | ~30 s |
| A gépen szükséges | Python 3.14, `uv`, `git` | csak Python 3.14 |

A development telepítést akkor válaszd, ha a forrást akarod módosítani, a CI-t helyben akarod futtatni, vagy új release-t akarsz szállítani. A release telepítést akkor, ha csak a három CLI kell scriptekből vagy cronból.

---

## Előfeltételek

| Eszköz | Verzió | Megjegyzés |
|---|---|---|
| Python | `>=3.14` | a `pyproject.toml:6` deklarálja |
| `uv` | `>=0.4` | a zárolt venvet oldja fel; telepítés: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `git` | bármely friss | a `git rev-parse --show-toplevel` hívást használja a `scripts/build-release.sh` és a bash wrapper-ek |
| `just` | bármely friss | **opcionális** — a recipe runner nem kötelező, de hasznos a gyakori task shortcutokhoz |

A `shiv`, `bats` és `shellcheck` NEM kell a fejlesztői gépre magához a telepítéshez — a `shiv` a build során a venv-be töltődik (lásd [installation-release.hu.md](installation-release.hu.md)); a `bats` és a `shellcheck` a pre-commit kapu által települ az első commitnál, vagy a CI workflow által `ubuntu-latest`-en.

---

## Telepítés

Négy parancs. A 2. lépés a munka nagy része; a 3-4. lépés a kaput és a smoke tesztet köti be.

```bash
# 1. A repo clone-olása és belépés
git clone https://github.com/EggProject/easter-skills-hack-to-hermes.git
cd easter-skills-hack-to-hermes

# 2. A venv bootstrappelése zárolt függőségekkel + dev extrákkal
uv sync --locked --all-extras --dev

# 3. Az egyesített pre-commit kapu telepítése (ruff + black + mypy + wemake + flake8 + pytest + bats + shellcheck)
uv run --locked pre-commit install

# 4. A CLI-k PATH-on vannak-e
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-report --version
```

A 2. lépés után a `.venv/` létezik. A 3. lépés után minden `git commit` lefuttatja a `.pre-commit-config.yaml`-ban definiált pre-commit kaput (lásd [docs/development.hu.md](development.hu.md)). A 4. lépés után a CLI-k a `.venv/bin/` mappából hívhatók az `uv run --locked` prefix nélkül; a prefix egyelőre kötelező, hogy az `uv.lock` autoritatív maradjon a `.claude/rules/worktree-pr-workflow.md` szerint.

### Opcionális: `.venv/bin` felvétele a `PATH`-ba

Ha a CLI-kat az `uv run --locked` prefix nélkül akarod hívni, exportáld a `.venv/bin`-t a `/usr/local/bin` elé a shell profilodban.

```bash
# Csak az aktuális shellben
export PATH="$(pwd)/.venv/bin:${PATH}"

# Perzisztens (válassz egyet)
echo 'export PATH="'$(pwd)'/.venv/bin:${PATH}"' >> ~/.zshrc   # zsh
echo 'export PATH="'$(pwd)'/.venv/bin:${PATH}"' >> ~/.bashrc  # bash
```

---

## Ellenőrzés

Három ellenőrzés; minden parancsnak `0` exit kóddal kell kilépnie.

```bash
# 1. Minden CLI kiírja a --version-t
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-report --version

# 2. A pre-commit kapu be van kötve
uv run --locked pre-commit run --files pyproject.toml

# 3. A teljes teszt + lint sweep tisztán fut
uv run --locked pre-commit run --all-files
uv run --locked pytest
```

A teljes kétnyelvű smoke teszthez (EN + HU help, `.pyz` zip listing, plugin tree) lásd [docs/installation-verify.hu.md](installation-verify.hu.md).

---

## Hibakezelés

| Tünet | Ok | Megoldás |
|---|---|---|
| `error: Python 3.13 or older is not supported` | a `requires-python = ">=3.14"` (`pyproject.toml:6`) nem teljesült | Telepíts Python 3.14-et, és exportáld újra a `PATH`-ot, hogy a `python3` arra oldódjon fel; vagy add ki az `uv sync`-et `--python 3.14` flag-gel |
| `command not found: uv` | az `uv` nincs a `PATH`-on | Telepítsd a `curl -LsSf https://astral.sh/uv/install.sh \| sh` paranccsal, majd `source ~/.zshrc` (vagy `~/.bashrc`) |
| `error: The lockfile at uv.lock would be modified` | az `uv sync` a commitolt `uv.lock` ellen változtatna | Futtasd újra `uv sync --locked --all-extras --dev` módon (a `--locked` flag megtagadja a lockfile módosítását); csak az `uv lock` regenerate-elheti |
| `.venv/bin/python3: No such file or directory` | friss checkout, nincs venv bootstrap | Futtasd egyszer az `uv sync --locked --all-extras --dev` parancsot; a további parancsok a `.venv/` meglétére számítanak |
| `easter-hermes-sorry-skills-patch-hermes: command not found` | a wrapper `uv run --locked` prefix nélkül futott | Vagy toldd be az `uv run --locked` prefixet, vagy használd közvetlenül a `.venv/bin/easter-hermes-sorry-skills-patch-hermes`-t, vagy exportáld a `.venv/bin`-t a `PATH`-ba (lásd fent) |
| `pre-commit: command not found` (a 3. lépés alatt) | a venv nem a dev extrákkal lett bootstrappelve | Futtasd az `uv sync --locked --all-extras --dev` parancsot — a `--dev` flag a `pre-commit`-ot a `.venv`-be telepíti |
| `pre-commit install` hook hibával elbukik | a hook-ok egyike hiányzik a hoston (pl. `shellcheck`, `bats`) | Telepítsd a platform csomagkezelőjével (pl. `sudo apt-get install -y shellcheck bats` Ubuntu 24.04-en), vagy bízd a CI-re `ubuntu-latest`-en |

Ha egyik sem illik, ragadd meg a teljes `uv run --locked` parancsot, az exit kódját, és a stderr első 10 sorát, majd nyiss egy issue-t.

Utoljára ellenőrizve: 2026-06-27. Vissza a [Telepítéshez](installation.hu.md).