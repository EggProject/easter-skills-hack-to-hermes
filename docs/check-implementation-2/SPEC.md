# Hermes Skills — Audit Spec Extract

Forrás: GitHub issue #33 (easter-skills-hack-to-hermes), az eredeti fejlesztési brief alapján.

Ez a fájl a FIND / VALIDATE / JUSTIFY audit agenteknek szól. **Csak olvasd, ne módosítsd.**

---

## §0. A Koordinátor Szerepe

- Autonóm fejlesztőcsapat vezető koordinátora.
- Feladat: munka felbontása, **implementáció delegálása specializált sub-agenteknek**, kimenet integrálása/ellenőrzése.
- **NE maga implementáljon**, ahol a delegálás lehetséges.
- `sequential-thinking` skill használata nem-triviális döntésekhez.
- `omh-deep-interview` skill nem egyértelmű követelményeknél.

---

## §1. Küldetés

Két összefüggő artefaktum:

1. **Hermes plugin**, amely a skill-description beolvasási limitet **60 → 1024 karakterre** emeli, az Anthropic hosszú skill-leírásokra vonatkozó megközelítését követve.
2. **Az Anthropic hivatalos `skill-creator` skill önálló, Hermes-natív migrációja**, amely **lecseréli** a gyári `openai/skills/skill-creator`-t az összes Hermes profilban.

A kettő összefügg: a migrált `skill-creator` patchelt kódon fut (1024-es limit érvényben).

---

## §2. Háttér

- A Hermes agent-skills alrendszer **minden skill description mezőjét 60 karakterre vágja**, mielőtt az agent kontextusába szúrná.
- A limit 1024 karakterre emelendő (Anthropic-stílus).
- A gyári `openai/skills/skill-creator` gyengébb, mint az Anthropic `skill-creator`-a. Letiltandó a gyári, telepítendő a migrált.

---

## §3. Környezet

| Elem | Útvonal |
|---|---|
| Plugin munkamappa | `/Users/kiscsicska/projects/easter-skills-hack-to-hermes-2` |
| Hermes telepítés (patch célpontja) | `~/.hermes/hermes-agent` |
| Meglévő patch-pont kutatás | `docs/maybe-patch-points.md` |
| Hermes plugin-írási referencia | `https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/build-a-hermes-plugin.md` |

A plugint a hivatalos Hermes plugin-dokumentáció szerint kell implementálni.

---

## §4. KRITIKUS BIZTONSÁGI MEGKÖTÉSEK

1. **SOHA NE futtasd a patch scriptet éles Hermes környezetben.** A patcht a felhasználó futtatja majd személyesen.
2. A patch/profil scriptek tesztekkel igazolandók, nem éles futtatással. **A teszt-lefedettség a helyesség elsődleges garanciája** (lásd §8).
3. **A HITL kapu a §7.4-ben kötelező**: a felhasználó jóváhagyása nélkül ne haladj tovább a tervről a végrehajtásra.

---

## §5. Leszállítandók

### §5.1 Hermes plugin — karakter-limit patch
- Egy Hermes plugin a hivatalos plugin-dokumentáció szerint megépítve.
- A skill-description limitet 60 → 1024-re emelő logikát hordozza.

### §5.2 Patch Script (Script #1)
- Alkalmazza a patcht a Hermes kódbázisra, §6.B logikával.
- **A csapat soha nem futtatja** (§4).

### §5.3 Profilkezelő Script (Script #2)
- Auditálja a Hermes profilokat, lecseréli a gyári `skill-creator`-t a miénk migrált verziójára, §6.C logikával.
- Script #1-től **különálló**.

### §5.4 Migrált `skill-creator` skill
- Az Anthropic hivatalos `skill-creator`-ának Hermes-natív migrációja.
- **Önállónak kell lennie — NEM beágyazva a pluginba.**
- **A neve `skill-creator` kell legyen** (tükrözze a letiltott gyári `openai/skills/skill-creator`-t).

### §5.5 Migrációs feljegyzés
- Szöveges, géppel olvasható migrációs dokumentum (lásd §6.D).
- Lehetővé teszi az újraszinkronizálást, ha az upstream változik.

### §5.6 Tervezési dokumentumok
- Ultra-részletes terv Markdownban.
- **Kemény korlát: fájlonként 500 sor — túllépés esetén több fájlra bontandó.**

### §5.7 Folyamatosan karbantartott Todo lista
- Előre létrehozandó, végig naprakészen tartandó.

---

## §6. Részletes Feladat-lebontás

### §6.A — Kutatás és Felderítés
- `omh-deep-research` használata:
  - (a) hogyan kell Hermes plugint írni
  - (b) hogyan működik a Hermes belül
  - (c) az Anthropic hivatalos `skill-creator`-a
- Pontosan meghatározandó, **hol vágja a `~/.hermes/hermes-agent` a skill description-jét 60 karakterre**.
- Megkeresendő a kapcsolódó GitHub issue.
- Letöltendő az Anthropic hivatalos `skill-creator` skillje (200k+ értékeléssel rendelkező kanonikus).

### §6.B — Patch Script (Script #1) logikája

1. **Idempotencia-őr:** patch-elés előtt állapítsd meg, hogy **már patchelve van-e**. Ha igen, **jelezd és állj le** (nincs változtatás).
2. **Több-jelzéses célzás:** minden patch-helyet **egyszerre a pontos szöveg/minta ÉS a pontos sorszám alapján** azonosíts.
3. **Mindent-vagy-semmit ellenőrző kapu:** először ellenőrző fázis AZ ÖSSZES célhelyen. A patch csak akkor folytatódhat, ha minden hely átmegy.
4. **Sorszám-eltérés kezelése:** ha szöveg egyezik, de sorszám nem, **ne patchelj — jelezd az eltérést**. A `--force` flag **csak a sorszám-ellenőrzést kapcsolja ki**. Szöveg/minta-egyezés `--force` alatt is érvényes.
5. **Opcionális patch-pont kapcsoló (§6.E):** a beépített promptok átirányítása a mi `skill-creator`-unkra — **ebben** a scriptben, **külön, opt-in CLI kapcsoló mögött**, alapból sosem alkalmazva.
6. **`--help` kötelező.**

### §6.C — Profilkezelő Script (Script #2) logikája

1. Vizsgáld meg az **alapértelmezett profilt (a `hermes` parancs)** *és* **az összes többi profilt**.
2. Minden profilban, ahol az `openai/skills/skill-creator` engedélyezve van: **tiltsd le**, és **telepítsd a mi migrált `skill-creator`-unkat**.
3. Ha a mi migrált verziónk **már telepítve van**: **frissítsd** (telepítsd újra a legújabbat).
4. **`--help` kötelező.**

### §6.D — Az Anthropic `skill-creator` migrálása → Hermes

1. **Töltsd le** az Anthropic hivatalos `skill-creator`-át.
2. **Migráld teljes egészében**, hogy átmenjen a `hermes-agent-skill-authoring` skillen.
3. **Ultra-alaposan cseréld le minden Claude-specifikus parancsot a Hermes-megfelelőjére** — egyetlen se maradjon.
4. **Őrizd meg Claude erősségeit** — a *formát* migráld Hermes-re, a *lényeget* tartsd meg.
5. A migrált skill **patchelt kódon működik** (1024-es leírások elérhetők).
6. Nevezd el **`skill-creator`**-nak (lásd §5.4), és tartsd **önállónak** (ne ágyazd be a pluginba).
7. **Migrációs feljegyzés (§5.5)** tartalmazza:
   - Forrás repo és skill azonosító.
   - Pontos commit hash, amelyből a migráció készült.
   - **Minden elvégzett változtatás pontos feljegyzése**, hogy újraszinkronizálható legyen.

### §6.E — Beépített Prompt Patch-pontok

**Cél:** ahol a Hermes automatikusan skilleket hoz létre, ott a skill-létrehozás mindig a mi `skill-creator`-unkon keresztül történjen.

1. Tanulmányozd a Hermes kódbázist + webes kutatás → **saját lista** a jelölt patch-pontokról és pontos módosításokról.
2. **Vesd össze a `docs/maybe-patch-points.md`-vel**, hangold össze.
3. Implementáld **opt-in, nem alapértelmezett kapcsolóként** a **patch scriptben** (Script #1, §6.B.5).

---

## §7. Végrehajtási Workflow

1. **Lebontás és Todo:** részletes lépések + Todo lista (§5.7), folyamatos karbantartás.
2. **Mély kutatás:** `omh-deep-research` minden releváns témában (§6.A).
3. **Tervezés:** megfelelő plan skill + `improve-codebase-architecture` + `tdd`. Ultra-részletes Markdown terv, **max. 500 sor/fájl → bontsd több fájlra**.
4. **HITL kapu:** a felhasználónak jóvá kell hagynia a tervet, mielőtt a végrehajtás elkezdődik.
5. **Végrehajtás:** sub-agentekkel (koordinátor delegál).
6. **Ellenőrzés:** sub-agentekkel.
7. **Hiba-hurok:** kutatási hiányosság → 2. lépés; tervezési hiányosság → 3. lépés; frissítsd a Todo listát.

---

## §8. Fejlesztési Sztenderdek

- **TDD kötelező** (`tdd` skill).
- **100% lefedettség kötelező** — kód-lefedettség ÉS logikai lefedettség (minden branch + minden logikai eset).
- **Worktree + PR workflow kötelező.**
- **Minden feladat után commit.**
- **Delegálj sub-agenteknek és koordinálj.**
- **`--help` kötelező** minden scripthez.
- **Nyelvi szabály:**
  - Kód, skillek, promptok → **angol**.
  - User-facing leírások, console/log üzenetek → **angol + magyar (kétnyelvű)**.
- **Python scriptekhez kötelező:**
  - `uv` virtual env a project mappában
  - `pyproject.toml`
  - `pre-commit` python csomag telepítve és beállítva
  - `ruff` + `black` + `mypy` + `wemake-python-styleguide` legszigorúbb standardokkal, pre-commit-ba bekötve

---

## §9. Skill-referencia

| Skill | Használat |
|---|---|
| `omh-deep-research` | Webes kutatás (§6.A, §7.2) |
| `improve-codebase-architecture` | Architektúra és tervezés (§7.3) |
| `tdd` | Teljes implementáció során |
| `hermes-agent-skill-authoring` | Migrált `skill-creator` validálása (§6.D.2) |
| `sequential-thinking` | Nem-triviális gondolkodási lépések |
| `omh-deep-interview` | Döntések kinyerése nem egyértelmű követelményeknél |
| megfelelő plan skill | Darabolt Markdown terv (§7.3) |

---

## §10. Elfogadási Kritériumok

- [ ] Plugin a hivatalos Hermes plugin-dokumentáció szerint megépítve, munkamappában elhelyezve.
- [ ] A pontos 60 karakteres vágási hely(ek) azonosítva, kapcsolódó GitHub issue hivatkozással.
- [ ] **Script #1** 1024-re emeli a limitet: idempotencia-őr, mindent-átfogó ellenőrző kapu, szöveg+sorszám célzás, `--force` (csak sorszám), opt-in beépített-prompt kapcsoló, `--help`.
- [ ] **Script #2** auditálja az alapértelmezett + az összes profilt, letiltja `openai/skills/skill-creator`-t, telepíti a migráltat, frissít, ha már jelen van, van `--help`-je.
- [ ] Migrált **`skill-creator`** önálló, átmegy `hermes-agent-skill-authoring`-on, minden Claude-specifikus parancs cserélve, megőrzi Claude erősségeit.
- [ ] AI-olvasható **migrációs feljegyzés** megvan: forrás repo, commit hash, pontos changelog.
- [ ] **Patch-pontok** önállóan elkészítve és összehangolva a `docs/maybe-patch-points.md`-vel.
- [ ] **100% kód- + logikai lefedettség** TDD-vel; egyetlen script sem fut élesben.
- [ ] Worktree + PR workflow betartva; commit minden feladat után; terv ≤500 sor/fájl; kétnyelvű leírások/console; angol kód/skillek/promptok.
- [ ] A terv jóváhagyva a **HITL kapunál** a végrehajtás előtt (§7.4).

---

## Audit-specifikus kiegészítések (issue #33-ból)

- **NE módosíts kódot** — csak riportot készíts.
- Az eredmény egy **interaktív HTML report** a `docs/check-implementation-2/` mappában.
- Minden eltérést osztályozz: **bug / justified_change / feature_change**, indoklással.
- 3-fázisú agent pattern: egyik keres → másik validál → harmadik indokol (kontextus-torzulás ellen).
- **A specifikáció minden pontját külön agent vizsgálja** (NEM egy nagy agent).
- Ultra-részletes Todo lista, hogy ne vesszen el semmi.
