# easter-hermes-sorry-skills

[English version](README.md) | [Dokumentáció](docs/README.hu.md) | [Licenc](LICENSE)

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![uv managed](https://img.shields.io/badge/uv-managed-green.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)
![Hermes](https://img.shields.io/badge/Hermes-30e947e0a-purple.svg)

> Támogatott Hermes commit: `30e947e0a`
> (`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

## Mit Csinál?

Az `easter-hermes-sorry-skills` egy kis Hermes kiegészítő csomag skill
betöltéshez és skill-authoring workflow-khoz.

| Terület | Cél |
| --- | --- |
| 🧩 Hermes plugin | `on_session_start` és `pre_llm_call` hookokat regisztrál. |
| 🪝 WOW skill hook | LLM hívás előtt emlékezteti a modellt a releváns enabled skill-ekre. |
| 🩹 Hermes patcher | A támogatott Hermes checkoutot igazítja a jobb skill prompt működéshez. |
| 🧰 Migrált skill | Hermes-kompatibilis `skills/skill-creator/` könyvtárat szállít. |
| 📊 Reporter | Config módosítás nélkül mutatja az enabled skill metaadatokat és token felületet. |

A plugin nem birtokolja és nem csomagolja be a migrált `skill-creator` skillt.
Az külön, top-level artifactként él a `skills/skill-creator/` alatt.

## Gyors Indulás

```bash
uv sync --locked --all-extras --dev

# Pinned Hermes checkout validálása írás nélkül.
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a

# Enabled skill használat ellenőrzése.
uv run --locked easter-hermes-sorry-skills-report
```

A patcher alapból ír. Validáláshoz és operátori ellenőrzéshez használd a
`--dry-run` kapcsolót, és csak utána fusson ugyanaz a parancs `--dry-run`
nélkül.

## Parancsok

| Parancs | Ír? | Megjegyzés |
| --- | --- | --- |
| `easter-hermes-sorry-skills-patch-hermes` | Igen, ha nincs `--dry-run` | Hermes checkoutot patchel. |
| `easter-hermes-sorry-skills-report` | Nem, kivéve operátor által megadott JSON output | Profilokat és skill metaadatokat olvas. |

## Skill Hook Config

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

Az `adaptive` mód minden turnnél lefut, de csak akkor szúr be rövid
emlékeztetőt, ha az aktuális user üzenet illeszkedik enabled skill névre vagy
descriptionre. A már betöltött skill-eket betöltött contextként kezeli, ezért
nem ajánlja újra erős jelzéssel.

## Dokumentáció

| Téma | Link |
| --- | --- |
| 🧭 Dokumentáció index | [docs/README.hu.md](docs/README.hu.md) |
| ⚡ Első lépések | [docs/getting-started.hu.md](docs/getting-started.hu.md) |
| 🧰 Parancsok | [docs/commands.hu.md](docs/commands.hu.md) |
| 🧩 Plugin és hookok | [docs/plugin.hu.md](docs/plugin.hu.md) |
| 🩹 Hermes patching | [docs/patching.hu.md](docs/patching.hu.md) |
| 🛠️ Skill creator | [docs/skill-creator.hu.md](docs/skill-creator.hu.md) |
| 📦 Üzemeltetés és release | [docs/operations.hu.md](docs/operations.hu.md) |
| 🧪 Fejlesztés | [docs/development.hu.md](docs/development.hu.md) |
| 🧾 Migrációs jegyzetek | [docs/migration-notes.hu.md](docs/migration-notes.hu.md) |
| 🪝 Hook folyamatábrák | [docs/wow-skills-flowcharts.hu.md](docs/wow-skills-flowcharts.hu.md) |

## Minőségi Kapu

```bash
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
scripts/build-release.sh
```

A Python tesztkapu a `pyproject.toml` alapján 100% branch coverage-et vár el.
A release artifactok a `dist/` mappába kerülnek, és release-t érintő változás
után a `dist/` legyen a legfrissebb build.

## Licenc

A repository [LICENSE](LICENSE) fájlja MIT licencet tartalmaz. A
`pyproject.toml` metadata belső csomagolási marker; a repository licencfájlja a
redisztribúció forráslicence.
