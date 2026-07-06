# 🧰 Commands

[Magyar verzio](commands.hu.md) | [Docs](README.md)

## `easter-hermes-sorry-skills-patch-hermes`

Patches a Hermes checkout. It writes by default; `--dry-run` changes the run
into validation only.

User install path:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

Development-from-source path:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

| Option | Meaning |
| --- | --- |
| `--target PATH` | Hermes checkout to inspect or patch. Defaults to Hermes' live checkout path. |
| `--dry-run` | Print the patch plan and validate anchors without writing. |
| `--verbose` | Print detailed diagnostics. |
| `--lang en\|hu` | Select command output language. |

The patcher raises the local skill description limit to 1024 characters and
applies the prompt guidance sites used by this package.

## `easter-hermes-sorry-skills-report`

Reads Hermes profile and skill metadata and prints a usage report.

User install path:

```bash
bash scripts/easter-hermes-sorry-skills-report.sh \
  --sort tokens \
  --format text
```

Development-from-source path:

```bash
uv run --locked easter-hermes-sorry-skills-report \
  --sort tokens \
  --format text
```

| Option | Meaning |
| --- | --- |
| `--profile NAME` | Restrict the report to one profile. |
| `--sort tokens\|use_count\|last_used_at` | Select row order. |
| `--format text\|json` | Select output format. |
| `--json PATH` | Write JSON output to `PATH` when `--format json` is used. |
| `--verbose` | Print detailed diagnostics. |
| `--lang en\|hu` | Select command output language. |

The reporter does not flip config, install skills, or patch Hermes.

## Release Wrappers

The release tarball includes shell wrappers in `scripts/`. They resolve
`dist/easter-hermes-sorry-skills.pyz` next to the wrapper or current checkout
and then run the matching Python entry point. They do not run `uv`.
