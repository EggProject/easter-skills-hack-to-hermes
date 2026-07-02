# WOW Skills Load Plan

## Cel

Adjunk a Hermes skill-kezelesehez egy futas kozbeni, alacsony zajszintu
skill-emlekezteto reteget. A cel nem a Hermes skill parserenek, frontmatter
kezelesenek vagy skill telepitesi logikajanak atirasa, hanem az, hogy a modell
kevesebbszer felejtse el: vannak enabled skill-ek, es relevans esetben
`skill_view(name)`-mel be kell toltenie oket.

## Nem cel

- Nem nyulunk a Hermes skill fejlec/frontmatter ertelmezesehez.
- Nem pasztazzuk kezzel a profile-okat, skill konyvtarakat vagy Hermes belso
  fajlstrukturajat.
- Nem masoljuk be minden turn ele az osszes enabled skill teljes indexet.
- Nem toltunk be teljes `SKILL.md` tartalmat a hookbol.
- Nem csereljuk le a Hermes meglevo system prompt skill-indexet.

## Fontos kovetelmeny

A skill-listat Hermes API-n vagy Hermes altal adott runtime/tool feluleten
keresztul kell beszerezni. A plugin ne epitsen sajat skill discoveryt, mert az
torne a Hermes profile-, scope-, override- es enabled/disabled-szabalyait.

Implementacios dontes:

1. a plugin a Hermes `tools.skills_tool.skills_list()` API-jat hasznalja
   enabled skill metadata lekeresere;
2. a lekeresett rekordokbol csak `name`, `description`, `category` mezoket
   hasznal a matcher;
3. a plugin nem olvas profile fajlokat es nem jarja be sajat maga a skill
   konyvtarakat;
4. a Hermes core patch csak akkor kerul elo, ha a `skills_list()` hivas plugin
   hookbol bizonyitottan nem hasznalhato biztonsagosan.

Config helye:

```yaml
plugins:
  entries:
    easter-hermes-sorry-skills-plugin:
      skill_hook:
        enabled: true
        mode: adaptive
        output: shortlist
        top_k: 3
        min_score: 2
        log_level: INFO
```

Ez a Hermes mar letezo plugin config mintajat koveti:
`plugins.entries.<plugin_id>.<plugin-owned-key>`.

## Mi legyen a hook

A megfelelo Hermes hook: `pre_llm_call`.

Indok:

- minden LLM call elott fut;
- visszaadhat ephemeral contextet;
- Hermes ezt a user message melle injektalja, nem a system promptba;
- nem rontja a system prompt cache prefixet;
- alkalmas rovid, dinamikus skill shortlist vagy reminder beszurasara.

## Miert nem always-on

Nem jo default, ha minden user uzenet melle ugyanazt az emlekeztetot vagy teljes
skill-indexet betesszuk.

Kockazatok:

- context szennyezes irrelevans feladatoknal;
- recency bias: a friss reminder tul nagy sulyt kap;
- false activation: a modell feleslegesen hiv `skill_view`-t;
- token es latency overhead hosszu sessionokben;
- a tenyleges user task hatterbe szorulhat.

Ezert a default policy adaptiv legyen.

## Javasolt default policy

Alapertelmezett mod: `adaptive`.

Mukodes:

1. `pre_llm_call` megkapja az aktualis `user_message`-et.
2. A plugin Hermes API-n keresztul bekeri az enabled skill metadata listat.
3. A matcher a user promptot osszeveti a skill `name` es `description`
   mezoivel.
4. Csak eleg eros talalatnal injektal rovid top-K shortlistet.
5. A shortlist nem utasitja kotelezo skill-hasznalatra a modellt, csak relevans
   jelolteket ad.

Pelda injektalt context:

```text
Relevant Hermes skills to consider:
- skill-creator: Use when creating or improving SKILL.md instructions.
- code-review: Use when reviewing code changes for risks and regressions.

Use skill_view(name) only if the current task actually matches.
```

## Matcher terv

Elso implementacio: lexical matcher, uj dependency nelkul.

Pontozasi pelda:

- `+5`: explicit skill name szerepel a user promptban;
- `+3`: tobb fontos description-token egyezik;
- `+2`: task/category jellegu szo egyezik;
- `+1`: elso turn es a prompt altalanosan skill-gyanus;
- `-3`: trivialis vagy tul rovid prompt;
- `-3`: a match csak nagyon altalanos stopword-szeru tokenekbol all.

Default ertekek:

```text
mode=adaptive
output=shortlist
matcher=lexical
top_k=3
min_score=2
```

Kesobbi bovites:

- semantic similarity / embedding alapu shortlisteles;
- path/context gate Hermes runtime munkakonyvtar es file-context adatokbol;
- skill risk metadata figyelembe vetele Hermes altal adott metadata mezobol.

## Modok es output formatumok

`mode` azt mondja meg, mikor injektaljon a hook.

```text
off       -> nincs injektalas
adaptive  -> default, csak relevans match eseten
first     -> csak session elso turnjeben rovid reminder vagy names-only lista
```

`output` azt mondja meg, milyen reszletessegu legyen az injektalt tartalom.

```text
shortlist -> default, top-K skill nev + rovid description
names     -> top-K skill nevek description nelkul
index     -> top-K skill nev + teljes Hermes description, debug/teszt celra
```

Az `adaptive` es `names` tehat nem ugyanaz a dimenzio:

- `adaptive`: trigger policy, vagyis csak match eseten tortenik injektalas;
- `names`: output formatum, vagyis az injektalt jeloltekbol csak a nevek
  jelennek meg.

Nincs `always` mod. A mindig injektalo mukodes tul sok context-zajjal jarna.

## Logging

Legyen bekapcsolhato plugin logolas tipikus loglevellel.

Javasolt env:

```text
EASTER_HERMES_SORRY_SKILLS_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

Az env loglevel csak override. A normal konfiguracio a Hermes
`config.yaml` `plugins.entries.easter-hermes-sorry-skills-plugin.skill_hook`
blokkja.

Debug log pelda:

```text
skill_hook: mode=adaptive skills=18 matched=2 injected=2
skill_hook: matched skill-creator score=8 reason=name+description
skill_hook: skipped reason=no_match
```

Ne legyen file handler alapbol; a plugin a standard logging rendszert hasznalja.

## Hermes patch dontes

Az elso implementaciohoz nem tervezunk Hermes core patch-et. A plugin a
Hermes `skills_list()` API-bol dolgozik.

Core patch csak bizonyitott API-akadalynal keszul. Ilyen akadalyt dry-run
validalas es lokalis teszt bizonyit. A patch minimalis input-bovites lenne:
`pre_llm_call` kapna egy Hermes altal osszeallitott enabled skill metadata
listat.

Ez a tartalek terv nem valtoztatna meg a skill discoveryt, es nem vinne sajat
scan logikat a core-ba.

## Hermes system prompt review

A skill hasznalatot leiro Hermes promptok a `30e947e0a` commitban:

- `agent/prompt_builder.py`: `MEMORY_GUIDANCE`;
- `agent/prompt_builder.py`: `SKILLS_GUIDANCE`;
- `agent/prompt_builder.py`: `build_skills_system_prompt()`;
- `agent/system_prompt.py`: a `build_skills_system_prompt()` beszurasa a
  stable system prompt reszbe.

Sajat review:

- A jelenlegi `## Skills (mandatory)` blokk eros recallra optimalizal.
- A `MUST`, `even partially relevant`, `Err on the side of loading` es
  `always better to have context` kifejezesek segitik, hogy a modell ne
  felejtse el a skill-eket.
- Ugyanezek a kifejezesek Qwen-szeru tool-calling modelleknel tul sok
  `skill_view` hivast okozhatnak.
- A hook shortlist megoldas elobb keruljon be, mert konkret jelolteket ad
  aktualis user prompt alapjan, es kisebb kockazatu mint a globalis prompt
  tovabbi erosites vagy atiras.

Prompt-engineer review:

- A prompt-engineer a `## Skills (mandatory)` preambulum roviditeset javasolja
  strukturaltabb routing szabalyra.
- Javasolt irany: explicit `skill_view(name="<exact skill name>")` szabaly,
  kozvetlen name/description match, 1-2 legspecifikusabb skill, es broad vagy
  tangencialis skill-ek kerulese.
- Kockazat: kevesebb false positive, de gyenge descriptionnel romolhat a
  recall.

Dontes:

A system prompt szovegen ebben a feladatban nem valtoztatunk. A prompt
modositasa kulon patch/eval lepes legyen, mert egyszerre erinti a recallt,
false positive aranyt es tobb modellcsalad tool-calling viselkedeset.

## Tesztelesi irany

Unit tesztek:

- explicit skill name match;
- description-token match;
- nincs match trivialis promptnal;
- top-K limit betartasa;
- `off`, `adaptive`, `first` modok;
- `shortlist`, `names`, `index` output formatumok;
- logging aggresziv mockolasa file IO nelkul;
- Hermes API hiba eseten fail-open: ne torje el a turnt, csak ne injektaljon.

Behavior/eval otlet:

- skillenkent 8-10 pozitiv trigger prompt;
- skillenkent 8-10 near-miss negativ prompt;
- merjuk: recall, false activation rate, tool-call precision, token overhead,
  latency.

## Forrasok

- Hermes hooks: https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
- Hermes plugin guide: https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Anthropic tool definitions: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling
- LlamaIndex retrieval-augmented agents: https://developers.llamaindex.ai/python/examples/agent/openai_agent_retrieval/
- LangChain tools: https://docs.langchain.com/oss/python/langchain/tools

## Dontes

A kovetkezo implementacios lepeshez javasolt irany:

`adaptive pre_llm_call` hook, Hermes API-bol szerzett enabled skill
metadata-val, name+description alapu top-K shortlist injektalassal.

Defaultban ne legyen teljes index es ne legyen minden turnben kotelezo
reminder.
