# Telepítés — Release artifact

> 🇬🇧 **[English version →](installation-release.md)**

A 2. mód: egy önálló `.pyz` + három bash wrapper fájl kerül a `PATH`-ra.
Nincs forrásfa, nincs `uv`, nincs `pip`. Oprátor hosztokon és CI runner-eken
használd, amelyeknek csak a három CLI-t kell futtatniuk.

Utoljára ellenőrizve: 2026-06-27 a `dist/easter-hermes-sorry-skills-v0.1.0.tar.gz` ellen (HEAD `76b7cc3`).

---

## Miért a release artifact?

| | Fejlesztői telepítés | Release artifact |
|---|---|---|
| Elrendezés | Forrásfa + `.venv/` | Önálló `.pyz` (zipapp) + 3 bash wrapper |
| Futtatókörnyezeti függőségek | Python 3.14 + `uv` + zárolt venv | Csak Python 3.14 a `PATH`-on |
| Forrás szerkeszthető | Igen | Nem |
| Fájlméret | `.venv/` ≈ 80 MB | `.pyz` ≈ 5.6 MB |
| Terjesztés | `git clone` | `curl -L` a GitHub release-ről |

A release módot production hosztokon és operátor munkaállomásokon válaszd.
A fejlesztői módot
([installation.md § 1. mód](installation.md)) akkor válaszd, ha a kódot
szeretnéd szerkeszteni.

---

## Előfeltételek

| Eszköz | Verzió | Megjegyzés |
|---|---|---|
| Python | `>=3.14` | A shebang a rendszer `python3`-ra mutat; a `requires-python = ">=3.14"` (`pyproject.toml:6`) build időben érvényesítve |
| `curl` | bármely | `wget` is működik |
| `tar` + `gzip` | bármely | A `tar -xzf` GNU `tar`-t igényel (BSD-ken: `gtar`) |
| `PATH` írási jog | `~/bin/`, `/usr/local/bin/` vagy hasonló | A `~/bin/` az alapértelmezett egyfelhasználós esetben |

Az artifact (`dist/easter-hermes-sorry-skills-v0.1.0.tar.gz`)
tartalmazza a `scripts/*.sh` fájlokat (15 soros bash wrapper-ek, amelyek
a mellettük lévő `.pyz`-t feloldják és `exec`-kel hívják a belépési pontot),
a `dist/*.pyz` fájlt (shiv által épített zipapp, ami a Python 3.14
site-packages-t ágyazza be), valamint a `skills/skill-creator/` könyvtárat
(a 3. módhoz). Nincs `uv`, nincs `git`, nincs hálózat futásidőben.

---

## Telepítés

```bash
# 1. Release artifact letöltése
curl -L -o easter-hermes-sorry-skills.tar.gz \
  https://github.com/EggProject/easter-skills-hack-to-hermes/releases/download/v0.1.0/easter-hermes-sorry-skills-v0.1.0.tar.gz

# 2. Kicsomagolás
tar -xzf easter-hermes-sorry-skills.tar.gz
cd easter-hermes-sorry-skills-v0.1.0

# 3. Wrapper szkriptek symlinkelése a ~/bin-be
mkdir -p ~/bin
for script in scripts/easter-hermes-sorry-skills-*.sh; do
  ln -sf "$(pwd)/${script}" ~/bin/$(basename "${script%.sh}")
done

# 4. A .pyz symlinkelése, hogy a wrapper-ek a ../dist/, ./dist/ vagy ./ útvonalat megtalálják
ln -sf "$(pwd)/dist/easter-hermes-sorry-skills.pyz" ~/bin/easter-hermes-sorry-skills.pyz

# 5. A ~/bin PATH-ra kerülésének ellenőrzése
case ":${PATH}:" in
  *":${HOME}/bin:"*) ;;
  *) export PATH="${HOME}/bin:${PATH}" ;;
esac
```

A wrapper-ek a `.pyz`-t maguk mellett keresik (`../dist/`, `./dist/`, majd
`./`). Ha a symlinket a wrapper symlinkek mellé tesszük a `~/bin/`-be, ez
a szerződés megmarad. Rendszerszintű telepítéshez:

```bash
sudo cp easter-hermes-sorry-skills-v0.1.0/scripts/easter-hermes-sorry-skills-*.sh /usr/local/bin/
sudo cp easter-hermes-sorry-skills-v0.1.0/dist/easter-hermes-sorry-skills.pyz /usr/local/bin/
```

A `chmod +x` nem szükséges: az `.sh` fájlok az executable bit-tel együtt
érkeznek, a `.pyz` pedig a Python shebangjén keresztül fut.

---

## Ellenőrzés

```bash
# 1. A wrapper feloldja a .pyz-t és 0-val lép ki
easter-hermes-sorry-skills-patch-hermes --version
easter-hermes-sorry-skills-report --version

# 2. A kétnyelvű help kiírja az EN és HU szekciót
easter-hermes-sorry-skills-patch-hermes --help --lang en
easter-hermes-sorry-skills-patch-hermes --help --lang hu

# 3. A .pyz érvényes zipapp és önállóan fut
python3 -m zipfile -l dist/easter-hermes-sorry-skills.pyz | head
./dist/easter-hermes-sorry-skills.pyz -c "import easter_hermes_sorry_skills; print(easter_hermes_sorry_skills.__name__)"
```

A tiszta telepítés minden `--version`-ből kiírja az
`easter-hermes-sorry-skills 0.1.0` szöveget, a `--help --lang en`-ből
mind a `[en]`, mind a `[hu]` blokkot, a `-c` hívásból pedig a csomagnevet.
Teljes smoke teszt: [installation-verify.md](installation-verify.md).

---

## Hibakezelés

| Tünet | Ok | Megoldás |
|---|---|---|
| `ERROR: dist/easter-hermes-sorry-skills.pyz: No such file or directory` | A wrapper nem találja a `.pyz`-t maga mellett | Symlinkeld a `.pyz`-t a `~/bin/`-be (4. lépés); vagy másold a `scripts/*.sh` és `dist/*.pyz` fájlokat ugyanabba a célkönyvtárba |
| `zipfile.BadZipFile: File is not a zip file` | A `.pyz` csonka vagy a letöltés félbeszakadt | `rm easter-hermes-sorry-skills.pyz` és futtasd újra az 1. lépést `-L` kapcsolóval; ellenőrizd a méretet `wc -c`-vel |
| `ModuleNotFoundError: easter_hermes_sorry_skills` (közvetlen `.pyz` hívás) | A `.pyz` rossz belépési pont ellen készült | Használd a wrapper-eket (ők a helyes `-c` snippetet hívják); vagy építsd újra a `scripts/build-release.sh --only-shiv` paranccsal |
| `Python 3.13 or older is not supported` | A `python3` a `PATH`-on < 3.14-re oldódik fel | Telepíts Python 3.14-et és exportáld újra a `PATH`-t; ne kerüld ki `--break-system-packages` kapcsolóval |
| `shiv: command not found` (csak build gépen) | A `shiv>=1.0,<2.0` nem került telepítésre a venv-be | `uv sync --locked --all-extras --dev` egyszer a fejlesztői gépen; csak buildeléshez kell, NEM érinti a release artifactot |

A `shiv` sor az egyetlen, ami a build gépéhez tartozik. A 2. módot futtató
operátoroknak nincs szükségük `shiv`-re, `uv`-re vagy `git`-re.

---

Utoljára ellenőrizve: 2026-06-27.
Vissza a [Telepítéshez](installation.hu.md)