# Telepítés — Hermes plugin

> 🇬🇧 **[English version →](installation-hermes.md)**

A 3. mód a migrált `skill-creator` skillt egy Hermes futtatókörnyezetbe
kötí be, hogy az agent felfedezhesse és meghívhassa. Független az 1. és
2. módtól: patchelj egy távoli Hermes checkoutot a CLI-k helyi futtatása
nélkül, vagy telepítsd a CLI-kat anélkül, hogy a skillt az agent számára
is elérhetővé tennéd.

Utoljára ellenőrizve: 2026-06-27 a `skills/skill-creator/SKILL.md` ellen (HEAD `76b7cc3`).

---

## Miért a Hermes plugin?

Az 1. és 2. mód a **CLI-kat** telepíti. A 3. mód a migrált **skillt** teszi
láthatóvá a Hermes agent számára. A skill egy sík fa struktúraként érkezik
a `skills/skill-creator/` alatt, és úgy lesz elérhető, hogy a felhasználó
skills könyvtárába symlinkeljük (`~/.hermes/skills/` a szokásos).

- A skill a Hermes indításakor töltődik be; az agent hívhatja a `/skill skill-creator` parancsot
- A frissítés egyetlen `git pull` ebben a repóban (a symlink megőrzi az útvonalat)
- A 3. mód önmagában nem patcheli a Hermes forrást. A 8 patch alkalmazásához futtasd az `easter-hermes-sorry-skills-patch-hermes --target /path/to/user-hermes` parancsot az 1. vagy 2. módból.

Hagyd ki a 3. módot, ha a skillre nincs szükséged futásidőben (csak operátori használat).

---

## Előfeltételek

- Felhasználó által birtokolt Hermes checkout (a patcher a kanonikus `~/.hermes/hermes-agent` útvonalat 4-es exit kóddal elutasítja; lásd [docs/patches.md](patches.md))
- Az `easter-hermes-sorry-skills` már telepítve van az 1. vagy 2. móddal (a 3. mód csak a skillt köti be)
- A `~/.hermes/skills/` írható
- A `skills/skill-creator/` jelen van a repóban (mindig szállítjuk; nem kell újraépíteni)

Klónozd a saját munkapéldányodat az upstream Hermes repóból, és add meg
azt `--target` paraméterként a patchernek.

---

## Telepítés

```bash
# 1. A skill-creator skill symlinkelése a ~/.hermes/skills/ alá
mkdir -p ~/.hermes/skills
ln -sf "$(pwd)/skills/skill-creator" ~/.hermes/skills/skill-creator

# 2. Annak ellenőrzése, hogy a Hermes felismeri
~/.hermes/hermes-agent --list-skills | grep skill-creator

# 3. (Opcionális) A plugin importálhatóvá tétele a hermes_cli.plugins felfedezéshez
uv pip install --target ~/.hermes/python-extras .
```

Az 1. lépés a `skill-creator` skillt felfedezhetővé teszi a futtatókörnyezet
számára. A symlink megőrzi az abszolút repó útvonalat, így az itteni
`git pull` a helyén frissíti a skillt.

A 3. lépés az `easter_hermes_sorry_skills` csomagot a Hermes által használt
Python útvonalra teszi (`src/easter_hermes_sorry_skills/_register.py:33-37`).
A következő Hermes újraindítás után az egyszeri kétnyelvű figyelmeztetés
felugrik, hacsak az `S1.cap` patchet nem alkalmazták; a marker fájl
(`~/.hermes/.easter_hermes_sorry_skills_advisory_seen`) elnyomja azt.

Ha a Hermes checkoutod a felhasználói konfigot a
`~/.hermes/hermes-agent.yaml`-ból olvassa, adj hozzá egy `skills_dirs`
bejegyzést, ami a `~/.hermes/skills`-re mutat. A pontos kulcs
futtatókörnyezet-specifikus.

---

## Ellenőrzés

```bash
# 1. A symlink egy valódi könyvtárra mutat
readlink -f ~/.hermes/skills/skill-creator

# 2. A skill manifest olvasható
head -20 ~/.hermes/skills/skill-creator/SKILL.md

# 3. A Hermesen belül hívd meg a skillt
~/.hermes/hermes-agent --list-skills | grep skill-creator
~/.hermes/hermes-agent --prompt "/skill skill-creator"
```

A tiszta telepítés kiírja a `readlink -f` abszolút repó útvonalat,
megmutatja a SKILL.md frontmatterét (`compatibility: hermes` sor), és a
`--list-skills` listában szerepel a `skill-creator`. Teljes smoke teszt:
[installation-verify.md](installation-verify.md).

---

## Hibakezelés

| Tünet | Ok | Megoldás |
|---|---|---|
| `ln: failed to create symbolic link ... File exists` | Egy korábbi symlink vagy valódi `skill-creator` könyvtár már a cél helyen van | `rm ~/.hermes/skills/skill-creator` és futtasd újra az 1. lépést; ellenőrizd a `ls -la ~/.hermes/skills/` paranccsal |
| `Skill not found` a `~/.hermes/hermes-agent`-ből | Sérült symlink vagy hiányzó `skills_dirs` konfig | A `readlink -f ~/.hermes/skills/skill-creator` oldjon fel; adj hozzá `skills_dirs: [~/.hermes/skills]` bejegyzést a `~/.hermes/hermes-agent.yaml` fájlhoz |
| `Permission denied` a `~/.hermes/skills/`-en | A könyvtár más felhasználó tulajdona vagy csak olvasható | `chown -R "${USER}": "${HOME}/.hermes/skills"`; a patcher 3-as exit kóddal elutasítja az olvashatatlan felhasználói fájlokba írást |
| `~/.hermes/hermes-agent.yaml: parse error` | Kézi szerkesztéskor lemaradt egy idézőjel vagy kulcs | `python3 -c "import yaml; yaml.safe_load(open('${HOME}/.hermes/hermes-agent.yaml'))"`; állítsd vissza biztonsági mentésből |
| A kétnyelvű figyelmeztetés ismétlődően felugrik | A marker fájl törölve vagy az `S1.cap` nincs alkalmazva | Hagyd, hogy a figyelmeztetés egyszer fusson, majd hozd létre újra a markert; vagy alkalmazd az S1.cap patchet a patcherrel |

---

Utoljára ellenőrizve: 2026-06-27.
Vissza a [Telepítéshez](installation.hu.md)