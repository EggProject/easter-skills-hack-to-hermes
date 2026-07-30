# easter-hermes-sorry-skills

[English README](README.md) | [Részletes dokumentáció](docs/README.hu.md) | [Licenc](LICENSE)

Ez a projekt egyszerűbbé és megbízhatóbbá teszi a skillek használatát a
Hermes Agentben. Segít Hermesnek felismerni, mikor hasznos egy telepített
skill, javítja a skill-leírásokat, és riportot tud készíteni az aktív
skillekről.

A projekt tartalma:

- patcher a támogatott Hermes verzióhoz;
- Hermes plugin, amely LLM-hívás előtt jelzi a releváns skilleket;
- Hermes-kompatibilis `skill-creator`;
- csak olvasó skill riport.

Támogatott Hermes commit: `a4973c3f11d9cc92da986cbe150d1e79d094626f`.

## Mi Kell Hozzá?

- Python 3.14 vagy újabb
- Hermes Agent
- Git

Normál használathoz nem kell `uv`.

## Telepítés

Klónozd a repositoryt:

```bash
git clone https://github.com/EggProject/easter-skills-hack-to-hermes.git
cd easter-skills-hack-to-hermes
```

Másold be a plugint és a `skill-creator` skillt a Hermes könyvtárába:

```bash
mkdir -p "$HOME/.hermes/plugins" "$HOME/.hermes/skills"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/"
cp -R skills/skill-creator "$HOME/.hermes/skills/"
```

Ha valamelyik célkönyvtár már létezik, másolás előtt töröld vagy mentsd el.
A [részletes telepítési leírás](docs/getting-started.hu.md) biztonságos
frissítési lépéseket is tartalmaz.

Engedélyezd a plugint a `~/.hermes/config.yaml` fájlban:

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
```

Ellenőrizd a Hermes patch tervét fájlmódosítás nélkül:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
```

Ha a terv megfelelő, alkalmazd a patch-et:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh
```

## Skill Riport

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

A reporter csak olvassa a Hermes adatait, kivéve, ha kifejezetten JSON
kimeneti fájlt kérsz.

## További Dokumentáció

- [Telepítés és frissítés](docs/getting-started.hu.md)
- [Parancsok és opciók](docs/commands.hu.md)
- [Plugin konfiguráció](docs/plugin.hu.md)
- [Fejlesztés](docs/development.hu.md)
- [Release folyamat](docs/operations.hu.md)

## Licenc

A projekt az [MIT Licenc](LICENSE) alatt használható. A migrált
`skill-creator` saját licence a
[`skills/skill-creator/LICENSE.txt`](skills/skill-creator/LICENSE.txt) fájlban
található.
