# ⚡ Felhasználói Telepítés

[English version](getting-started.md) | [Dokumentáció](README.hu.md)

Ez az oldal operátoroknak szól, akik a release artifactot akarják használni.
Külön van választva a [fejlesztői setuptól](development.hu.md).

## Követelmények

| Követelmény | Miért kell |
| --- | --- |
| Python `>=3.14` | A `.pyz` zipapp a rendszer `python3` parancsával fut. |
| Release artifact | Tartalmazza a `dist/easter-hermes-sorry-skills.pyz` fájlt és a shell wrapper-eket. |
| Hermes checkout | Patch dry-run target, validáláshoz általában `/tmp/hermes-30e947e0a`. |

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
README.md
README.hu.md
```

## 2. Patcher Futtatása Dry-Run Módban

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

A wrapper a becsomagolt `.pyz` fájlt futtatja. Nem hoz létre `.venv/`
könyvtárat, nem telepít dependencyket, és nem hív `uv`-t.

## 3. Read-Only Report Futtatása

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

Használd a `--format json --json PATH` opciókat, ha másik toolnak strukturált
kimenet kell.

## 4. Hermes Plugin Külön Bekapcsolása

A CLI bundle és a Hermes plugin két külön install felület. A wrapper scriptek
Hermes-en kívül futnak. A plugin Hermes-en belül, a Hermes plugin loaderén
keresztül fut, és ott kell megtalálhatóvá tenni és engedélyezni.

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

## Nem Fejlesztői Setup

Ha a repositoryt szerkeszted, teszteket futtatsz, vagy újraépíted a release
artifactot, a [Fejlesztés](development.hu.md) oldal kell. A `uv sync --locked
--all-extras --dev` oda tartozik.
