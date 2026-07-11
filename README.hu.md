# easter-hermes-sorry-skills

[English version](README.md) | [Dokumentáció](docs/README.hu.md) | [Licenc](LICENSE)

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![Hermes plugin](https://img.shields.io/badge/Hermes-plugin-purple.svg)
![Release artifact](https://img.shields.io/badge/release-.pyz%20%2B%20wrappers-green.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

> Támogatott Hermes commit: `30e947e0a`
> (`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

## Mit Csinál?

Az `easter-hermes-sorry-skills` egy kis kompatibilitási bundle, hogy a Hermes
Agent skill használata közelebb legyen az elvárt Claude-style skill
workflow-hoz. Négy részből áll:

| Rész | Runtime | Cél |
| --- | --- | --- |
| 🩹 Hermes patcher | Release `.pyz` + shell wrapper | A támogatott Hermes checkoutot igazítja, hogy a skill descriptionök és skill-authoring promptok jól működjenek. |
| 🧩 Hermes plugin | Hermes plugin loader | `on_session_start` és `pre_llm_call` hookokat regisztrál, hogy Hermes rövid skill emlékeztetőt kapjon LLM hívás előtt. |
| 🛠️ Migrált skill | Hermes skill rendszer | Az installed OpenAI `skill-creator` skillt cseréli erre a Hermes-kompatibilis verzióra. |
| 📊 Reporter | Release `.pyz` + shell wrapper | Read-only skill metadata és token surface diagnosztikát ír ki. |

A plugin és a migrált `skill-creator` szándékosan külön van. A plugin csak
emlékezteti Hermest, ha a `skill-creator` vagy más enabled skill relevánsnak
tűnik; a tényleges skill betöltés továbbra is Hermes feladata.

## Felhasználói Telepítés

Ha csak használni akarod az eszközt, a release artifact kell. Ehhez nem kell
`uv` setup.

```bash
tar -xzf dist/easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0

bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
bash scripts/easter-hermes-sorry-skills-report.sh
```

A wrapper scriptek megkeresik a `dist/easter-hermes-sorry-skills.pyz` fájlt, és
a becsomagolt Python entry pointot futtatják. Nem hoznak létre virtual envet, és
nem futtatnak `uv`-t.

Másold be a plugin payloadot Hermes user plugin könyvtárába:

```bash
plugin_backup="$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" ] || \
  mv "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin" "$plugin_backup"
mkdir -p "$HOME/.hermes/plugins"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/easter-hermes-sorry-skills-plugin"
```

Cseréld le Hermes installed OpenAI `skill-creator` skilljét erre a Hermes portra:

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

## Hermes Plugin Bekapcsolás

A Hermes plugint Hermes tölti be, nem a wrapper script. A hivatalos Hermes
plugin dokumentáció szerint a general plugin opt-in: egy megtalált plugin csak
akkor töltődik be, ha a neve szerepel a `plugins.enabled` listában.

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
        top_k: 3
        min_score: 2
        log_level: INFO
```

Az `adaptive` mód LLM hívás előtt fut, és csak akkor szúr be rövid
emlékeztetőt, ha a legutóbbi user üzenet illeszkedik enabled skill névre vagy
descriptionre.

## Fejlesztői Setup

`uv` csak akkor kell, ha a repositoryt szerkeszted, teszteket futtatsz, vagy
újraépíted a `dist/` artifactokat.

```bash
uv sync --locked --all-extras --dev
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
scripts/build-release.sh
```

A Python tesztkapu a `pyproject.toml` alapján 100% branch coverage-et vár el.

## Dokumentáció

| Téma | Link |
| --- | --- |
| 🧭 Dokumentáció index | [docs/README.hu.md](docs/README.hu.md) |
| ⚡ Felhasználói telepítés | [docs/getting-started.hu.md](docs/getting-started.hu.md) |
| 🧰 Parancsok | [docs/commands.hu.md](docs/commands.hu.md) |
| 🧩 Plugin és hookok | [docs/plugin.hu.md](docs/plugin.hu.md) |
| 🩹 Hermes patching | [docs/patching.hu.md](docs/patching.hu.md) |
| 🛠️ Skill creator | [docs/skill-creator.hu.md](docs/skill-creator.hu.md) |
| 📦 Üzemeltetés és release | [docs/operations.hu.md](docs/operations.hu.md) |
| 🧪 Fejlesztés | [docs/development.hu.md](docs/development.hu.md) |
| 🧾 Migrációs jegyzetek | [docs/migration-notes.hu.md](docs/migration-notes.hu.md) |
| 🪝 Hook folyamatábrák | [docs/wow-skills-flowcharts.hu.md](docs/wow-skills-flowcharts.hu.md) |

## Licenc

A repository [LICENSE](LICENSE) fájlja MIT licencet tartalmaz. A
`pyproject.toml` metadata belső csomagolási marker; a repository licencfájlja a
redisztribúció forráslicence.
