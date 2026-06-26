# Telepítés — Ellenőrzés, frissítés, eltávolítás

> 🇬🇧 **[English version →](installation-verify.md)**

A tiszta telepítést igazoló smoke teszt, az általa felfedett gyakori
hibamódok, valamint a frissítési és eltávolítási munkafolyamat.

Utoljára ellenőrizve: 2026-06-27 a HEAD `76b7cc3` ellen.

---

## Smoke teszt

Futtasd a telepítési módodnak megfelelő blokkot. Minden parancsnak `0`
exit kóddal kell kilépnie.

### Fejlesztői telepítés (1. mód)

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes --version
uv run --locked easter-hermes-sorry-skills-install-profiles --version
uv run --locked easter-hermes-sorry-skills-report --version

uv run --locked pre-commit run --files pyproject.toml
uv run --locked pytest
```

A pre-commit lépés után minden `git commit` futtatja a
`.pre-commit-config.yaml`-ban definiált kaput.

### Release artifact (2. mód)

```bash
easter-hermes-sorry-skills-patch-hermes --version
easter-hermes-sorry-skills-install-profiles --version
easter-hermes-sorry-skills-report --version

easter-hermes-sorry-skills-patch-hermes --help --lang en
easter-hermes-sorry-skills-patch-hermes --help --lang hu
easter-hermes-sorry-skills-install-profiles --help --lang en
easter-hermes-sorry-skills-report --help --lang en

easter-hermes-sorry-skills-install-profiles
easter-hermes-sorry-skills-report --format text

python3 -m zipfile -l dist/easter-hermes-sorry-skills.pyz | head
./dist/easter-hermes-sorry-skills.pyz -c "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__name__)"

.venv/bin/python3 -c "from easter_hermes_sorry_skills import cli_patch; cli_patch._main_entry()" -- --help
```

Az utolsó sor ugyanaz a hívás, amit a wrapper a motorháztető alatt
végrehajt; egyszeri futtatása bizonyítja, hogy a wrapper `exec` szerződése
ép.

### Hermes plugin (3. mód)

```bash
readlink -f ~/.hermes/skills/skill-creator

~/.hermes/hermes-agent --list-skills | grep skill-creator

~/.hermes/hermes-agent --prompt "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__file__)"
```

A tiszta telepítés kiírja minden CLI verzióját, az EN és HU help szekciót
is, és minden parancs `0` exit kóddal lép ki. Ha bármelyik parancs
nem-nullával lép ki, vagy a `.pyz` zip listájából hiányzik a
`site-packages/`, a telepítés hibás; NE lépj tovább a
[docs/usage.hu.md](usage.hu.md)-ra; helyette menj az alábbi
hibakezelési táblázathoz. A megfelelő `bats` ellenőrzések a
`tests/bats/{patch-hermes,install-profiles,report}.bats` fájlokban
találhatók.

---

## Hibakezelés

| # | Tünet | Ok | Megoldás |
|---|---|---|---|
| 1 | `error: Python 3.13 or older is not supported` | A `requires-python = ">=3.14"` (`pyproject.toml:6`) nem teljesült; a `python3` < 3.14-re oldódik fel | Telepíts Python 3.14-et és exportáld újra a `PATH`-t; vagy add meg a `--python 3.14` kapcsolót az `uv sync` parancsnak |
| 2 | `uv: command not found` | Az `uv` nincs a `PATH`-on (csak fejlesztői módban) | Telepítsd a `curl -LsSf https://astral.sh/uv/install.sh \| sh` paranccsal, majd source-old újra a shell profilod |
| 3 | `shiv: command not found` (csak build gépen; a release artifact ÉRINTETLEN) | A `shiv>=1.0,<2.0` nem került telepítésre a venv-be | `uv sync --locked --all-extras --dev` egyszer a fejlesztői gépen; a `scripts/build-release.sh` build időben telepíti a `shiv`-et |
| 4 | `.venv/bin/python3: No such file or directory` | Friss checkout venv bootstrap nélkül | `uv sync --locked --all-extras --dev` egyszer; a további parancsok a `.venv/` létezését feltételezik |
| 5 | `easter-hermes-sorry-skills-patch-hermes: command not found` (fejlesztői telepítés) | A wrapper `uv run --locked` nélkül futott | Prefixeld `uv run --locked` kapcsolóval, vagy használd közvetlenül a `.venv/bin/easter-hermes-sorry-skills-patch-hermes` fájlt |
| 6 | `Permission denied` patchek alkalmazásakor egy Hermes checkouton | A checkout csak olvasható vagy más felhasználó tulajdona | `chown -R "${USER}": /path/to/user-hermes`; a patcher 3-as exit kóddal lép ki jogosultsági hibáknál |
| 7 | `Skill not found` a `~/.hermes/hermes-agent`-ből | Sérült symlink vagy `skills_dirs` hiányzik a `~/.hermes/hermes-agent.yaml`-ból | A `readlink -f ~/.hermes/skills/skill-creator` oldjon fel; adj hozzá `skills_dirs: [~/.hermes/skills]` bejegyzést |
| 8 | `JSON parse error` az `easter-hermes-sorry-skills-report`-ból | A `~/.hermes/hermes-agent.yaml` hibás (kézi szerkesztéskor lemaradt egy idézőjel) | `python3 -c "import yaml; yaml.safe_load(open('${HOME}/.hermes/hermes-agent.yaml'))"`; állítsd vissza biztonsági mentésből |
| 9 | A `--lang hu` szekció hiányzik vagy a `--help` csak `[en]`-t ír ki | Egyedi `--help` felüldefiniálás törölt egy szekciót, vagy Python 3.13-on fut (3.14 kell a kétnyelvű táblázatokhoz) | Generáld újra az `uv sync --locked --all-extras --dev` paranccsal; NE szerkeszd kézzel a `messages_en.py` / `messages_hu.py` fájlokat; ellenőrizd, hogy a `python3 --version` 3.14.x-et írjon |

Ha a fentiek egyike sem illik, rögzítsd a teljes parancsot, annak exit
kódját és a stderr első 10 sorát, majd nyiss egy issue-t.

---

## Frissítés

Egy új release három lépésben frissül. Az 1-2. lépések feltételezik,
hogy a repót `git pull`-lal követed; a 3. lépés az artifact frissítés.

```bash
# 1. Fejlesztés: pull és a venv frissítése
git pull origin main
uv sync --locked --all-extras --dev

# 2. Release artifact: új tarball letöltése és csere
curl -L -o easter-hermes-sorry-skills.tar.gz \
  https://github.com/EggProject/easter-skills-hack-to-hermes/releases/download/<NEW_VERSION>/easter-hermes-sorry-skills-<NEW_VERSION>.tar.gz
tar -xzf easter-hermes-sorry-skills.tar.gz --overwrite
cd easter-hermes-sorry-skills-<NEW_VERSION>/
ln -sf "$(pwd)/scripts/easter-hermes-sorry-skills-*.sh" ~/bin/
ln -sf "$(pwd)/dist/easter-hermes-sorry-skills.pyz" ~/bin/

# 3. Hermes plugin: a symlink újrakészítése (a repóra mutat, így az 1. lépés már lefedi)
ln -sf "$(pwd)/skills/skill-creator" ~/.hermes/skills/skill-creator
```

Rendszerszintű release frissítéshez:

```bash
sudo cp easter-hermes-sorry-skills-<NEW_VERSION>/scripts/easter-hermes-sorry-skills-*.sh /usr/local/bin/
sudo cp easter-hermes-sorry-skills-<NEW_VERSION>/dist/easter-hermes-sorry-skills.pyz /usr/local/bin/
```

Bármilyen frissítés után futtasd újra a [Smoke teszt](#smoke-teszt) szakaszt.
Megjegyzés a `pyproject.toml:6` sorhoz (`requires-python = ">=3.14"`): ha
egy release megemeli a minimális verziót, a régi interpreteren a telepítés
elutasítódik. Előbb nézd meg a release notes-t, ha egy korábban tiszta
gépen az `uv sync` hirtelen elkezd hibázni.

---

## Eltávolítás

```bash
# 1. Fejlesztés: a venv törlése
rm -rf .venv

# 2. Release artifact: a wrapper-ek + .pyz törlése
rm -rf ~/bin/easter-hermes-sorry-skills-* ~/bin/easter-hermes-sorry-skills.pyz
# Vagy rendszerszintű telepítés esetén:
sudo rm -f /usr/local/bin/easter-hermes-sorry-skills.pyz
sudo rm -f /usr/local/bin/easter-hermes-sorry-skills-{patch-hermes,install-profiles,report}.sh

# 3. Hermes plugin: a symlink + plugin fa törlése
rm -f  ~/.hermes/skills/skill-creator                                # a symlink
rm -rf ~/.hermes/python-extras/easter_hermes_sorry_skills            # a plugin fa

# 4. A ~/.hermes/hermes-agent.yaml visszaállítása (ha módosítottad)
cp ~/.hermes/hermes-agent.yaml.bak ~/.hermes/hermes-agent.yaml      # ha készítettél biztonsági mentést

# 5. A 8 patch visszavonása (Hermes oldalán; checkout-onként)
cd /path/to/user-hermes
git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py
```

Az 5. lépés csak akkor kell, ha a 3. módban egy felhasználó által birtokolt
Hermes checkout ellen telepítettél. Az 1-4. lépések a kanonikus eltávolítás
az 1. és 2. módhoz. A plugin egyszeri figyelmeztetés markere
(`~/.hermes/.easter_hermes_sorry_skills_advisory_seen`) szándékosan a
helyén marad; töröld kézzel, ha szeretnéd, hogy a figyelmeztetés újra
felugráljon az újratelepítés után.

A build artifactoknak a repóból való törléséhez (csak fejlesztői mód):

```bash
git clean -fdx dist/
```

Ez törli a `dist/*.pyz` és `dist/*.tar.gz` fájlokat.

---

Utoljára ellenőrizve: 2026-06-27.
Vissza a [Telepítéshez](installation.hu.md)