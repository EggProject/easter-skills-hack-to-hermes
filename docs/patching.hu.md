# 🩹 Hermes Patching

[English version](patching.md) | [Dokumentáció](README.hu.md)

## Támogatott Cél

A jelenlegi patch set a Hermes `30e947e0a`
(`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`) commitjához van karbantartva.

Operátori validáláshoz dry-runt használj:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
```

Forrásból fejlesztésnél a lockolt környezetet használd:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run
```

## Mit Patchel?

| Terület | Hatás |
| --- | --- |
| Skill description cap | A lokális description limitet 1024 karakterre emeli. |
| Skill prompt guidance | Olyan iránymutatást ad, hogy a modellek skill szerkesztés/létrehozás előtt konzultáljanak a `skill-creator` skillel. |
| Prompt snapshot | Sikeres write mód után törli a skills prompt snapshotot, hogy Hermes újraépítse a contextet. |

A patcher írás előtt exact anchorokat validál. A drift azt jelenti, hogy Hermes
változott egy patch site körül, és a site táblázatot frissíteni kell.

## Dry-Run Output

A dry-run tervet ír ki, és nem módosít target fájlokat.

```text
◇ plan for /path/to/hermes:
• would patch: agent/prompt_builder.py (site E1.skills_guidance)
⚠ --dry-run mode, patches were NOT applied
```

A dry-run kimenet a review artifact. Apply módban ugyanazt a checkoutot
használd, miután a terv elfogadott.

## Operátori Apply

Apply mód ugyanaz a parancs `--dry-run` nélkül:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh
```

Ne apply-olj ellenőrizetlen checkoutra. Először validáld a pontos forrásverziót.

## Hibakeresés

| Tünet | Jelentés | Teendő |
| --- | --- | --- |
| `line drift detected` | Az anchor text elmozdult vagy megváltozott. | Frissítsd a patch site-ot a támogatott Hermes commithoz. |
| `validation failed` | Egy vagy több patch site nem bizonyítható biztonságosnak. | Ne apply-olj; javítsd az anchorokat és futtasd újra dry-runban. |
| Nincs target match | Rossz vagy hiányos checkout path. | Ellenőrizd a `--target` értéket. |
