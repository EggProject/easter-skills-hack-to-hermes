# Migráció: claude-plugins-official → Hermes

> [English](migration.md) · [Vissza a README-hez](../README.hu.md)
> [Mechanika és dossier](migration-mechanics.hu.md)

## Döntési napló

Az alábbi döntések mindegyike egy-egy binding a `MIGRATION.md`-ben. A
formátum **Probléma · Választás · Indoklás**, hogy a „miért" a diff
újraolvasása nélkül is visszafejthető legyen. A kontextus, az upstream
pin, a `MIGRATION.patch` olvasása és a `research/` artifact-térkép a
[Mechanika](migration-mechanics.hu.md) oldalon található.

### D4 — Artifact átnevezés (`.skill` → `.zip`)

**Probléma** — A Claude Code `.skill` blobokba csomagolja a skilleket, de
az alatta lévő archívum-formátum sima ZIP. A Hermes nem ismeri a `.skill`
kiterjesztést, és a skilleket közvetlenül `.zip`-ként csomagolja.

**Választás** — Minden `.skill` hivatkozás átnevezése `.zip`-re a `SKILL.md`-ben és a `scripts/package_skill.py`-ban. A kimeneti fájlnév `{skill_name}.zip`; a lemezen lévő archívum-formátum nem változik.

**Indoklás** — A Claude-Code-specifikus kiterjesztés elhagyása
megszünteti a host-specifikus fork-kockázatot, és az artifactot
hordozhatóvá teszi bármely ZIP-olvasó számára. A csomagolási logika
(`zipfile.ZipFile(...)` `ZIP_DEFLATED` mellett) változatlan.

### D5 / D11 — `compatibility` frontmatter

**Probléma** — A downstream hosztoknak tudniuk kell, hogy egy skill
támogatja-e az adott runtime-ot, anélkül, hogy forkolniuk kellene a
skillt vagy el kellene olvasniuk a prózáját.

**Választás** — Egy top-level `compatibility` mező hozzáadása a `SKILL.md` frontmatteréhez, amely deklarálja a támogatott runtime-okat. Dual-kompatibilis esetben ez a mező a kanonikus jelzés — előnyben részesítve a `claude_compatible`-stílusú sidecar flagekkel szemben.

**Indoklás** — Egyetlen deklaratív mező greppelhető, géppel
ellenőrizhető, és túléli a runtime-frissítéseket. A jelenlegi érték:
`Compatible with Hermes Agent SDK and Claude Code`.

### D15 — Parancs-csere (`claude -p` → `hermes chat -q`)

**Probléma** — A `claude -p` a Claude-Code CLI felszíne; a Hermesnek
saját egyenértékű CLI felszíne van, amelyet az eval harness-nek kell
használnia.

**Választás** — Minden `claude -p <query> --output-format stream-json`
hívás cseréje `hermes chat -q <query> --output-format json`-ra. A
`--model` argumentum szemantikája megmarad
(`if model: cmd.extend(["--model", model])`, `scripts/run_eval.py:41-42`).

**Indoklás** — A `hermes chat -q` megőrzi ugyanazt a prompt-in /
stdout-out szerződést és a `--model` argumentum szemantikát, így a csere
mechanikus, és az eval harness logikája ép marad. A kimeneti formátum
NDJSON-ről JSON-re vált, mert a ShareGPT JSONL session export (D22)
veszi át a streaming parser helyét.

### D16 — `hermes_subprocess_env()` helper

**Probléma** — A `claude -p` megköveteli a `CLAUDECODE` eltávolítását,
mielőtt nested CLI sessiont indítanánk (interaktív terminál-konfliktus
ellen véd). A Hermes-ben nincs ilyen őr, és a létező
`{k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` minta
széttöredezett a scriptek között.

**Választás** — Bevezetjük a
`scripts/_subprocess.py:hermes_subprocess_env(extra_vars_to_strip=None)`
segédet, amely egyetlen helyen építi fel a subprocess env-et.
Alapértelmezetten **minden változót megőriz** — beleértve a
`CLAUDECODE`-ot is. Nested izolációhoz használj `hermes -p <profile>`-t
vagy `HERMES_HOME` felülírást, ne env-strippelést.

**Indoklás** — A `CLAUDECODE` strippelése a Hermes számára
kategóriahiba: a Hermes nem olvassa, és a csendes strippelés config-bugokat
rejt el. Egy elnevezett helper a nested-Hermes hívóknak is nyilvánvaló
menekülőutat ad (`extra_vars_to_strip=...`).

### D17 — `.claude/` project-root walker eldobása

> Megjegyzés: a `.claude/` itt az upstream Claude projekt-gyökerének
> config-fáját jelenti (amit eldobunk), nem a projekt saját
> `.claude/rules/` konfigurációs fájljait.

**Probléma** — A `run_eval.py:find_project_root()` felsétált a `cwd`-ből felfelé, és `.claude/` könyvtárat keresett, hogy command fájlokat stage-eljen oda. Hermesben a skill útvonala a deployment egysége; nincs `.claude/commands/` stage-terület, amit felfedezni kellene.

**Választás** — A `find_project_root()` törlendő. A project root inline származtatható `skill_path.parent`-ként mind a `run_eval.py`-ban, mind a `run_loop.py`-ban. A `project_commands_dir = Path(project_root) / ".claude" / "commands"` ág teljesen törlendő.

**Indoklás** — A `skill_path.parent` mindig helyes (az eval a skill saját könyvtárából fut), eltávolít egy törékeny fájlrendszer-bejárást, és kiküszöböli azt a race-condition osztályt, ahol két párhuzamos eval-run egymás stage-elt command fájljait tiporja szét.

### D18 — Claude.ai + Cowork szekciók törlése

**Probléma** — Az upstream `SKILL.md` két nagy szekciót tartalmaz
(`## Claude.ai-specific instructions`, `## Cowork-Specific Instructions`),
amelyek az adott hosztok toolszetjéhez és UI-jához kötött munkafolyamatokat
írnak le. Hermesben ezek zajt jelentenek, és olyan mechanikákra
hivatkoznak, amelyek itt nem léteznek (pl. Claude.ai no-subagents
rendszere, Cowork statikus-HTML eval viewer).

**Választás** — Mindkét szekció törlése. A megmaradt
`claude-with-access-to-the-skill` említések átírása
`hermes-with-access-to-the-skill`-re.

**Indoklás** — A törölt tartalom hoszt-specifikus operatív útmutató,
amelyre a Hermes skill-creator munkafolyamatnak nincs szüksége. A
megmaradt említések átírása a prózát ön-konzisztensen tartja.

### D20 — Leaf-agent YAML frontmatter wrapper

**Probléma** — A Hermes a `delegate_task`-on keresztül diszpécseli az
agenteket, strukturált szerződéssel (`goal`, `context`, `toolsets`,
`role`). A Claude Code agentek csupasz Markdown fájlok, H1 fejléccel.

**Választás** — Minden leaf-agent Markdown fájlt YAML frontmatterbe csomagolunk, amely deklarálja a `name`, `description`, `goal`, `toolsets`, `role: leaf` mezőket. Érintett fájlok: `agents/analyzer.md`, `agents/comparator.md`, `agents/grader.md`.

**Indoklás** — A strukturált frontmatter a fájl szintjén teszi
explicitré a diszpécselési szerződést, és a `delegate_task`-ot a próza
parsing helyett metaadatok alapján tudja irányítani. Az eredeti H1
fejléc megmarad az agent testében, így a grep-and-read munkafolyamatok
továbbra is működnek.

### D21 / D22 — ShareGPT JSONL session export

**Probléma** — Az upstream eval harness egy 130 soros NDJSON streamet
parsol a `claude -p --include-partial-messages` kimenetéből, diszpécselve
`stream_event`, `content_block_start`, `content_block_delta`,
`content_block_stop`, `message_stop`, `assistant`, `result` eseményekre,
és `input_json_delta`-t akkumulálva, hogy egy `Skill` vagy `Read`
tool_use-t detektáljon, mielőtt az assistant üzenet megérkezik. Ez
törékeny, Claude-stream-specifikus, és jelentős komplexitást ad hozzá.

**Választás** — Az NDJSON parser cseréje két subprocess hívásra:

1. `hermes chat -q <query> --output-format json` (visszaadja a session
   id-t).
2. `hermes sessions export --session-id <sid> <tmp.jsonl>`
   (ShareGPT-formátumú JSONL transcript-et ír).

A JSONL-t soronként iteráljuk; minden assistant turn-nél olyan tool_use
blokkot keresünk, amelynek `arguments.skill` mezője megegyezik a jelölt
skill nevével (a tisztított `skill_name-eval-<id>` formában).

**Indoklás** — A session export egyetlen forrás, amelyet a Hermes úgyis
előállít; a JSONL iterálása ~70 sor triviális Python a 130 sor stateful
stream-parsing helyett. A költség az, hogy a trigger-detekció most **a
chat befejezése után** történik, nem menet közben — elfogadható, mert az
eval átbocsátóképessége a szűk keresztmetszet, nem a tail latency.

### D23 — Eval-run ID átnevezés (`with_skill|without_skill` → `skill_active|baseline`)

**Probléma** — Az upstream viewer, sémák, aggregate script és a
`SKILL.md` prózája mind a `with_skill` / `without_skill` (a `new_skill`
/ `old_skill` aliasokkal az iterációs runokhoz) kulcsokra épülnek. A
nevek Claude-Code elnevezést kódolnak, és nem élik túl a Hermes
iterációs folyamait.

**Választás** — Átnevezés a teljes skill felszínen:

| Régi | Új |
|---|---|
| `with_skill` | `skill_active` |
| `without_skill` | `baseline` |
| `new_skill` | `skill_iter_n` |
| `old_skill` | `skill_iter_prev` |

Érintett helyek: `eval-viewer/viewer.html:716` regex, `references/schemas.md:239`, `scripts/aggregate_benchmark.py:7`, `SKILL.md:181` útvonal-példák, valamint `agents/analyzer.md:230`.

**Indoklás** — Az új nevek azt írják le, amit a run **jelent** (aktív skill vs baseline; n-edik iteráció vs előző), nem pedig azt, hogy melyik hoszt állította elő őket. A viewer szemantikailag helyes marad a Hermes iterációs runok során.

### D24 — `delegate_task` leaf pattern

**Probléma** — A Hermes a `delegate_task`-on keresztül diszpécseli a
leaf agenteket, strukturált szignatúrával. A leaf agenteknek explicit
invokációs szerződésre van szükségük, hogy a diszpécser tudja, milyen
goal-t, context-et, toolsetet és iterációs korlátot alkalmazzon.

**Választás** — A kanonikus leaf invokáció:

```
delegate_task(
    goal="<one-sentence goal>",
    context="<comma-separated bound variable names>",
    toolsets=["<toolset-1>", "<toolset-2>"],
    role="leaf",
    max_iterations=N,
)
```

**Indoklás** — Egyetlen, elnevezett szignatúra auditálhatóvá teszi a
leaf diszpécselést. A `max_iterations=N` korlátozza a kontrollálatlan
ciklusokat; a `toolsets=[...]` a minimális szükséges toolsetre szűkíti
az agentet.

## Lásd még

- [Mechanika és dossier](migration-mechanics.hu.md) — kontextus, upstream
  pin, a `MIGRATION.patch` olvasása és a `research/` artifact-térkép.
- 📖 [Skill-creator](skill-creator.hu.md) — a migrált skill áttekintése.
- 🛠️ [Patch-ek](patches.hu.md) — a cap-felemelés + Task E site patchek,
  amelyek magára a Hermes checkoutra kerülnek alkalmazásra.
- [Forrás migrációs dossier](../skills/migration-claude-skill-creator/MIGRATION.md)
  — a generált per-binding tábla és döntési napló.