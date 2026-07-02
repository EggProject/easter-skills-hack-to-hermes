# WOW Skills Implementation TODO

## Cel

Megvalositani a `docs/wow-skills-load-plan.md` tervet ugy, hogy a Hermes plugin
`pre_llm_call` hookon keresztul adaptiv, alacsony zajszintu skill shortlistet
adjon az LLM aktualis turnjehez.

A megvalositas elso kore:

- nem patcheli a Hermes core-t;
- nem nyul a Hermes skill frontmatter/parser logikahoz;
- nem jarja be sajat maga a profile-okat vagy skill konyvtarakat;
- a skill metadata forrasa a Hermes `tools.skills_tool.skills_list()` API;
- defaultban nem always-on;
- 100% unit coverage + lint + static safety + release artifact frissites.

## Fuggosegek es invariansok

- Hermes celverzio: `30e947e0a`, csak `/tmp/hermes-30e947e0a` alatt vizsgalva.
- `~/.hermes` fejlesztes kozben tovabbra is tiltott.
- Hermes patcher parancs csak `--dry-run` modban futhat.
- Python toolchain: `uv`.
- `dist/` implementacios PR-ben mindig az utolso verziot tartalmazza.
- A plugin nem hivhat `ctx.register_skill`.
- A plugin nem vegez `setattr`-t Hermes modulokon.
- A plugin fail-open: hook hiba eseten ne torje el a turnt, csak ne injektaljon.

## Fajlcsoportok

### Runtime plugin

- `src/easter_hermes_sorry_skills/_register.py`
- `src/easter_hermes_sorry_skills/plugin.yaml`
- uj modul: `src/easter_hermes_sorry_skills/_skill_hook_config.py`
- uj modul: `src/easter_hermes_sorry_skills/_skill_hook_api.py`
- uj modul: `src/easter_hermes_sorry_skills/_skill_hook_matcher.py`
- uj modul: `src/easter_hermes_sorry_skills/_skill_hook_render.py`
- uj modul: `src/easter_hermes_sorry_skills/_skill_hook.py`

### Tesztek

- `tests/test_register.py`
- uj teszt: `tests/test_skill_hook_config.py`
- uj teszt: `tests/test_skill_hook_api.py`
- uj teszt: `tests/test_skill_hook_matcher.py`
- uj teszt: `tests/test_skill_hook_render.py`
- uj teszt: `tests/test_skill_hook.py`
- uj stub: `tests/stubs/tools/skills_tool.pyi`

### Dokumentacio es release

- `docs/wow-skills-load-plan.md`
- `docs/wow-skills-implementation-todo.md`
- `docs/usage.md`
- `docs/usage.hu.md`
- `dist/easter-hermes-sorry-skills.pyz`
- `dist/easter-hermes-sorry-skills-v0.1.0.tar.gz`

## Phase 0 - contract spike es baseline

- [ ] `main` frissitese `git pull --ff-only`.
- [ ] Feature branch nyitasa.
- [ ] Ellenorizni: `git status --short --branch` tiszta.
- [ ] Ellenorizni, hogy `/tmp/hermes-30e947e0a` megvan es a commit:
  `30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`.
- [ ] A `/tmp/hermes-30e947e0a/agent/turn_context.py` alapjan bizonyitani a
  `pre_llm_call` input contractot:
  - `user_message`;
  - `conversation_history`;
  - `is_first_turn`;
  - `session_id`;
  - `task_id`;
  - `turn_id`;
  - `model`;
  - `platform`;
  - `sender_id`.
- [ ] A `/tmp/hermes-30e947e0a/hermes_cli/plugins.py` alapjan bizonyitani a
  return contractot:
  - `{"context": "..."}` ephemeral user-message contextet injektal;
  - plain string ugyanennek felel meg;
  - `None` nem injektal.
- [ ] A spike eredmenyet roviden rogziteni a TODO doksi implementacio kozbeni
  frissiteseben es a PR leirasban.
- [ ] Dry-run patcher baseline:
  `uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run --target /tmp/hermes-30e947e0a`.
- [ ] Nem futtatni semmit `--dry-run` nelkul Hermes target ellen.

Sikerfeltetel:

- tiszta feature branch;
- `pre_llm_call` contract bizonyitott a pinned Hermes kodbol;
- dry-run patcher nem ir fajlt;
- nincs `~/.hermes` hozzaferes.

## Phase 1 - config modell

Feladat:

- [ ] Letrehozni `_skill_hook_config.py` modult.
- [ ] Definialni immutable config adatmodellt.
- [ ] Config forrasok:
  1. Hermes `config.yaml`:
     `plugins.entries.easter-hermes-sorry-skills-plugin.skill_hook`;
  2. env override csak loglevelhez:
     `EASTER_HERMES_SORRY_SKILLS_LOG_LEVEL`.
- [ ] Tamogatott `mode` ertekek:
  - `off`
  - `adaptive`
  - `first`
- [ ] Tamogatott `output` ertekek:
  - `shortlist`
  - `names`
  - `index`
- [ ] Default:
  - `enabled=True`
  - `mode=adaptive`
  - `output=shortlist`
  - `top_k=3`
  - `min_score=2`
  - `log_level=INFO`
- [ ] Hibasan megadott config fail-closed legyen adott mezore:
  invalid `mode` -> `adaptive`;
  invalid `output` -> `shortlist`;
  invalid szam -> default.

Tesztek:

- [ ] config defaultok.
- [ ] config.yaml strukturalt dictbol olvasas.
- [ ] invalid mode/output fallback.
- [ ] top_k es min_score normalizalas.
- [ ] env loglevel override.
- [ ] missing `hermes_cli.config` import fail-open defaulttal.

Sikerfeltetel:

- config modul 100% line + branch coverage;
- nincs fajliras;
- nincs `~/.hermes` olvasas tesztben.

## Phase 2 - Hermes skills API adapter

Feladat:

- [ ] Letrehozni `_skill_hook_api.py` API helper modult.
- [ ] Importalni es hivni: `tools.skills_tool.skills_list()`.
- [ ] A JSON string valaszt parse-olni.
- [ ] Csak sikeres, dict alaku, `success=True` es list alaku `skills` valaszt
  elfogadni.
- [ ] A rekordokat normalizalni:
  - `name: str`
  - `description: str`
  - `category: str`
- [ ] Ures, nev nelkuli vagy nem string rekordokat eldobni.
- [ ] API exception vagy hibas JSON eseten ures skill lista.

Tesztek:

- [ ] sikeres `skills_list()` JSON.
- [ ] ures lista.
- [ ] hibas JSON.
- [ ] `success=False`.
- [ ] nem list `skills`.
- [ ] rossz tipusu rekordok.
- [ ] exception fail-open.
- [ ] `tests/stubs/tools/skills_tool.pyi` eleg a mypy strict importhoz.

Sikerfeltetel:

- a plugin skill metadata forrasa bizonyithatoan `skills_list()`;
- nincs sajat filesystem scan;
- API adapter 100% coverage.

## Phase 3 - lexical matcher

Feladat:

- [ ] Letrehozni `_skill_hook_matcher.py` modult.
- [ ] Normalizacio:
  - lowercase;
  - egyszeru punctuation split;
  - stopword lista angol + minimal magyar altalanos szavakkal;
  - token minimum hossz.
- [ ] Pontozas:
  - explicit skill name szerepel: `+5`;
  - description token overlap: `+3` tobb eros tokennel;
  - category/token match: `+2`;
  - elso turn skill-gyanus prompt: `+1`;
  - trivialis/tul rovid prompt: `-3`;
  - csak stopword-szeru match: `-3`.
- [ ] Stabil rendezesi szabaly:
  - magasabb score elore;
  - azonos score eseten skill name abc szerint.
- [ ] `top_k` limit.
- [ ] `min_score` kuszob.
- [ ] Match reason lista debughoz.

Tesztek:

- [ ] explicit name match.
- [ ] description overlap match.
- [ ] category match.
- [ ] trivial prompt skip.
- [ ] stopword-only skip.
- [ ] top_k stabil sorrend.
- [ ] min_score szures.
- [ ] unicode/ekezetes input nem dob hibat.
- [ ] ures user prompt.
- [ ] duplikalt skill nev stabilan kezelve.

Sikerfeltetel:

- determinisztikus matcher;
- nincs kulso dependency;
- 100% coverage.

## Phase 4 - context renderer

Feladat:

- [ ] Letrehozni `_skill_hook_render.py` modult.
- [ ] `output=shortlist`:
  `name + rovid description`.
- [ ] `output=names`:
  csak top-K skill nevek.
- [ ] `output=index`:
  top-K skill nev + teljes Hermes description, debug/teszt celra.
- [ ] Injektalt szoveg legyen nem kikenyszerito:
  `Use skill_view(name) only if the current task actually matches.`
- [ ] Ne legyen teljes skill body.
- [ ] Ne legyen teljes enabled skill index.
- [ ] Output hossza legyen bounded:
  - max sorok: top_k + header/footer;
  - description normalizalt es levagott.

Tesztek:

- [ ] shortlist format.
- [ ] names format.
- [ ] index format.
- [ ] ures match lista -> `None` vagy ures context.
- [ ] description truncation.
- [ ] stable order.
- [ ] nincs `SKILL.md` body jellegu tartalom.

Sikerfeltetel:

- prompt context rovid, stabil, nem always-on;
- 100% coverage.

## Phase 5 - pre_llm_call hook bekotese

Feladat:

- [ ] Letrehozni `_skill_hook.py` orchestration modult.
- [ ] `_register.py` bovites:
  - megtartani az `on_session_start` advisory hookot;
  - regisztralni `pre_llm_call` hookot;
  - nem regisztralni skillt.
- [ ] `plugin.yaml` bovites:
  `provides_hooks` tartalmazza:
  - `on_session_start`
  - `pre_llm_call`
- [ ] Hook callback input:
  - `user_message`;
  - `is_first_turn`;
  - `session_id` csak log kontextusra, tartalomba nem kell.
- [ ] `mode=off`: nincs context.
- [ ] `mode=first`: csak `is_first_turn=True` eseten futtatja ugyanazt a
  matcher + renderer pipeline-t; match nelkul nem injektal.
- [ ] `mode=adaptive`: csak matcher talalat eseten.
- [ ] Return shape:
  - nincs injection: `None`;
  - van injection: `{"context": rendered_text}`.
- [ ] Minden exception fail-open, warning/debug loggal.

Tesztek:

- [ ] `register()` ket hookot regisztral.
- [ ] `ctx.register_skill` tovabbra sincs hivva.
- [ ] static no-`setattr` invariant tovabbra is zold.
- [ ] `pre_llm_call` callback off/adaptive/first mod.
- [ ] callback exception fail-open.
- [ ] manifest tartalmazza `pre_llm_call`.

Sikerfeltetel:

- Hermes plugin loader kompatibilis marad;
- nincs runtime mutation;
- 100% coverage.

## Phase 6 - logging

Feladat:

- [ ] stdlib `logging.getLogger(__name__)`.
- [ ] loglevel config/env alapjan.
- [ ] Nincs file handler.
- [ ] Debug log:
  - mode;
  - output;
  - skill count;
  - matched count;
  - injected count;
  - score/reason.
- [ ] Info vagy warning csak valodi config/API hiba eseten.
- [ ] User prompt teljes szoveget ne logolja.

Tesztek:

- [ ] loglevel normalizalas.
- [ ] debug log nem tartalmaz teljes user promptot.
- [ ] no file handler invariant.

Sikerfeltetel:

- debugolhato mukodes;
- nincs adat- vagy prompt-szivarogas logba.

## Phase 7 - dokumentacio frissites

Feladat:

- [ ] `docs/wow-skills-load-plan.md` frissitese minden implementacio kozbeni
  tervtol eltero dontesnel.
- [ ] User-facing config pelda: `docs/usage.md`.
- [ ] Magyar par frissitese: `docs/usage.hu.md`.
- [ ] Ellenorizni a forditasok tartalmi egyezeset.

Sikerfeltetel:

- config hasznalata dokumentalt;
- magyar es angol doksi nem mond ellent egymasnak.

## Phase 8 - verification

Kotelezo lokalis parancsok:

- [ ] `uv run --locked pytest -q`
- [ ] `uv run --locked pre-commit run --all-files --show-diff-on-failure`
- [ ] `uv run --locked ruff check .`
- [ ] `uv run --locked black --check .`
- [ ] `uv run --locked mypy src tests tools`
- [ ] `bats tests/bats/`
- [ ] `scripts/build-release.sh`
- [ ] `git status --short`

Hermes dry-run ellenorzes:

- [ ] `uv run --locked easter-hermes-sorry-skills-patch-hermes --dry-run --target /tmp/hermes-30e947e0a`

Sikerfeltetel:

- pytest 100% coverage zold;
- lint/pre-commit zold;
- bats zold;
- release build zold;
- `dist/` frissult es commitban van;
- Hermes patcher csak dry-run volt futtatva;
- munkafa csak a tervezett fajlokat mutatja.

## Phase 9 - PR

Feladat:

- [ ] Commit(ok) attekintese.
- [ ] PR nyitasa.
- [ ] PR body tartalmazza:
  - summary;
  - config kulcsok;
  - verification parancsok;
  - explicit megjegyzes: nincs Hermes core patch;
  - explicit megjegyzes: nincs `~/.hermes` hozzaferes;
  - explicit megjegyzes: patcher csak `--dry-run`.
- [ ] CI checkek figyelese.
- [ ] Bukas eseten root-cause, majd minimal fix.

Sikerfeltetel:

- PR mergeable;
- minden CI zold;
- nincs remote/live Hermes mutacio.

## Feladat sorrend

1. Contract spike.
2. Config modell.
3. Hermes `skills_list()` adapter.
4. Matcher.
5. Renderer.
6. Hook orchestration.
7. Register + manifest wiring.
8. Logging.
9. Docs.
10. Full verification.
11. Release artifact rebuild.
12. PR.

Ez a sorrend TDD-barath: minden alacsony szintu modul kulon tesztelheto, es a
hook bekotes csak akkor jon, amikor a config/API/matcher/render reszek mar
stabilak.

## Parhuzamosithatosag

- Batch A: contract spike utan a config modell, API adapter es matcher kulon
  workerben is keszulhet.
- Batch B: renderer a matcher adatmodell stabilizalasa utan induljon.
- Batch C: hook orchestration, register wiring es manifest update soros.
- Batch D: coverage/lint, release artifact es PR szigoruan a vegen.

## Rogzitett implementacios dontesek

- `first` mode ugyanazt a matcher + renderer pipeline-t hasznalja, mint az
  `adaptive`, de csak `is_first_turn=True` eseten fut.
- A matcher minimal angol + magyar stopword listat hasznal.
- A user-facing config dokumentacio helye `docs/usage.md` es `docs/usage.hu.md`.

Ezek a dontesek a tesztek elvart viselkedeset is meghatarozzak.
