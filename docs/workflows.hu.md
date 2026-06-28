# Munkafolyamatok

🇬🇧 **[English version →](workflows.md)**

> [Vissza a Használathoz](usage.hu.md)

Három kezelői munkafolyamat: első telepítés, új skill fejlesztése a
migrált `skill-creator`-on keresztül, és a napi usage report. Az
[installation-verify](installation-verify.md) által nem lefedett futásidejű
hibák alább találhatók.

Előfeltételek: tiszta telepítés az [installation.hu.md](installation.hu.md)
szerint, és a három CLI a `PATH`-on.

Utoljára ellenőrizve: 2026-06-27 a `pyproject.toml` alapján (HEAD `76b7cc3`).

---

## 1. munkafolyamat: Első telepítés

Friss gép bootstrappelése. Az 1.1-1.2 read-only; az 1.3 kiírja a 8
patchet; az 1.4-1.5 ellenőrzi, hogy a migrált skill triggerelődik a
Hermesben.

```bash
# 1.1  Telepítsd a csomagot (fejlesztés vagy release artifact) — lásd docs/installation.hu.md.

# 1.2  Patch audit — változtatna a patcher bármit is?
uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run \
    --target ~/work/hermes-fork

# 1.3  Patch apply — a 8 patch kiírása (S1.cap + 5 Task E + cache purge)
uv run --locked easter-hermes-sorry-skills-patch-hermes \
    --target ~/work/hermes-fork

# 1.4  Smoke test — a skill látható minden Hermes profilban?
uv run --locked easter-hermes-sorry-skills-report --format text

# 1.5  Indítsd újra a Hermest, majd ellenőrizd a migrált skill triggerelődését
hermes chat -p "Use skill-creator to scaffold a skill called hello-world."
```

Az 1.2-ben a `--dry-run` site-onként egy kétnyelvű sort ír ki. Ha bármely
site `drifted`-et jelez, abort és olvasd el a
[Hibakezelés](#hibakezelés) szekciót — ne futtasd az 1.3-at drifted
targeten. Az 1.3 fájlonként atomi; az 1.4 read-only; az 1.5 a teljes
round-tripet erősíti meg.

---

## 2. munkafolyamat: Új skill fejlesztése

Szerző, validál, regisztrál, smoke-tesztelj, majd commitolj.

```bash
# 2.1  A Hermesen belül hívd meg a migrált skill-creatort a szándékkal
hermes chat -p "Use skill-creator to create a skill that wraps 'git status' \
for our support team. The skill should group changes by working-tree vs \
staged and emit a single concise summary line an operator can paste into a ticket."
#      Lépések: szándék rögzítése -> interjú -> SKILL.md piszkozat -> teszt promptok
#              -> értékelés -> iteráció -> becsomagolás .zip-ként.

# 2.2  A generált skill validálása (read-only, gyors kapu)
uv run --locked python skills/skill-creator/scripts/quick_validate.py \
    skills/git-status-helper

# 2.3  A skill regisztrálása a kezelő Hermes telepítésében
mkdir -p "${HOME}/.hermes/skills"
ln -sfn "$(pwd)/skills/git-status-helper" "${HOME}/.hermes/skills/git-status-helper"
#      Szimbolikus link (nem másolat), hogy a `git pull` helyben frissítsen.

# 2.4  Smoke-teszt a Hermesen belül — a skill a megfelelő kifejezésekre triggerelődik?
hermes chat -p "Why is my commit not showing up?"

# 2.5  (Opcionális) Az új skill commitolása a host repóba
git add skills/git-status-helper/
git commit -m "feat(skills): add git-status-helper scaffold"
```

A 2.2 az egyetlen kapu a 2.4 előtt — a `quick_validate.py` a konkrét
frontmatter / mappa-elrendezés elutasítást jelzi. Teljes skill-creator
szerződés: [docs/skill-creator.hu.md](skill-creator.hu.md).

---

## 3. munkafolyamat: Napi usage report

Read-only nézet: „mi van most fent, és mennyibe kerül?". Cron-ra
biztonságosan futtatható; nincs konfiguráció-átállítás, nincs
skill-szintű írás.

```bash
# 3.1  Szöveges összefoglaló (kezelőbarát, token becslés szerint rendezve)
uv run --locked easter-hermes-sorry-skills-report --format text

# 3.2  JSON stdout-ra — pipe-olható jq-ba / dashboardokba
uv run --locked easter-hermes-sorry-skills-report --format json | jq .

# 3.3  JSON perzisztálása lemezre — alapértelmezett útvonal ./skill-report.json
uv run --locked easter-hermes-sorry-skills-report --format json \
    --json ./skill-report.json --sort use_count
#      ^ stabil a futtatások között (ua. bemenet -> ua. bájtok), napról napra diffelhető.
```

Az alapértelmezett rendezés `tokens`; a `--sort use_count` és
`--sort last_used_at` is érvényes (lásd [docs/scripts.hu.md](scripts.hu.md)).
A 3.2-t cron bejegyzéssel párosítsd — a perc eltolt a `:00`-tól, hogy a
különböző kezelők flottája ne ütközzön:

```cron
# 17. perc, nem :00 — cron-fleet desync
17 7 * * *  ubuntu  cd /opt/easter-hermes-sorry-skills && \
                   uv run --locked easter-hermes-sorry-skills-report --format json \
                   --json /var/lib/easter-hermes/daily-$(date +\%F).json
```

---

## Hibakezelés

A telepítési idejű hibák (`Permission denied`, `LINE_DRIFT`, no-touch
sentinel, hiányzó szimbolikus linkek) a
[docs/installation-verify.hu.md](installation-verify.hu.md) oldalon
találhatók. Ez a táblázat a telepítés UTÁNI futásidejű hibákat fedi le
— azokat a tüneteket, amelyeket az on-call engineer a 2. napon és
azután lát.

| Tünet | Megoldás |
|---|---|
| A patchek kiíródtak, de a cap futásidőben még mindig 60 karakter | A patcher siker esetén törli a `~/.hermes/.skills_prompt_snapshot.json` fájlt; kézzel `rm -f` és indítsd újra a Hermest |
| Patch rollback kell (CI piros, upstream felülírta a capet) | `git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py`. Lásd [patches.hu.md#rollback](patches.hu.md#rollback) |
| `.venv` sérült vagy `uv run --locked` import hibákkal elszáll | `rm -rf .venv && uv sync --locked --all-extras --dev`. `uv.lock` eltérés esetén előbb `uv lock` és audit |
| A `--lang hu` nem váltja át az alapértelmezett help szekciót | A release artifact a `--lang` bevezetése előtt épült (`76b7cc3` commit, PR #47). Újraépítés: `scripts/build-release.sh` |
| `Skill 'X' already exists` hiba `ln -sfn` regisztrációnál | `rm -f "${HOME}/.hermes/skills/X"`, majd hozd létre újra a szimbolikus linket |
| A `report --json` nem nullával lép ki, `Invalid --sort value` üzenettel | Érvényes `--sort` értékek: `tokens`, `use_count`, `last_used_at`. Lásd [scripts.hu.md](scripts.hu.md) |
| A kétnyelvű `[hu]` sorok hiányoznak a kimenetből | `uv sync --locked --all-extras --dev`; NE szerkeszd kézzel a `messages_en.py` / `messages_hu.py` fájlokat |

Ha egyik sem illik, rögzítsd a teljes `uv run --locked` parancsot, a
kilépési kódot és a stderr első 10 sorát, majd nyiss egy issue-t. Az
on-call engineer ugyanazt a CLI-t ugyanazon a Hermes checkouton
újrafuttatva reprodukálni tudja.

---

Utoljára ellenőrizve: 2026-06-27.
Vissza a [Használathoz](usage.hu.md).
