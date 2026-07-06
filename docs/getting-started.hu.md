# ⚡ Első Lépések

[English version](getting-started.md) | [Dokumentáció](README.hu.md)

## Előfeltételek

| Eszköz | Miért kell |
| --- | --- |
| Python `>=3.14` | Project runtime és release zipapp cél. |
| `uv` | Virtual env, dependency sync és locked command runner. |
| Git | Branch, PR workflow és release metadata. |
| Hermes checkout | `30e947e0a` commit elleni validáláshoz. |

## 1. Project Előkészítése

```bash
uv sync --locked --all-extras --dev
```

Az `uv run --locked` nem frissíti implicit módon a lockfile-t. Így a helyi
parancsok ugyanazzal az `uv.lock` állapottal futnak, mint a CI.

## 2. Hermes Validálás Írás Nélkül

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

Olvasd át a kiírt tervet. A drift azt jelenti, hogy a patch anchorok már nem
illeszkednek a támogatott Hermes forráskódhoz, és apply mód előtt javítani kell.

## 3. Plugin Bekapcsolása

Add hozzá a csomagot Hermes pluginként, majd állítsd be a hookot a
`config.yaml` fájlban:

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

A hook az enabled skill listát a Hermes runtime API-n keresztül olvassa. Nem
pásztáz profil könyvtárakat kézzel.

## 4. Skill Állapot Ellenőrzése

```bash
uv run --locked easter-hermes-sorry-skills-report
```

Használd a `--format json --json PATH` opciókat, ha másik toolnak strukturált
kimenet kell.

## Következő

- [Parancsok](commands.hu.md) listázza a flag-eket.
- [Plugin és hookok](plugin.hu.md) magyarázza az `adaptive`, `first`, `off` módokat.
- [Hermes patching](patching.hu.md) írja le a patch site-okat és dry-run outputot.
