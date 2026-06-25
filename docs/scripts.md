# Scripts

> [English](scripts.md) · [Magyar verzió](scripts.hu.md)
> [Back to README](../README.md)

This page documents the three Python CLIs and three shell wrappers shipped
with `easter-hermes-sorry-skills`. The CLIs are declared as console-script
entry points in `pyproject.toml:33-36`; the shell wrappers are convenience
launchers that resolve the venv before execing the entry point.

All three CLIs print bilingual `--help` text (English + Hungarian). All
three are intentionally thin: every flag flows through to a typed
dataclass (`PatchArgs` for #1, `ReportInputs` for #3; #2 is invoked via
`run_audit(...)`) and the click decorator only parses argv.

---

## #1 `easter-hermes-sorry-skills-patch-hermes`

Idempotent Hermes patcher. Applies S1.cap (replaces the hard-coded `60`
cap with `MAX_DESCRIPTION_LENGTH`) plus 6 Task E prompt-injection sites
for the consult rule. Task E runs by default — there is no opt-out flag
for it. The patcher WRITES by default; pass `--dry-run` to audit only.

### Synopsis

```text
easter-hermes-sorry-skills-patch-hermes [--target DIR] [--dry-run] [--verbose] [--help]
```

### Flags

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--target DIR` | path | `~/.hermes/hermes-agent` (REFUSED) | User-owned Hermes checkout. The default is the no-touch sentinel; the patcher refuses it (resolve() comparison, exit code 4). Pass an explicit path to patch a different checkout. |
| `--dry-run` | flag | `false` (writes) | Audit only; no writes. Default behavior is to WRITE. |
| `--verbose` | flag | `false` | Print bilingual per-site diagnostics on stderr/stdout. |
| `--help` / `-h` | flag | `false` | Show bilingual EN + HU help. |

### Example

```bash
$ easter-hermes-sorry-skills-patch-hermes --dry-run --target /path/to/user-hermes
[en] S1.cap: matched, would patch
[hu] S1.cap: illesztve, patch-elendo
[en] Task E site 1/5: matched, would patch
[hu] Task E 1/5 hely: illesztve, patch-elendo
$ echo $?
0
```

### Exit codes

Defined in `_patcher_consts.py:13-18`:

| Code | Meaning |
|---|---|
| `0` | OK |
| `1` | validation |
| `2` | drift |
| `3` | permission |
| `4` | I/O |
| `5` | user-abort |

---

## #2 `easter-hermes-sorry-skills-install-profiles`

Per-profile READ-ONLY audit of the migrated skill-creator skill. Walks
every Hermes profile (the default `hermes` profile plus every named
profile from `hermes_cli.profiles.list_profiles()`), audits each
profile's enabled-skills tree, and emits a report. There is no
`--apply` / `--dry-run` split — the runner is read-only by design.

### Synopsis

```text
easter-hermes-sorry-skills-install-profiles [--profile NAME] [--verbose] [--json] [--help]
```

### Flags

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--profile NAME` | string | (audit all profiles) | Restrict the audit to one named profile. |
| `--verbose` | flag | `false` | Verbose progress output (bilingual). |
| `--json` | flag | `false` (rich text tables) | Emit machine-readable JSON instead of the rich text tables. |
| `--help` / `-h` | flag | `false` | Show bilingual EN + HU help. |

### Example

```bash
$ easter-hermes-sorry-skills-install-profiles
[en] auditing default profile…
[hu] alapertelmezett profil audit…
[en] profile=hermes enabled_skills=4 disabled_skills=2
[hu] profil=hermes engedelyezett=4 tiltott=2
$ echo $?
0
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Audit completed (whether or not any drift was found). |
| non-zero | Unexpected error during profile resolution or rendering. |

---

## #3 `easter-hermes-sorry-skills-report`

Read-only operator view: "what is on right now, and what does it cost?"
Reports enabled skills per profile with token estimates, use counts, and
last-used timestamps. NO file writes (except an operator-chosen
`--json PATH`); NO config flips; NO install calls.

### Synopsis

```text
easter-hermes-sorry-skills-report [--profile NAME] [--sort {tokens,use_count,last_used_at}] [--format {text,json}] [--json PATH] [--verbose] [--help]
```

### Flags

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--profile NAME` | string | (all profiles) | Restrict the report to one named profile. |
| `--sort` | choice | `tokens` | Sort rows by one of: `tokens`, `use_count`, `last_used_at`. |
| `--format` / `--fmt` | choice | `text` | Output format: `text` (rich tables) or `json` (machine-readable). |
| `--json PATH` | path | `./skill-report.json` | Write the JSON report to `PATH`. Only meaningful when `--format json` is also passed. The default JSON name is `DEFAULT_JSON_NAME` in `_cli_report_helpers_consts.py:42`. |
| `--verbose` | flag | `false` | Verbose diagnostics. |
| `--help` | flag | `false` | Show bilingual EN + HU help. |

The CLI also rejects the legacy flags `--apply`, `--emit-migration-note`,
and `--write-report` (defined in `REJECTED_FLAGS` at
`_cli_report_helpers_consts.py:12-18`). Passing any of them exits
non-zero before the report is built.

### Example

```bash
$ easter-hermes-sorry-skills-report --format json --json ./skill-report.json --sort use_count
[en] writing report to ./skill-report.json
[hu] jelentés írása ide: ./skill-report.json
$ echo $?
0
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Report rendered (and optionally written). |
| `2` | Invalid `--sort` or `--format` value, or a rejected legacy flag was passed. |

---

## Shell wrappers

Three 15-line bash wrappers under `scripts/` provide a stable
"`./scripts/<name>.sh`" entry point regardless of whether the project
is installed via the `.venv` or via `PATH`. Every wrapper uses
`set -euo pipefail`, runs `cd "$(git rev-parse --show-toplevel)"`,
and exits `127` with a bilingual error if the entry point is not
found (the message tells the operator to run
`uv sync --locked --all-extras --dev`).

| Wrapper | Maps to |
|---|---|
| `scripts/easter-hermes-sorry-skills-patch-hermes.sh` | CLI #1 |
| `scripts/easter-hermes-sorry-skills-install-profiles.sh` | CLI #2 |
| `scripts/easter-hermes-sorry-skills-report.sh` | CLI #3 |

### Wrapper contract

```text
1. set -euo pipefail
2. cd to the git repo root (so .venv/bin/... resolves)
3. if .venv/bin/<name> exists and is executable → exec it
4. elif <name> is on PATH → exec it
5. else → print bilingual ERROR to stderr, exit 127
```

### Example

```bash
$ ./scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
[en] S1.cap: matched, no change in dry-run
[hu] S1.cap: illesztve, dry-run módban nincs valtozas
```

---

## Sources verified

- `src/easter_hermes_sorry_skills/cli_patch.py`, `_patcher_consts.py` (Script #1 + exit codes)
- `src/easter_hermes_sorry_skills/cli_profiles.py`, `_cli_profiles_cli.py` (Script #2)
- `src/easter_hermes_sorry_skills/cli_report.py`, `_cli_report_cmd.py`, `_cli_report_helpers_consts.py`, `_cli_report_helpers_parse.py` (Script #3)
- `pyproject.toml:33-36` (entry points); `scripts/*.sh` (three wrappers)
