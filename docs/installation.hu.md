# Telepítés (magyar)

> [English](installation.md) · [Magyar verzió](installation.hu.md)
> [Vissza a README-hez](../README.hu.md)

Az `easter-hermes-sorry-skills` három CLI-t és egy migrált skillt szállít. Az alábbi három telepítési mód a három működési profilhoz igazodik: a fejlesztő, aki a forrást szerkeszti; az üzemeltető, aki csak futtatja a CLI-kat; és a felhasználó, aki a plugint egy Hermes futtatókörnyezetbe köti be. Válaszd ki a céllal egyező módot; az egyes linkek a teljes eljárást végigvezetik.

A telepítés után a CLI-k kezeléséhez lásd [docs/usage.hu.md](usage.hu.md); a lint / teszt / CI konvenciókhoz pedig [docs/development.hu.md](development.hu.md).

Utoljára ellenőrizve: 2026-06-27 a `pyproject.toml` (HEAD `76b7cc3`) alapján.

---

## Előfeltételek

Ugyanaz a három eszköz kell minden módban; az opcionális eszközök módonként változnak.

| Eszköz | Verzió | Melyik módhoz kell | Megjegyzés |
|---|---|---|---|
| Python | `>=3.14` | minden mód | a `pyproject.toml:6` deklarálja (`requires-python = ">=3.14"`); a `.pyz` shebang a rendszer `python3`-jára mutat |
| `uv` | `>=0.4` | dev telepítés + release build | az `uv.lock` autoritatív; az `uv` oldja fel a venvet és a pre-commit kaput |
| `git` | bármely friss | dev telepítés + release build | a `git rev-parse --show-toplevel` hívást használja a `scripts/build-release.sh` és a bash wrapper-ek |
| `shiv` | `>=1.0,<2.0` | csak release build | a `scripts/build-release.sh` telepíti a `.venv`-be; csak a build-gépen kell, az üzemeltető gépen soha |
| `bats` | bármely friss | smoke tesztek | a `tests/bats/*.bats` végigmegy a shell wrapper-eken |
| `shellcheck` | bármely friss | pre-commit lint | a `scripts/*.sh` severity=warning szinten kapuzott |

A három belépési pont a `pyproject.toml:33-36` címen található:

- `easter-hermes-sorry-skills-patch-hermes`
- `easter-hermes-sorry-skills-report`

A `.pyz` egy önálló, egyfájlos zipapp (PEP 441), amelyet a `shiv` állít elő a venv `site-packages/` mappájából; a Python 3.14 site-packages be van ágyazva, de a `python3` futtatót PATH-on várja.

---

## Gyors telepítés

Három mód, egy CLI felszín. Minden mód a teljes eljárásra mutat, plusz egy verification link a smoke teszthez.

### 1. mód — Development telepítés

Forrásszerkesztéshez, tesztfuttatáshoz és újraépítéshez. A locked függőségekkel és a pre-commit kapuval bootstrappel.

- Extra előfeltétel: `just` (opcionális) a recipe runnerhez.
- Idő a kész állapotig: ~2 perc meleg cache mellett.

→ [docs/installation-dev.hu.md](installation-dev.hu.md)

### 2. mód — Release artifact telepítés

Olyan üzemeltető gépekhez, amelyeknek csak a három CLI-t kell futtatniuk. Nincs forrás, nincs `uv`, nincs újraépítés — csak a `.pyz` és a bash wrapper-ek a `PATH`-on.

- Extra előfeltétel: nincs, csak Python 3.14.
- Idő a kész állapotig: ~30 másodperc.

→ [docs/installation-release.hu.md](installation-release.hu.md)

### 3. mód — Hermes plugin + skill telepítés

Olyan Hermes futtatókörnyezetekhez, amelyeknek a migrált `skill-creator` skillt kell kitenniük, és induláskor be kell tölteniük a patcher plugint. Az 1-es és 2-es módtól független.

- Extra előfeltétel: user-owned Hermes checkout (a patcher elutasítja az upstream repot, exit code 4).
- Idő a kész állapotig: ~5 perc a patch audit-tal együtt.

→ [docs/installation-hermes.hu.md](installation-hermes.hu.md)

### A telepítés ellenőrzése

Bármelyik mód után futtasd a kétnyelvű smoke tesztet. Minden parancsnak `0` exit kóddal kell kilépnie; az EN + HU help szekcióknak egyszerre kell megjelenniük.

→ [docs/installation-verify.hu.md](installation-verify.hu.md)

---

## Lásd még

- [Telepítés — development mód](installation-dev.hu.md) — clone, `uv sync`, pre-commit
- [Telepítés — release mód](installation-release.hu.md) — `.pyz` + wrapper-ek a `PATH`-on
- [Telepítés — Hermes mód](installation-hermes.hu.md) — patch + plugin + skill
- [Telepítés — verify](installation-verify.hu.md) — kétnyelvű smoke teszt
- [Használat](usage.hu.md) — a három CLI end-to-end vezérlése
- [Workflow-k](workflows.hu.md) — gyakori telepítési / szerzői / riport receptek
- [Fejlesztés](development.hu.md) — teszt, lint, CI, worktree + PR konvenciók
- [License](../LICENSE) — MIT
- [README](../README.hu.md) — projekt landing page

Utoljára ellenőrizve: 2026-06-27. Vissza a [README-hez](../README.hu.md).