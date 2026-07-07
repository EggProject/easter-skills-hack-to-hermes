# 🧩 Plugin és Hookok

[English version](plugin.md) | [Dokumentáció](README.hu.md)

## Runtime Felület

A plugin manifest: `src/easter_hermes_sorry_skills/plugin.yaml`.

```yaml
name: easter-hermes-sorry-skills-plugin
provides_hooks:
  - on_session_start
  - pre_llm_call
```

A `register(ctx)` mindkét hookot beköti Hermesbe. A package-szintű plugin nem
regisztrálja a migrált `skill-creator` skillt.

Ez az oldal csak a runtime bekapcsolást írja le. A release wrapper scriptek a
[Felhasználói telepítés](getting-started.hu.md) oldalon vannak, és Hermes-en
kívül futnak.

## Discovery és Bekapcsolás

Hermes harmadik féltől származó general plugineket plugin könyvtárakból vagy
Python package entry pointokból fedez fel. Egy directory plugin helye
`~/.hermes/plugins/<plugin-name>/`, és kell bele `plugin.yaml` plusz
`__init__.py`. Egy megtalált general plugin opt-in: Hermes csak akkor tölti be,
ha a plugin key szerepel a `plugins.enabled` listában.

A release bundle tartalmazza a bemásolható könyvtárat:

```text
plugin/easter-hermes-sorry-skills-plugin/
```

Ezt ide kell másolni:

```text
~/.hermes/plugins/easter-hermes-sorry-skills-plugin/
```

Utána engedélyezd az `easter-hermes-sorry-skills-plugin` keyt Hermes configban.

## `on_session_start`

Ez a hook ellenőrzi, hogy a cél Hermes checkoutban még a régi skill description
cap van-e. Csak advisoryt ír ki; a cap-et a patcher módosítja, nem a plugin.

## `pre_llm_call`

Ez a hook rövid, ideiglenes skill emlékeztetőt szúrhat be, mielőtt Hermes LLM
hívást indít. Szándékosan kicsi:

1. Betölti a `skill_hook` configot.
2. Hermes runtime API-n keresztül lekéri az enabled skill-eket.
3. Az aktuális user üzenetet skill nevekre és descriptionokra illeszti.
4. Felismeri, ha egy skill már be van töltve a conversation historyban.
5. Csak akkor szúr be shortlistet, ha van hasznos találat.

A teljes döntési folyamat és chat példák megmaradtak itt:
[WOW skill folyamatábrák](wow-skills-flowcharts.hu.md).

## Plugin Saját Configja

A `plugins.enabled` azt szabályozza, hogy Hermes betölti-e a plugint. A beágyazott
`plugins.entries.easter-hermes-sorry-skills-plugin.skill_hook` szakaszt ez a
plugin olvassa a saját hook működéséhez.

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
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

| Kulcs | Default | Jelentés |
| --- | --- | --- |
| `enabled` | `true` | Hook be- vagy kikapcsolása. |
| `mode` | `adaptive` | `adaptive`, `first`, vagy `off`. |
| `output` | `shortlist` | `shortlist`, `names`, vagy `index`. |
| `top_k` | `3` | Maximum hány találó skill kerüljön az emlékeztetőbe. |
| `min_score` | `2` | Minimum score beszúrás előtt. |
| `log_level` | `INFO` | Standard Python logging level. |

A repository nem olvas root-level
`easter-hermes-sorry-skills-plugin:` config kulcsot.

## Módok

| Mód | Működés |
| --- | --- |
| `adaptive` | Minden turnnel fut, de csak illeszkedő enabled skill esetén szúr be. |
| `first` | Csak a session első LLM hívása előtt fut. |
| `off` | Teljesen kihagyja a hookot. |

## Output Formátumok

| Output | Működés |
| --- | --- |
| `shortlist` | Skill nevek és rövid okok. |
| `names` | Csak a talalo skill nevek. |
| `index` | Tomor skill index. |

## Debug

Hook validálásnál állítsd `log_level: DEBUG` értékre. Production configban az
`INFO` legyen az alap, hacsak nincs szükség diagnosztikára.

## Hivatkozások

- Hermes Build a Plugin guide: plugin könyvtárak, `register(ctx)` és
  `ctx.register_hook(...)`.
- Hermes Plugins feature docs: plugin discovery források és `plugins.enabled`.
- Hermes Hooks feature docs: plugin hookok és `pre_llm_call` működés.
