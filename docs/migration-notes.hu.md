# 🧾 Migrációs Jegyzetek

[English version](migration-notes.md) | [Dokumentáció](README.hu.md)

## Jelenlegi Állapot

Ez a repository Hermes skill/plugin migrációs kísérletként indult. A publikus
dokumentáció most a szállított működést írja le, nem a régi tervezési archívot
őrzi.

## Megőrzött Döntések

| Döntés | Jelenlegi forma |
| --- | --- |
| Hermes pin | A patch kompatibilitás `30e947e0a` commit ellen dokumentált. |
| Plugin szétválasztás | A plugin hookokat regisztrál; a migrált skill top-level artifact. |
| Skill emlékeztető | A `pre_llm_call` rövid adaptive emlékeztetőt ad, nem teljes skill bodyt. |
| Betöltött skill kezelés | A már betöltött skill-eket conversation historyból felismeri és gyengébben jelzi. |
| Biztonságos validálás | A patcher dry-run a review út operátori apply előtt. |

## Mi Került Ki A Publikus Docsból?

A régi `docs/plans`, generált auditok és vendored research másolatok kikerültek
a publikus dokumentációs felületből. Ezek történeti tervezési állapotot, stale
implementációs állításokat és nyers kutatási artifactokat tartalmaztak, amelyek
már nem segítették az aktuális projekt megértését.

## Mi Maradt Részletes?

A hook flowchartok megmaradtak, mert a live `pre_llm_call` működést jobban
magyarázzák, mint a próza:

- [WOW skill flowchartok](wow-skills-flowcharts.md)
- [Magyar flowchartok](wow-skills-flowcharts.hu.md)

