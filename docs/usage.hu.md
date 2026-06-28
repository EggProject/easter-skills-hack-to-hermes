# Használat

🇬🇧 **[English version →](usage.md)**

> [Vissza a README-hez](../README.hu.md)

Az `easter-hermes-sorry-skills` kezelői felszíne telepítés után: a négy
lépéses gyors kezdés, a három CLI áttekintése, és a migrált
`skill-creator` skill. A részletes referencia a linkelt oldalakon él —
ez a fájl csak hivatkozik, nem duplikál.

Ha a CLI-k még nincsenek a `PATH`-on, előbb olvasd el a
[docs/installation.hu.md](installation.hu.md) oldalt. Flag-referencia:
[scripts.hu.md](scripts.hu.md). Patcher belsők: [patches.hu.md](patches.hu.md).
A skill: [skill-creator.hu.md](skill-creator.hu.md). Munkafolyamatok:
[workflows.hu.md](workflows.hu.md).

Utoljára ellenőrizve: 2026-06-27 a `pyproject.toml` alapján (HEAD `76b7cc3`).

---

## Gyors kezdés

Négy kezelői parancs. Az 1-2. lépés read-only; a 3. lépés ír; a 4. lépés
ellenőriz.

```bash
# 1. Telepítsd a csomagot (fejlesztés vagy release artifact)
#    Lásd docs/installation.hu.md

# 2. Patch audit (dry-run) — mit változtatna a patcher?
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run \
    --target /path/to/user-hermes

# 3. Patch apply — a 8 patch kiírása
uv run --locked easter-hermes-sorry-skills-patch-hermes \
    --target /path/to/user-hermes

# 4. Smoke test — a skill látható a Hermes számára?
uv run --locked easter-hermes-sorry-skills-report
```

Ha a 2. lépés bármely site-nál `drifted`-et jelez, abort és olvasd el a
[Hibakezelés](workflows.hu.md#hibakezelés) szekciót a 3. lépés
újrafuttatása előtt. A 3. lépés fájlonként atomi (az írás `<file>.patch.tmp`
+ `os.replace` útvonalon megy), ezért a futás közbeni összeomlás az
eredetit érintetlenül hagyja. A 4. lépés read-only és biztonságosan
ismételhető.

A 4. lépés után indítsd újra a Hermest, és hívd meg a
`/skill skill-creator` parancsot — lásd
[A migrált skill-creator skill](#a-migrált-skill-creator-skill).

---

## A három CLI áttekintése

Mindhárom console-script entry point a `pyproject.toml:33-36` sorokban van
deklarálva, és kétnyelvű `--help` szöveget ír ki (angol + magyar;
váltás: `--lang en|hu`). A flag-enkénti táblázatok, kilépési kódok és a
shell-wrapper szerződés a [docs/scripts.hu.md](scripts.hu.md) oldalon
találhatók.

- `easter-hermes-sorry-skills-patch-hermes` — A 8 patch (S1.cap + 5 Task E
  site + skills-cache purge) alkalmazása egy felhasználó tulajdonában
  lévő Hermes checkout-ra. Alapértelmezetten ír; `--dry-run` flaggel
  csak auditol. Nem nyúl a `~/.hermes/hermes-agent` útvonalhoz (az
  upstream repó).
- `easter-hermes-sorry-skills-report` — Read-only kezelői nézet: az
  engedélyezett skill-ek profilonként, token becslésekkel, használati
  számmal és utolsó használat időbélyeggel. NEM ír, kivéve egy
  kezelő által választott `--json PATH` útvonalat; NEM kapcsol át
  konfigurációt.

---

## A migrált `skill-creator` skill

A 3-as telepítési mód flat módon telepíti a felhasználó Hermes skills
mappájába — NEM a pluginon belül van csomagolva. A Hermesen belül:

```text
/skill skill-creator
```

Vagy kéréssel együtt a CLI-ból:

```text
hermes chat -p "Use skill-creator to create a skill that wraps 'git status'."
```

A skill a következő lépéseken vezeti végig a modellt: szándék rögzítése →
interjú → `SKILL.md` piszkozat → evals futtatása → értékelés → iteráció
→ becsomagolás `.zip`-ként. Forrás: `skills/skill-creator/SKILL.md`. A
teljes lépésenkénti szerződés, az eval-harness részletek és a leaf
agent-ek (`analyzer`, `comparator`, `grader`):
[docs/skill-creator.hu.md](skill-creator.hu.md).

---

## Csak hivatkozások

- [docs/installation.hu.md](installation.hu.md) — három telepítési mód + smoke test
- [docs/scripts.hu.md](scripts.hu.md) — flag-enkénti referencia a három CLI-hoz
- [docs/skill-creator.hu.md](skill-creator.hu.md) — a migrált `skill-creator` skill
- [docs/patches.hu.md](patches.hu.md) — a nyolc patch site (S1.cap + 5 Task E site) és a rollback mechanika
- [docs/workflows.hu.md](workflows.hu.md) — gyakori munkafolyamatok + hibakezelés
- [docs/development.hu.md](development.hu.md) — teszt, lint, CI, és a worktree + PR munkafolyamat

---

Utoljára ellenőrizve: 2026-06-27.
Vissza a [README-hez](../README.hu.md).
