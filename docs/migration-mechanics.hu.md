# Migráció: mechanika és dossier

> [English](migration-mechanics.md) · [Vissza a README-hez](../README.hu.md)
> [Döntési napló](migration.hu.md)

Ez az oldal a migráció mechanikai fele — kontextus, upstream pin, a
generált patch olvasása és a `research/` artifact-térkép. A per-binding
indoklások a [Döntési napló](migration.hu.md) oldalon találhatók.

## Kontextus

A repóban lévő `skills/skill-creator/` fa az Anthropic upstream
`skill-creator` skilljének **portja**, Claude Code-ról Hermes-re
adaptálva. A port megtartja az upstream munkafolyamatot; csak a
„csővezeték" változik.

A migráció három réteget érint:

1. **Frontmatter-szerződés** — dual-runtime kompatibilitás deklarálása,
   hogy ugyanaz a `SKILL.md` működjön a Hermes Agent SDK-ban és a Claude
   Code-ban.
2. **Subprocess-csővezeték** — a `claude -p` helyére `hermes chat -q`
   kerül, és a `CLAUDECODE` strip már nem kell.
3. **Eval pipeline** — az NDJSON stream-parser helyét a
   `hermes sessions export` ShareGPT-formátumú JSONL-je veszi át.

A teljes upstream-binding dossier itt található:
`skills/migration-claude-skill-creator/`. Ez az oldal az olvasható
összefoglaló.

## Upstream pin

A port az
`anthropics/claude-plugins-official` repó
`5fc2987a44918a455ef7dc583b51f8faf875c3ed` commitjához van rögzítve.
A metaadatokat a
`skills/migration-claude-skill-creator/UPSTREAM_COMMIT.txt` rögzíti:

- **Forrás-fa**: `plugins/skill-creator/skills/skill-creator`
- **Lekérés ideje**: 2026-06-22T17:36:25Z
- **Fájlok**: 18, összesen 225 004 byte
- **Fájlonkénti SHA-256**: lásd
  `skills/migration-claude-skill-creator/research/upstream_commit.json`

A commit-SHA-val (és nem branch-címkével) való rögzítés reprodukálhatóvá
teszi a migrációs diffet — a `MIGRATION.patch` egy egységesített diff,
amely pontosan erre a fára alkalmazható.

## A `MIGRATION.patch` olvasása

A `MIGRATION.patch` (31 529 byte) egy egységesített diff az upstream fa
rögzített commitja és a migrált `skills/skill-creator/` fa között.
Generált, nem kézzel írt — alkalmazd az upstream commitot, és pipe-old
a patchet a `git apply`-ba a migráció szó szerinti reprodukálásához.

Hasznos konvenciók a patch olvasásához:

- Útvonal-prefixek — `upstream-skill-creator-5fc2987/...` (bal oldal) a
  worktree útvonalával szemben (jobb oldal). A jobb oldal az, ami a
  repóba kerül.
- `Only in` jelölések — a migráció által bevezetett új fájlokat
  jelölik (pl. `scripts/_subprocess.py`). Nincs bal oldaluk.
- Anchor blokkok — minden binding egy 5 soros anchor-t idéz (`---`
  kivonat) az **upstream** oldalról, így a binding a diff önmagából
  visszafejthető, a migrált forrás újraolvasása nélkül.

## `research/`

A migráció előtti kutatási artifactok itt találhatók:
`skills/migration-claude-skill-creator/research/`:

- `binding_sites_*.json` — nyelvenkénti binding-site regiszterek
  (agents, docs, NDJSON parser, Python scriptek, validation), amelyek
  katalogizálnak minden sort, amelyet a migráció érint.
- `code_review_findings.json` / `code_review_findings_r2.json` — az
  1. és 2. review-kör az generált patchen.
- `hermes_mapping.json` — az upstream-szimbólum → Hermes-szimbólum
  tábla, amely a cseréket hajtja.
- `migrations_applied.json` — a `MIGRATION.md` per-binding táblájának
  géppel olvasható tükörképe.
- `session_inspection_verdict.json` — ítélet arról, hogy a
  `hermes sessions export` JSONL elég struktúrát tartalmaz-e az NDJSON
  parser leváltásához.
- `upstream_commit.json` — teljes fájlonkénti SHA-256 + byte-szám a
  rögzített commitra.

## Lásd még

- [Döntési napló](migration.hu.md) — a 10 binding bejegyzés
  (D4, D5/D11, D15, D16, D17, D18, D20, D21/D22, D23, D24).
- 📖 [Skill-creator](skill-creator.hu.md) — a migrált skill áttekintése.
- 🛠️ [Patch-ek](patches.hu.md) — a cap-felemelés + Task E site patchek,
  amelyek magára a Hermes checkoutra kerülnek alkalmazásra.
- [Forrás migrációs dossier](../skills/migration-claude-skill-creator/MIGRATION.md)
  — a generált per-binding tábla és döntési napló.
