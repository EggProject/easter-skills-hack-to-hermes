# easter-hermes-sorry-skills

> 🇬🇧 **[English version →](README.md)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: EN](https://img.shields.io/badge/lang-EN-blue.svg)](README.md)
[![Language: HU](https://img.shields.io/badge/lang-HU-blue.svg)](README.hu.md)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-pre--commit%20%2B%20pytest-green.svg)](.github/workflows/ci.yml)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-plugin-blueviolet.svg)](src/easter_hermes_sorry_skills/_register.py)
[![Hermes Hack: deliverable](https://img.shields.io/badge/Hermes%20Hack-deliverable-orange.svg)](#mir%C5%91l-sz%C3%B3l-ez-a-projekt)

## Miről szól ez a projekt?

A Hermes Skills Hack 5. fázisából származó két összehangolt artifact:

1. **Hermes plugin** (`src/easter_hermes_sorry_skills/`) — egyszeri, kétnyelvű
   figyelmeztetést ad ki, ha a 60 karakteres skill-leírás cap nincs felemelve a
   Hermes checkout-odban. A plugin **kizárólag tanácsadó**: soha nem módosítja
   a Hermest (`_register.py:1-13`).
2. **Migrált `skill-creator`** (`skills/skill-creator/`) — Anthropic
   `claude-plugins-official` repójából portolva Hermes-re (`claude` → `hermes`,
   `.skill` → `.zip`, NDJSON → ShareGPT, valamint `compatibility` frontmatter).
   A frontmatter-szerződést lásd: `skills/skill-creator/SKILL.md:4`.

A csomag három, operátor felé néző CLI entry pointot szállít
(`pyproject.toml:34-36`), valamint a kétnyelvű üzenetkatalógust itt:
`src/easter_hermes_sorry_skills/i18n/`.

## Gyors indulás

```sh
# 1. Telepítsd a csomagot (3 mód: development / release artifact / Hermes plugin)
#    Lásd: docs/installation.md
uv sync --locked --all-extras --dev
uv run --locked pre-commit install

# 2. Patch audit (dry-run)
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run

# 3. Patch apply
uv run --locked easter-hermes-sorry-skills-patch-hermes

# 4. Smoke test
uv run --locked easter-hermes-sorry-skills-install-profiles
uv run --locked easter-hermes-sorry-skills-report
```

Részletes telepítési útmutató: [docs/installation.md](docs/installation.md).
Részletes használati útmutató: [docs/usage.md](docs/usage.md).

Telepítés után a három CLI a `PATH`-odon lesz:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-install-profiles`
- `easter-hermes-sorry-skills-report`

## Dokumentáció

| Téma | Link |
|---|---|
| Telepítés (3 mód) | [docs/installation.md](docs/installation.md) |
| Telepítés: development | [docs/installation-dev.md](docs/installation-dev.md) |
| Telepítés: release artifact | [docs/installation-release.md](docs/installation-release.md) |
| Telepítés: Hermes plugin | [docs/installation-hermes.md](docs/installation-hermes.md) |
| Verifikáció + életciklus | [docs/installation-verify.md](docs/installation-verify.md) |
| Használat (gyors indulás + workflow-k) | [docs/usage.md](docs/usage.md) |
| Gyakori workflow-k + hibaelhárítás | [docs/workflows.md](docs/workflows.md) |
| Patch-ek (S1.cap + Task E site-ok) | [docs/patches.md](docs/patches.md) |
| Skill-creator (migrált) | [docs/skill-creator.md](docs/skill-creator.md) |
| Szkriptek (a három CLI) | [docs/scripts.md](docs/scripts.md) |
| Migrációs napló (claude → hermes) | [docs/migration.md](docs/migration.md) |
| Fejlesztés (uv + pre-commit) | [docs/development.md](docs/development.md) |

## Szkriptek áttekintése

Mind a három entry point a `pyproject.toml:34-36` sorban van deklarálva. Mindig
`uv run --locked` mögé zárd, hogy az `uv.lock` maradjon a mérvadó.

- `easter-hermes-sorry-skills-patch-hermes` — alkalmazza a **8 patch-et**
  (S1.cap + 6 Task E site + S1.cap skills-prompt-snapshot purge) a Hermes
  checkout-odon. Alapértelmezetten `--target ~/.hermes/hermes-agent`. Alapból
  **ír**; a `--dry-run` kapcsolóval auditálhatsz írás nélkül.
- `easter-hermes-sorry-skills-install-profiles` — **read-only**, profile-onkénti
  audit a migrált `skill-creator` mellett (mely profilokban engedélyezett,
  mely skill-ek láthatók). Alapértelmezetten táblázatot ad, a `--json`
  kapcsolóval JSON-t.
- `easter-hermes-sorry-skills-report` — **read-only** használati riport.
  Megmutatja, mely skill-ek vannak jelenleg engedélyezve, és hogyan néz ki a
  napi költségfelület. Nincs írás, nincs config-flippelés.

### `--dry-run` és a dry-run terv

Az `easter-hermes-sorry-skills-patch-hermes --dry-run` az összes tervezett
patch-et auditálja anélkül, hogy egyetlen byte-ot is írna a célpontra. A
kimenet egy kétnyelvű (EN/HU) **terv**, amelyet az operátor az apply
előtt olvas el:

```text
[en] plan for /path/to/target:
[hu] terv a /path/to/target útvonalra:
[en] would patch: agent/skill_utils.py (site S1.cap)
[hu] patchelné: agent/skill_utils.py (S1.cap site)
  line 688: - régi sor tartalma
  line 688: + új sor tartalma
[en] 8 patch(es) would be applied / [hu] 8 patch kerülne alkalmazásra
[en] WARNING: --dry-run mode, 8 patches were NOT applied /
[hu] FIGYELEM: --dry-run módban vagyunk, 8 patch NEM történt meg
```

Az apply mód ugyanazt a tervet adja ki, de a záró sor átvált a
kétnyelvű „alkalmazva" üzenetre a dry-run figyelmeztetés helyett:

```text
[en] 8 patches applied / [hu] 8 patch alkalmazva
```

**Lágy safety.** A `~/.hermes/hermes-agent` checkout a patcher
no-touch sentinelje. Az apply mód (`--dry-run` nélkül) KEMÉNYEN
megtagadja `EXIT_IO` kóddal és kétnyelvű diagnosztikával. A dry-run
mód LÁGYÍTJA a megtagadást: a patcher kétnyelvű WARNING-ot ad ki,
kiírja a tervet, és továbbhalad, hogy az operátor az apply előtt
megnézhesse a tervezett változtatásokat. A célfájl hash-e
byte-azonos marad (a `test_cli_dry_run_no_writes_to_target`
egységteszt ellenőrzi).

Mind a három CLI kétnyelvű (EN/HU) konzol-kimenetet ad
(`i18n/messages_en.py`, `i18n/messages_hu.py`); a `--help` tükrözött angol /
magyar szekciókat tartalmaz.

## Projekt felépítése

```
src/easter_hermes_sorry_skills/   # plugin + a három CLI
  _register.py                    # hermes_cli.plugins entry point
  _advisory.py                    # statikus-AST cap-detektálás (nincs módosítás)
  _patcher*.py                    # the 8-patch engine
  cli_patch.py                    # patch-hermes CLI
  cli_profiles.py                 # install-profiles CLI
  cli_report.py                   # report CLI
  i18n/                           # kétnyelvű üzenetkatalógus (en, hu)
skills/skill-creator/             # migrált skill (Hermes variáns)
docs/                             # témánkénti dokk (lásd a fenti táblázatot)
scripts/                          # bash wrapper-ek minden CLI köré
```

## Fejlesztés

Ez a projekt **Python 3.14+**, **uv-kezelésű**, és a
[pre-commit](https://pre-commit.com/) felügyeli. A legszigorúbb hook-ok
(wemake-python-styleguide, mypy strict, ruff, black) a
`.pre-commit-config.yaml` fájlban vannak konfigurálva a toolchain-konvenciók
terve szerint.

```sh
uv sync --locked --all-extras --dev           # egyszeri venv-bootstrap
uv run --locked pre-commit install            # gate minden commitra
uv run --locked pre-commit run --all-files    # teljes sweep push előtt
uv run --locked pytest                        # run the test suite
uv run --locked ruff check src tests          # csak lint
uv run --locked mypy src                      # csak típusellenőrzés
```

A CI ugyanazt az `uv sync --all-extras --dev` lépést futtatja
(`.github/workflows/ci.yml`), így a helyi pre-commit átfutás garantálja, hogy
ugyanaz a kód átmegy a CI-on is.

## Release build

Amikor a release artifact-ba kerülő kód változik (Python forrás az `src/` mappában vagy függőségek a `pyproject.toml` / `uv.lock` fájlokban), újra kell építeni a release artifact-ot:

```bash
scripts/build-release.sh
```

A script 3 lépést végez:

1. **`uv sync --locked`** — a függőségek telepítése az `uv.lock` alapján a `.venv/` mappába
2. **`shiv`** — a `.venv/lib/python3.14/site-packages/` becsomagolása a `dist/easter-hermes-sorry-skills.pyz` fájlba (single-file standalone zipapp, PEP 441)
3. **`tar -czf`** — a `dist/*.pyz` + `scripts/` + `README*` becsomagolása a `dist/easter-hermes-sorry-skills-v{VERSION}.tar.gz` fájlba

### Terjesztés

Az elkészült `dist/easter-hermes-sorry-skills-v{VERSION}.tar.gz` egy ön-teljes release artifact. A felhasználók letöltik, kibontják, és **install nélkül** futtatják a wrapper scripteket (nincs `uv sync`, nincs `pip install`):

```bash
tar -xzf easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0/
bash scripts/easter-hermes-sorry-skills-install-profiles.sh [args...]
```

Az egyetlen követelmény a felhasználó gépén: **Python 3.14+** (a `.pyz` shebang a rendszer `python3`-ra mutat).

### Build flag-ek

A `scripts/build-release.sh` a következő opcionális flag-eket támogatja:

- `--only-shiv` — csak a `.pyz` build (kihagyja a `tar.gz`-t)
- `--only-tar` — csak a `tar.gz` (feltételezi, hogy a `.pyz` már létezik)

A `dist/` mappa törléséhez rebuild előtt futtasd manuálisan: `rm -rf dist/` (a `--clean` flag szándékosan nem került a scriptbe, hogy ne legyen destruktív).

## Licenc

Kettős licencelés:

- A [LICENSE](LICENSE) fájl a kanonikus **MIT Licenc** (Copyright © 2026
  eggproject Kft.) — ez a hiteles licenc a nyílt forráskódú terjesztéshez.
- A `pyproject.toml:7` `license = { text = "Proprietary" }` mező az operátor
  által kezelt marker a belső Hermes Hack csomagoláshoz és terjesztés-
  felügyelethez. NEM külön licenc; az MIT szöveg szabályozza a forráskód
  minden felhasználását ebben a repository-ban.

## Közreműködés

Kizárólag belső hozzájárulás. Az alábbi útvonal-hivatkozások a projekt belső fájljaira mutatnak (`.claude/rules/*.md`), amelyek a worktree+PR workflow-t szabályozzák; ezek nem külső függőségek. Nyiss feature branch-et
`.claude/worktrees/<branch>/` alatt, futtasd az egységes pre-commit kaput, és
nyújts be PR-t `main` ellenében. A `main` ágra közvetlen commit tilos a worktree
+ PR workflow szabály szerint (`.claude/rules/worktree-pr-workflow.md`). Minden
PR-t kövess végig, amíg zöld CI-jú merge-ölésre nem kerül
(`.claude/rules/follow-up-pr-until-merged.md`,
`.claude/rules/no-pr-merge-without-green-ci.md`).
