# A skill-creator skill

> [English](skill-creator.md) · [Magyar verzió](skill-creator.hu.md)
> [Vissza a README-hez](../README.hu.md)

## Mi ez?

A `skill-creator` az Anthropic `claude-plugins-official` skill-creator-jának
Hermes-re portolt változata, Claude Code-ról átültetve. A `skills/skill-creator/`
mappában található, és a #2 telepítő script **flat módon** (önállóan) telepíti
a felhasználó agent runtime-jába — **nem** része a plugin csomagnak.

A skill végigvezeti az agentet a teljes skill-szerzői cikluson: szándék
rögzítése, felhasználó kikérdezése, `SKILL.md` piszkozat, teszt promptok
futtatása, kiértékelés grader-ekkel és benchmarkokkal, valamint a description
iterálása a jobb triggerelés érdekében.

> Forrás: `skills/skill-creator/SKILL.md` (447 sor), a frontmatter ezt deklarálja:
> `compatibility: Compatible with Hermes Agent SDK and Claude Code`.

## Miért kell?

A Hermes felhasználók a skill frontmatter `description` mezőjének 60 karakteres
korlátjába ütköznek, és nincs beépített mód új skill-ek author-olására,
validálására vagy benchmarkolására. `skill-creator` nélkül a description
iteráció manuális tippelés — a skill pedig csendben alultriggerelhet. Ez a
skill a teljes eval harness-t szállítja (`run_eval.py`,
`aggregate_benchmark.py`, `improve_description.py`, `quick_validate.py`,
`package_skill.py`), hogy a szerzők mérni tudják: egy-egy változtatás
ténylegesen javít-e.

## Mit módosítottunk (magas szinten)

A port megtartja az upstream skill-creator munkafolyamatot; csak a plumbing
változik. A D4–D24 döntési indoklást lásd: [`migration.hu.md`](migration.hu.md).

- **Frontmatter** — hozzáadva a `compatibility: Compatible with Hermes Agent SDK and Claude Code`.
- **Parancs-csere** — a `claude -p` mindenhol `hermes chat -q`-ra cserélve (`scripts/run_eval.py:38`, `scripts/improve_description.py:27`).
- **Artifact átnevezés** — a csomagolt skill fájlok mostantól `.zip` (a `zipfile.ZipFile`-on keresztül, `scripts/package_skill.py:91`), nem a Claude-féle `.skill` blob.
- **Trigger detekció** — a 130 soros NDJSON parser lecserélve a `hermes sessions export --session-id <sid>` ShareGPT-formátumú JSONL-jére (`scripts/run_eval.py:32–102`).
- **Új helper** — a `scripts/_subprocess.py:hermes_subprocess_env(extra_vars_to_strip=None)` egy szanitized env dict-et ad vissza Hermes alfolyamatok indításához. **Nem** strip-peli automatikusan a `CLAUDECODE` változót (a Hermes-ben nincs Anthropic-specifikus nesting guard; beágyazott izolációhoz használj `hermes -p <profile>`-t vagy `HERMES_HOME`-ot).
- **Walker elhagyás** — a Claude gyökér-bejáró, ami rekurzívan rótta a `.claude/`-t, törölve; a csomagolás `skill_path.parent`-et használ a testvérek megtalálásához (`scripts/package_skill.py:32–33`).
- **Surface trim** — a Claude.ai és Cowork szekciók törölve az upstream törzsszövegből.
- **Leaf agentek YAML-ben** — az `agents/analyzer.md`, `agents/comparator.md`, `agents/grader.md` mostantól YAML frontmatter-be csomagolva (`name`, `description`, `goal`, `toolsets`, `role: leaf`), és a `delegate_task(goal=..., context=..., toolsets=[...], role="leaf", max_iterations=N)` hívást használják.
- **Eval-run azonosítók** — a `with_skill|without_skill` átnevezve `skill_active|baseline`-ra (`scripts/aggregate_benchmark.py:7,20–33,214–215`).

## Fájl-struktúra

```
skills/skill-creator/
├── SKILL.md                       # top-level prompt (447 lines)
├── LICENSE.txt                    # Anthropic licenc (201 sor)
├── agents/
│   ├── analyzer.md                # post-hoc blind-összehasonlító analyzer (296 sor)
│   ├── comparator.md              # blind A/B összehasonlító (224 sor)
│   └── grader.md                  # assertion-alapú grader (245 sor)
├── eval-viewer/
│   ├── generate_review.py         # eval review generátor (471 sor)
│   └── viewer.html                # önálló web viewer (1325 sor)
├── references/
│   └── schemas.md                 # ShareGPT / session sémák (430 sor)
├── assets/
│   └── eval_review.html           # eval review sablon asset
└── scripts/
    ├── _subprocess.py             # hermes_subprocess_env helper (38 sor)
    ├── aggregate_benchmark.py     # benchmark variancia + delta (401 sor)
    ├── generate_report.py         # markdown riport író (326 sor)
    ├── improve_description.py     # leírás-optimalizáló hermes chat-en át (245 sor)
    ├── package_skill.py           # skill → .zip csomagoló (136 sor)
    ├── quick_validate.py          # frontmatter + struktúra validátor (102 sor)
    ├── run_eval.py                # eval harness, hermes sessions export-ot olvas (260 sor)
    ├── run_loop.py                # több iterációs eval driver (329 sor)
    └── utils.py                   # parse_skill_md + megosztott helper-ek (47 sor)
```

## Használat

Egy piszkozat skill validálása, majd becsomagolása terjesztéshez. A csomagoló
helper visszaadja az elkészült `.zip` abszolút elérési útját.

```bash
# 1. Validate frontmatter and folder layout
uv run python skills/skill-creator/scripts/quick_validate.py skills/my-skill

# 2. Skill becsomagolása terjeszthető .zip-be
uv run python skills/skill-creator/scripts/package_skill.py \
    skills/my-skill ./dist

# 3. (Opcionális) Eval harness futtatása egy teszt prompt-készleten
uv run python skills/skill-creator/scripts/run_eval.py \
    --skill skills/my-skill \
    --eval-set evals/my-skill/evals.json
```

Minden script a skill `SKILL.md`-jét a `parse_skill_md`-n keresztül olvassa
(`scripts/utils.py`), és tiszteletben tartja a `skill-creator` konvencióit:
`compatibility`, `description`, mappa-elrendezés.

## Eval ciklus

### Az eval ciklus dióhéjban

1. `quick_validate.py` — kapu bármely eval futás előtt; elutasítja a hibás
   frontmatter-t vagy a hiányzó kötelező mappákat.
2. `run_eval.py` — prompt-onként indít egy `hermes chat -q` folyamatot,
   rögzíti a sessiont a `hermes sessions export --session-id <sid>`-n át,
   majd kiértékeli az eredményt.
3. `aggregate_benchmark.py` — a futásonkénti JSON-t összehajtogatja
   `skill_active` vs `baseline` rollupokba (átlagos átmeneti arány, idő,
   tokenek), és megadja a varianciát, hogy jelet tudj megkülönböztetni a
   zajtól.
4. `generate_report.py` — emberi olvasásra szánt markdown riportot készít
   az aggregált JSON-ból.
5. `improve_description.py` — amikor a description alultriggerel, ez a script
   úgy javasol átírást, hogy megkéri a Hermest: hasonlítsa össze a jelenlegi
   description-t az eval transcript-ekkel.

Az eval webes UI (`eval-viewer/viewer.html` + `eval-viewer/generate_review.py`)
úgy nyílik meg, ahogy a szülő `SKILL.md` munkafolyamat elindítja — az ember
így kvalitatívan is tudja értékelni a futásokat.

### Leaf agentek

A három leaf agentet (`agents/analyzer.md`, `agents/comparator.md`,
`agents/grader.md`) a `delegate_task` hívással, `role: leaf` paraméterrel
indítjuk. Parancssorból közvetlenül nem hívhatók — az eval/iterációs
ciklusban vesznek részt, amit a szülő `SKILL.md` vezényel.

## Lásd még

- [Patch-ek](patches.hu.md) — hogyan oldja fel a cap-emelés a 60 karakternél hosszabb skill-leírásokat.
- [Forrás skill](../skills/skill-creator/SKILL.md) — a prompt, amit a modell ténylegesen olvas futásidőben.
- A D4–D24 döntési indoklás az upstream migrációs doszsziéban található (nem ebben a worktree-ben).