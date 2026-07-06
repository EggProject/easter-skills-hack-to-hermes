# easter-hermes-sorry-skills

[English version](README.md) | [Dokumentáció](docs/README.hu.md) | [Licenc](LICENSE)

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![Hermes plugin](https://img.shields.io/badge/Hermes-plugin-purple.svg)
![Release artifact](https://img.shields.io/badge/release-.pyz%20%2B%20wrappers-green.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

> Támogatott Hermes commit: `30e947e0a`
> (`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

## Mit Csinál?

Az `easter-hermes-sorry-skills` két külön felületet ad:

| Felület | Runtime | Cél |
| --- | --- | --- |
| 🧩 Hermes plugin | Hermes saját Python/plugin loader | `on_session_start` és `pre_llm_call` hookokat regisztrál. |
| 🧰 Operátori CLI bundle | `dist/easter-hermes-sorry-skills.pyz` + shell wrapper-ek | Patch dry-run/apply és read-only riport Hermes-en kívül. |

A migrált `skill-creator` külön él a `skills/skill-creator/` alatt. A plugin
emlékeztetheti Hermest a releváns skill betöltésére, de nem csomagolja és nem
birtokolja ezt a skillt.

## Felhasználói Telepítés

Ha csak használni akarod az eszközt, a release artifact kell. Ehhez nem kell
`uv` setup.

```bash
tar -xzf dist/easter-hermes-sorry-skills-v0.1.0.tar.gz
cd easter-hermes-sorry-skills-v0.1.0

bash scripts/easter-hermes-sorry-skills-patch-hermes.sh \
  --dry-run \
  --target /tmp/hermes-30e947e0a

bash scripts/easter-hermes-sorry-skills-report.sh
```

A wrapper scriptek megkeresik a `dist/easter-hermes-sorry-skills.pyz` fájlt, és
a becsomagolt Python entry pointot futtatják. Nem hoznak létre virtual envet, és
nem futtatnak `uv`-t.

## Hermes Plugin Bekapcsolás

A Hermes plugint Hermes tölti be, nem a wrapper script. A hivatalos Hermes
plugin dokumentáció szerint a general plugin opt-in: egy megtalált plugin csak
akkor töltődik be, ha a neve szerepel a `plugins.enabled` listában.

A jelenlegi release bundle nem Hermes plugin installer. Az operátori CLI
bundle-t adja. A plugint külön kell Hermes plugin discovery útvonalon
telepíthetővé vagy láthatóvá tenni, majd ezzel a configgal bekapcsolni és
hangolni.

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
