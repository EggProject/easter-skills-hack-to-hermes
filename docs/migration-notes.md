# 🧾 Migration Notes

[Magyar verzio](migration-notes.hu.md) | [Docs](README.md)

## Current State

This repository started as a Hermes skill/plugin migration experiment. The
public documentation now describes the shipped behavior instead of preserving
the old planning archive.

## Preserved Decisions

| Decision | Current form |
| --- | --- |
| Hermes pin | Patch compatibility is documented against `30e947e0a`. |
| Plugin separation | The plugin registers hooks; the migrated skill is top-level. |
| Skill reminder | `pre_llm_call` adds short adaptive reminders, not full skill bodies. |
| Loaded-skill handling | Already loaded skills are detected from conversation history and downgraded. |
| Safe validation | Patcher dry-run is the review path before operator apply. |

## Removed From Public Docs

The old `docs/plans`, generated audits, and vendored research copies were
removed from the public documentation surface. They contained historical
planning state, stale implementation claims, and raw research artifacts that no
longer helped an operator understand the current project.

## What Remains Detailed

The hook flowcharts remain because they explain the live `pre_llm_call`
behavior better than prose:

- [WOW skill flowcharts](wow-skills-flowcharts.md)
- [Hungarian flowcharts](wow-skills-flowcharts.hu.md)

