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

## Config

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
