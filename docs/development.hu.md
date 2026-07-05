# 🧪 Fejlesztés

[English version](development.md) | [Dokumentáció](README.hu.md)

## Helyi Környezet

```bash
uv sync --locked --all-extras --dev
uv run --locked pre-commit install
```

Python toolokhoz használj `uv run --locked` formát. A közvetlen `pytest`,
`ruff`, `black` vagy `mypy` futtatás eltérhet a lockolt környezettől.

## Teszt Kapu

```bash
uv run --locked pytest -q
```

A `pyproject.toml` branch coverage-et kapcsol be, és `--cov-fail-under=100`
értéket vár. Új Python kódnál a teszteknek teljesen le kell fedniük.

## Lint Kapu

```bash
uv run --locked pre-commit run --all-files --show-diff-on-failure
```

A kapu szigorú Python lintet, formatot, mypy-t, shell checkeket és helyi meta
ellenőrzéseket futtat.

## Hermes Kompatibilitás

Ne használj live Hermes checkoutot fejlesztési validálásra, ha van pinned
target. Validálási cél:

```bash
/tmp/hermes-30e947e0a
```

Fejlesztési handoff közben a patchert csak `--dry-run` módban futtasd:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

## Dokumentációs Szabályok

- Az angol a kanonikus.
- A magyar fordítás ugyanaz a fájlnév plusz `.hu.md`.
- A `docs/wow-skills-flowcharts.md` és `docs/wow-skills-flowcharts.hu.md`
  megtartja a hook diagramokat és példákat.
- A példák legyenek futtathatók; pontos parancs jobb, mint csak próza.

## Branch Workflow

Feature branchben dolgozz, pushold, nyisd vagy frissítsd a PR-t, és várd meg a
zöld CI-t. Minden új változás külön új commit legyen.

