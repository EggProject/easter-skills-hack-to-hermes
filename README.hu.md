# easter-hermes-sorry-skills

> 🇬🇧 **[English version →](README.md)**

[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)](#licenc)
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
# 1. Install runtime + dev + extras (locked to uv.lock)
uv sync --locked --all-extras --dev

# 2. Telepítsd az egységes pre-commit kaput (ruff + black + mypy + wemake + pytest)
uv run --locked pre-commit install

# 3. Alkalmazd a 8 patch-et a Hermes checkout-odon (S1.cap + 6 Task E site)
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run   # előbb audit
uv run --locked easter-hermes-sorry-skills-patch-hermes              # utána alkalmaz
```

Telepítés után a három CLI a `PATH`-odon lesz:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-install-profiles`
- `easter-hermes-sorry-skills-report`

## Dokumentáció

| Téma | Link |
|---|---|
| 🛠️ Patch-ek (S1.cap + Task E site-ok) | **[Patch-ek](docs/patches.hu.md)** |
| 📖 Skill-creator (migrált) | **[Skill-creator](docs/skill-creator.hu.md)** |
| 📦 Szkriptek (a három CLI) | **[Szkriptek](docs/scripts.hu.md)** |
| 🚀 Migrációs napló (claude → hermes) | **[Migráció](docs/migration.hu.md)** |
| 🔧 Fejlesztés (uv + pre-commit) | **[Fejlesztés](docs/development.hu.md)** |

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

## Licenc

Proprietary. Lásd [pyproject.toml:7](pyproject.toml). A Hermes Skills Hack belső
szállítmánya. A hack-csapaton kívüli terjesztés tilos, kivéve az operátor
kifejezett jóváhagyásával.

## Közreműködés

Kizárólag belső hozzájárulás. Az alábbi útvonal-hivatkozások a projekt belső fájljaira mutatnak (`.claude/rules/*.md`), amelyek a worktree+PR workflow-t szabályozzák; ezek nem külső függőségek. Nyiss feature branch-et
`.claude/worktrees/<branch>/` alatt, futtasd az egységes pre-commit kaput, és
nyújts be PR-t `main` ellenében. A `main` ágra közvetlen commit tilos a worktree
+ PR workflow szabály szerint (`.claude/rules/worktree-pr-workflow.md`). Minden
PR-t kövess végig, amíg zöld CI-jú merge-ölésre nem kerül
(`.claude/rules/follow-up-pr-until-merged.md`,
`.claude/rules/no-pr-merge-without-green-ci.md`).
