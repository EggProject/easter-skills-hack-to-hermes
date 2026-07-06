# 🩹 Patching Hermes

[Magyar verzio](patching.hu.md) | [Docs](README.md)

## Supported Target

The current patch set is maintained for Hermes commit `30e947e0a`
(`30e947e0a05ef535e4b25a183d8bbe34fd68d1d5`).

Use a pinned checkout for validation:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

## What Gets Patched

| Area | Effect |
| --- | --- |
| Skill description cap | Raises the local description limit from the old short cap to 1024 characters. |
| Skill prompt guidance | Adds guidance so models consult `skill-creator` before editing or creating skills. |
| Prompt snapshot | Clears the skills prompt snapshot after successful write mode so Hermes rebuilds context. |

The patcher validates exact anchors before writing. Drift means Hermes changed
around a patch site and the site table must be updated.

## Dry-Run Output

Dry-run prints the plan and exits without writing target files.

```text
◇ plan for /path/to/hermes:
• would patch: agent/prompt_builder.py (site E1.skills_guidance)
⚠ --dry-run mode, patches were NOT applied
```

Treat dry-run as the review artifact. Apply mode should use the same `--target`
after the plan is accepted.

## Operator Apply

Apply mode is the same command without `--dry-run`:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --target /path/to/hermes-agent
```

Do not apply against an unreviewed checkout. Validate the exact source version
first.

## Troubleshooting

| Symptom | Meaning | Action |
| --- | --- | --- |
| `line drift detected` | Anchor text moved or changed. | Update the patch site for the supported Hermes commit. |
| `validation failed` | One or more patch sites cannot be proven safe. | Do not apply; fix anchors and re-run dry-run. |
| No matching target | The checkout path is wrong or incomplete. | Re-check `--target`. |

