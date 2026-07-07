# ⚡ Felhasználói Telepítés

[English version](getting-started.md) | [Dokumentáció](README.hu.md)

Ez az oldal operátoroknak szól, akik a release artifactot akarják használni.
Külön van választva a [fejlesztői setuptól](development.hu.md).

## Követelmények

| Követelmény | Miért kell |
| --- | --- |
| Python `>=3.14` | A `.pyz` zipapp a rendszer `python3` parancsával fut. |
| Release artifact | Tartalmazza a wrapper-eket, a Hermes plugin payloadot és a migrált `skill-creator` skillt. |
| Hermes checkout | A patch wrapper alapból Hermes live checkout pathra céloz. |

Felhasználói telepítéshez nem kell `uv` parancs.

## 1. Release Bundle Kibontása

```bash
tar -xzf dist/easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0
```

A bundle tartalma:

```text
dist/easter-hermes-sorry-skills.pyz
scripts/easter-hermes-sorry-skills-patch-hermes.sh
scripts/easter-hermes-sorry-skills-report.sh
plugin/easter-hermes-sorry-skills-plugin/
skills/skill-creator/
README.md
README.hu.md
```

## 2. Hermes Plugin Payload Telepítése

```bash
plugin_backup="$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" ] || \
  mv "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" "$plugin_backup"
mkdir -p "$HOME/.hermes/plugins"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin"
```

A Hermes directory plugin helye `~/.hermes/plugins/<plugin-name>/`, és kell
bele `plugin.yaml` plusz `__init__.py`. A release bundle pontosan ezt adja a
`plugin/easter-hermes-sorry-skills-plugin/` könyvtárban.

## 3. Installed `skill-creator` Cseréje

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

Ez az installed OpenAI `skill-creator` skillt cseréli le a repository
Hermes-portjára. A backup lépés megőrzi az előző könyvtárat, ha létezik.

## 4. Hermes Plugin Bekapcsolása

A wrapper scriptek Hermes-en kívül futnak. A plugin Hermes-en belül, a Hermes
plugin loaderén keresztül fut, és Hermes configban kell engedélyezni.

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
  entries:
    easter-hermes-sorry-skills-plugin:
      skill_hook:
        enabled: true
        mode: adaptive
        output: shortlist
```

A runtime működést a [Plugin és hookok](plugin.hu.md) oldal írja le.

## 5. Patcher Futtatása Dry-Run Módban

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
```

A wrapper a becsomagolt `.pyz` fájlt futtatja. Nem hoz létre `.venv/`
könyvtárat, nem telepít dependencyket, és nem hív `uv`-t.

## 6. Read-Only Report Futtatása

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

Használd a `--format json --json PATH` opciókat, ha másik toolnak strukturált
kimenet kell.

## Nem Fejlesztői Setup

Ha a repositoryt szerkeszted, teszteket futtatsz, vagy újraépíted a release
artifactot, a [Fejlesztés](development.hu.md) oldal kell. A `uv sync --locked
--all-extras --dev` oda tartozik.
