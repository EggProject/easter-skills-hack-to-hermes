# Patch site-ok

> 📖 [English](patches.md) · [Magyar verzió](patches.hu.md)
> ↩️ [Vissza a README-hez](../README.hu.md)

Utoljára ellenőrizve: 2026-06-25, a kanonikus site-tábla alapján: `src/easter_hermes_sorry_skills/_patcher_sites_table.py`.

Ez a dokumentum a Script #1 patcher által alkalmazott nyolc patch site-ot sorolja fel egy felhasználó tulajdonában álló Hermes checkout-on. Azért létezik, hogy egy review-er auditálhassa *mit* írunk és *hová* — anélkül, hogy a targeting szabályokat az orchestratorból kellene visszafejtenie.

## Áttekintés

A patcher (`src/easter_hermes_sorry_skills/_patcher.py`) egy egyszeri, advisory jellegű mutator egy downstream Hermes forrásfán. Nem módosítja magát a skill-creator skill-t; kizárólag a felhasználó Hermes checkout-ját szerkeszti, három fájlt: `agent/skill_utils.py`, `agent/prompt_builder.py`, `agent/background_review.py`.

Működési modell:

- **Egyszeri tanács:** egyetlen `--apply` lefuttatja a teljes site-táblát; semmi nem fut Hermes induláskor vagy meghíváskor.
- **Mindent vagy semmit:** ha bármely site validációja elbukik, a patcher kiírja a `.patch.rejected` fájlt és nullától különböző exit kóddal kilép, a célfájlon nulla bájtot sem módosítva.
- **Idempotens:** újrafuttatva egy már patchelt checkout ellen a futás no-op (minden site rendelkezik `expected_replacement` ellenőrzéssel).
- **Többszignálos targeting:** minden site-ot egyszerre azonosít egy 8+ karakteres fizikai sor anchor és egy 1-alapú sorszám. Mindkettőnek egyeznie kell — a részleges egyezés drift, nem patch.

A patcher mindig a teljes site-táblát alkalmazza: `S1.cap` (vagy a fallbackje) plusz mind a hat Task E site (`E0`, `E1`, `E2`, `E4b`, `E4`, `E5`). Nincs opt-out flag.

## Cap felemelés

Az `S1` pár két fizikai sort cserél ki az `agent/skill_utils.py` fájlban, amelyek egy 60-karakteres description cap-et hard-code-olnak. A 60 karakternél hosszabb skill leírások csendben truncálódnak futásidőben, ami a konzultációs szabályt és a gazdagabb skill leírásokat használhatatlanná teszi. A csere a cap-et egy olyan konstanson keresztül vezeti, amelyet a modul többi része is olvashat.

### S1.cap — a 60-karakteres cap felemelése

- **Site ID:** `S1.cap`
- **Cél:** `agent/skill_utils.py` L688–L689
- **Művelet:** két soros atomi csere (`kind="cap"`); mindkét anchor egyezése szükséges ahhoz, hogy a site patcheltnek számítson
- **Anchor A (L688):** `    if len(desc) > 60:`
- **Anchor B (L689):** `        return desc[:57] + "..."`
- **Csere:**

  ```python
      if len(desc) > MAX_DESCRIPTION_LENGTH:
          return desc[:MAX_DESCRIPTION_LENGTH - 3] + "..."
  ```

- **Miért:** a `60` literál mélyen a truncációs ágban lakik; a felemelése egy elnevezett konstanson keresztül lehetővé teszi, hogy a `tools.skills_tool` is importálja ugyanazt a cap-et, és a modulok között konzisztens maradjon.

### S1.cap_fallback — circular-import fallback

- **Site ID:** `S1.cap_fallback`
- **Cél:** ugyanaz a fájl, ugyanazok az anchorok (L688–L689)
- **Művelet:** két soros atomi csere, de a csere egy lokális `_MAX_DESCRIPTION_LENGTH = 1024` konstanst is beilleszt a sorok elé
- **Trigger:** a pre-flight circular-import detektor (`_check_circular_import` a `_patcher_internals.py:74-89`-ben) bejárja az `agent/skill_utils.py` meglévő `from tools.skills_tool import …` láncát. Ha ciklust talál, az orchestrator `S1.cap` helyett `S1.cap_fallback`-et választ, így a patch a cross-module `MAX_DESCRIPTION_LENGTH` importálása nélkül is lefuthat
- **Miért:** a cap-emelés akkor is működik, amikor az import-gráf egyébként visszafordulna az általunk szerkesztendő fájlba

## Prompt-injection site-ok

A négy `E*` site a `SKILL_CREATOR_CONSULT_RULE` konstanst (vagy egy hivatkozást rá) injektálja a Hermes prompt-building útvonalába. A konstans a szabály szövegének egyetlen forrása; az `E0` definiálja egyszer, és minden más site a névre hivatkozik.

A site-okat **csökkenő sorszám-sorrendben** alkalmazzuk, hogy a fájl-teteji beszúrások (`E0`, `E4b`) fussanak utoljára, és ne tolják el az orchestrator által már validált magasabb-sorszámú anchorokat.

### E0.consult_rule_def

- **Site ID:** `E0.consult_rule_def`
- **Cél:** `agent/prompt_builder.py` L1
- **Művelet:** modul-szintű konstans hozzáfűzése közvetlenül az L1 docstring anchor után (`kind="append"`)
- **Anchor szövege:** az `agent/prompt_builder.py` L1 docstringje
- **Beszúrás (verbatim, a docstring után):**

  ```python

  SKILL_CREATOR_CONSULT_RULE = (
      "When creating or editing a skill — use skill-creator. Persist with skill_manage. Small targeted fixes (one-file, < ~20 lines, no schema change) stay patch-first."
  )

  ```

- **Miért:** a konstanst modul-szinten definiálja ugyanabban a fájlban, ahol használva lesz; az E1 és E2 ezután import nélkül hivatkozhat a névre.

### E1.skills_guidance

- **Site ID:** `E1.skills_guidance`
- **Cél:** `agent/prompt_builder.py` L179
- **Művelet:** egyetlen forrássor hozzáfűzése közvetlenül az anchor után (additív — a környező literálok verbatim maradnak)
- **Anchor szövege:** egy implicit-concat blokk záró sora a skills being maintained-ről
- **Beszúrás (egy sor):**

  ```python
      " " + SKILL_CREATOR_CONSULT_RULE
  ```

- **Miért:** a konzultációs szabályt a skills guidance promptba emeli, hogy a modell lássa, amikor a skill-creator, skill_manage és patch-first útvonalak között választ.

### E2.memory_guidance

- **Site ID:** `E2.memory_guidance`
- **Cél:** `agent/prompt_builder.py` L158
- **Művelet:** egyetlen forrássor hozzáfűzése közvetlenül az anchor után
- **Anchor szövege:** a memory-guidance literál, amely `"necessary later, save it as a skill with the skill tool.\n"`-re végződik
- **Beszúrás (egy sor):**

  ```python
      " " + SKILL_CREATOR_CONSULT_RULE + "\n"
  ```

- **Miért:** ugyanaz a prompt-injection cél, mint az `E1` esetén, de a memory guidance blokkban — lefedi azokat a promptokat, amelyek a skills felület helyett a memory-n keresztül haladnak.

## Background-review site-ok

Az `E4b` / `E4` / `E5` hármas az `agent/background_review.py` fájlt szerkeszti. Az `E4b` hozzáadja a cross-module importot, amely a konstanst elérhetővé teszi; az `E4` és `E5` ezután a két background-review prompt template-be injektálja.

### E4b.consult_rule_import

- **Site ID:** `E4b.consult_rule_import`
- **Cél:** `agent/background_review.py` L1
- **Művelet:** egyetlen fájl-teteji import hozzáfűzése közvetlenül az L1 docstring után
- **Anchor szövege:** az `agent/background_review.py` L1 docstringje
- **Beszúrás (egy sor):**

  ```python
  from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE
  ```

- **Miért:** a konstans az `agent/prompt_builder.py`-ban lakik; ez az import a híd, amely az `E4`-nek és `E5`-nek lehetővé teszi, hogy a nevet egy másik modulban, újradefiniálás nélkül hivatkozza.

### E4.skill_review_prompt_opt4

- **Site ID:** `E4.skill_review_prompt_opt4`
- **Cél:** `agent/background_review.py` L105
- **Művelet:** egyetlen forrássor hozzáfűzése a skill-review prompt template belsejében
- **Anchor szövege:** egy implicit-concat blokk záró sora, amely a mai task helytelenségéről szól
- **Beszúrás (egy sor):**

  ```python
      SKILL_CREATOR_CONSULT_RULE + "\n\n"
  ```

- **Miért:** a `"\n\n"` Python string literál (load-bearing — a forrásnak a literális `\n\n` sztringgel kell végződnie, nem két tényleges újsor karakterrel); egy üres-soros elválasztóval fűzi a szabályt a skill-review prompt végére.

### E5.combined_review_prompt_opt4

- **Site ID:** `E5.combined_review_prompt_opt4`
- **Cél:** `agent/background_review.py` L194
- **Művelet:** egyetlen forrássor hozzáfűzése a combined-review prompt template belsejében
- **Anchor szövege:** egy implicit-concat blokk záró sora, amely az (1)/(2)/(3) opciókra hivatkozik vissza
- **Beszúrás (egy sor):**

  ```python
      SKILL_CREATOR_CONSULT_RULE + "\n\n"
  ```

- **Miért:** ugyanaz a prompt-injection cél, mint az `E4` esetén, de a combined-review promptra alkalmazva, amely mind a skill, mind a memory review lefutása után fut.

## Apply mechanika

Az orchestrator (`_patcher.py:124-255`) egy fix pipeline-t követ:

1. **Preflight** — megtagadja a futást, ha a `--target` a `~/.hermes/hermes-agent` útvonalra oldódik fel (az upstream repo), 4-es exit kóddal és kétnyelvű diagnosztikával. Lásd `_patcher.py:1-45` a refusal-rule contractért.
2. **Circular-import ellenőrzés** — a `file_has_circular_import` (a `_patcher_imports.py`-ban újraexportálva, eredetileg `_patcher_helpers`-ben) bejárja az `agent/skill_utils.py` meglévő import-gráfját. Egy észlelt ciklus `S1.cap`-et `S1.cap_fallback`-re cseréli (a patch tovább fut, a cross-module import elkerülve). Lásd `_patcher_internals.py:74-89`.
3. **Site-szintű validáció** — minden site egyezését a fájl nyers bájtjain futtatjuk, a többszignálos anchor (8+ kar + 1-alapú sor) alapján. Az eltérés `LINE_DRIFT` vagy `TEXT_DRIFT` (a `_patcher_consts.py:26-27`-ben definiált konstansok).
4. **Atomi írás** — a sikeres site-kat a `<file>.patch.tmp` + `os.replace` mintán keresztül írjuk (`_patcher_apply_atomic.py:47-71`). POSIX-atomi ugyanazon a fájlrendszeren; a mode bitek `os.chmod` segítségével megmaradnak. A temp fájl bármilyen kivétel esetén törlődik, így az eredeti érintetlen marad.
5. **State sidecar** — a `.patch.state.json` (a `_patcher_apply_state.py:35-52`-ben) rögzíti, hogy mely site-ok `matched`, `patched` vagy `drifted` állapotúak. A következő futás ebből olvassa ki a már alkalmazott site-okat.
6. **Rejected sidecar** — a `.patch.rejected` (a `_patcher_apply.py:64-102`-ban) a kétnyelvű, géppel olvasható hibarekord, amelyet drift esetén írunk ki. Sikeres futáskor soha nem jön létre.
7. **Audit log** — a `~/.hermes/patch-audit.log` (a `_patcher_apply.py:42`-ben definiált `AUDIT_LOG_NAME`) csak sikeres `--force` futáskor kap egy új sort (időbélyeg + combined diff sha256). A normál `--apply` futások nem írnak audit sort.
8. **Cache purge** — sikeres apply után a `_patcher_pipeline_purge.py:48-59` törli a `~/.hermes/.skills_prompt_snapshot.json` fájlt. A snapshot csak a `SKILL.md` / `DESCRIPTION.md` mtime-okat követi; nem veszi észre, ha a `prompt_builder.py`-t a patcher módosította. A purge hideg rebuildet kényszerít a következő Hermes futáskor.

### Exit kódok

A `_patcher_consts.py:13-18`-ból:

| Kód | Jelentés             |
|---:|----------------------|
|  0 | OK                   |
|  1 | Validáció            |
|  2 | Drift                |
|  3 | Jogosultság          |
|  4 | I/O                  |
|  5 | User-abort           |

## Rollback

A patcher egyszeri, de minden sikeres apply kiír egy tartós state sidecart, így a rollback mechanikus.

1. **State fájl átnézése.** A `cat .patch.state.json` a patchelt target mellett listázza az egyes site-okat és az aktuális `state` értéküket (`matched` / `patched` / `drifted`).
2. **Audit log átnézése.** A `~/.hermes/patch-audit.log` minden sikeres `--force` futást rögzít időbélyeggel és diff hash-sel. A `git log` kombinálásával megtalálható az a commit, amely bevezette a patchelt állapotot.
3. **Visszaállítás `git checkout`-tal.** Minden patchelt fájl tracked a felhasználó Hermes checkout-jában. A `git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py` a kanonikus revert; a patcher anchorjai upstream szövegre vannak hangolva, így a revert nem ütközik egy jövőbeli re-apply-jel.
4. **Re-apply.** Egy tiszta checkout újra patchelhető a patcher újrafuttatásával; a visszaállított kísérlet state sidecarja a következő futáskor felülíródik.

**Ne** szerkesszük kézzel a `.patch.state.json`-t, hogy "kikényszerítsünk" egy re-apply-t. A state fájl rekord, nem kapcsoló; a `--force` apply-időben újrapróbálja a drifted site-okat, és egy friss drift továbbra is 2-es exit kóddal kilép, hacsak az operátor manuálisan nem oldja fel a mögöttes driftet (lásd `_patcher.py:206-210`).
