# 🧭 Dokumentáció

[English version](README.md) | [Projekt README](../README.hu.md)

Ez a dokumentáció azok köré a feladatok köré van szervezve, amelyeket az
operátorok és maintainerek a leggyakrabban végeznek. Az angol az alapnyelv; a
magyar fordítások ugyanazon név `.hu.md` párjaiban vannak.

## Kezdd Itt

| Cél | Olvasd |
| --- | --- |
| ⚡ Release bundle használata `uv` nélkül | [Felhasználói telepítés](getting-started.hu.md) |
| 🧰 Command flag-ek és példák | [Parancsok](commands.hu.md) |
| 🧩 Hermes plugin hook config | [Plugin és hookok](plugin.hu.md) |
| 🩹 Hermes patch validálás vagy apply | [Hermes patching](patching.hu.md) |
| 🛠️ Migrált skill creator használata | [Skill creator](skill-creator.hu.md) |
| 📦 Build, verify és release | [Üzemeltetés](operations.hu.md) |
| 🧪 Forrásból fejlesztés `uv`-val | [Fejlesztés](development.hu.md) |
| 🧾 Migrációs döntések | [Migrációs jegyzetek](migration-notes.hu.md) |
| 🪝 Hook döntési folyamatok | [WOW skill folyamatábrák](wow-skills-flowcharts.hu.md) |

## Telepítési Utak

| Út | Használ `uv`-t? | Hermes-en belül fut? | Cél |
| --- | --- | --- | --- |
| Felhasználói telepítés | Nem | Nem | A csomagolt `.pyz` futtatása release wrapper scriptekkel. |
| Hermes plugin bekapcsolás | Nem | Igen | Hermes töltse be a plugint és regisztrálja a hookokat. |
| Fejlesztői setup | Igen | Nem | Szerkesztés, teszt, lint és release artifact build forrásból. |

## Safety Modell

- A támogatott Hermes forrásverzió commitja: `30e947e0a`.
- Pinned checkout validálásához: `--dry-run --target /tmp/hermes-30e947e0a`.
- A patcher ír, ha a `--dry-run` hiányzik.
- A reporter read-only, kivéve ha az operátor JSON output fájlt kér.
- A plugin rövid runtime contextet szúr be; Hermes forrást nem módosít.

## Dokumentációs Stílus

- A parancsok, flag-ek, pathok, env varok és package nevek mindkét nyelven
  angolul maradnak.
- A felhasználói példák release wrapper scripteket használnak; a fejlesztői
  példák `uv run --locked` formát, hogy az `uv.lock` maradjon mérvadó.
- A Mermaid diagramok a flowchart lapokon maradnak, külön validálva.
