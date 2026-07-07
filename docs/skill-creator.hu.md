# 🛠️ Skill Creator

[English version](skill-creator.md) | [Dokumentáció](README.hu.md)

## Helye

A migrált skill itt él:

```text
skills/skill-creator/
```

Szándékosan a plugin package-en kívül van. Hermes számára flat
`skill-creator` nevű skill legyen, ne plugin által birtokolt bundled skill.

## Telepítés Hermesbe

A release bundle tartalmazza ezt a könyvtárat:

```text
skills/skill-creator/
```

Ezzel kell lecserélni Hermes installed OpenAI `skill-creator` skilljét:

```bash
skill_backup="$HOME/.hermes/skills/skill-creator.backup.$(date +%Y%m%d%H%M%S)"
[ ! -e "$HOME/.hermes/skills/skill-creator" ] || \
  mv "$HOME/.hermes/skills/skill-creator" "$skill_backup"
mkdir -p "$HOME/.hermes/skills"
cp -R skills/skill-creator "$HOME/.hermes/skills/skill-creator"
```

A backup lépés megtartja az előző OpenAI verziót kézi rollbackhez.

## Cél

Akkor használd, amikor a modellnek skillt kell létrehoznia, javítania,
csomagolnia vagy értékelnie. A Hermes port megtartja az upstream skill-authoring
workflow-t, de a Claude-specifikus parancsokat és csomagolási feltételezéseket
Hermes-kompatibilis megfelelőkre cseréli.

## Mi Változott A Portban?

| Upstream feltételezés | Hermes port |
| --- | --- |
| `claude` command példák | Hermes command példák. |
| `.skill` package cél | `.zip` package cél. |
| Claude session output | Hermes-kompatibilis output kezelés. |
| Claude nesting guard | Hermes subprocess helper. |

## Kapcsolat A Pluginnal

A plugin emlékeztetheti a modellt, hogy a `skill-creator` releváns, de a skill
tartalma Hermes normál skill rendszerén keresztül töltődik be. Ez a
szétválasztás fontos: a plugin hookok emlékeztetőket kezelnek, a tényleges
skill betöltést Hermes birtokolja.

## Kapcsolódó Dokumentumok

- [Plugin és hookok](plugin.hu.md)
- [WOW skill folyamatábrák](wow-skills-flowcharts.hu.md)
- [Migrációs jegyzetek](migration-notes.hu.md)
