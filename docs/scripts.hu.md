# Szkriptek

> [English](scripts.md) · [Magyar verzió](scripts.hu.md)
> [Vissza a README-hez](../README.hu.md)

Ez az oldal az `easter-hermes-sorry-skills` csomaghoz szállított két Python CLI-t és két shell wrapper-t dokumentálja. A CLI-k console-script entry pointként vannak deklarálva a `pyproject.toml:33-36` sorban; a shell wrapper-ek kényelmi indítók, amelyek a venv-et feloldják `exec` előtt.

Mindkét CLI kétnyelvű `--help` szöveget ír ki (angol + magyar), és szándékosan vékony: minden flag egy típusos dataclassba folyik (`PatchArgs` az #1-hez, `ReportInputs` a #2-höz); a click dekorátor csak az argv-ot parseolja.

---

## #1 `easter-hermes-sorry-skills-patch-hermes`

Idempotens Hermes patcher. Alkalmazza az S1.cap-et (a hard-coded `60` cap-et
`MAX_DESCRIPTION_LENGTH`-re cseréli) plusz 6 Task E prompt-injection
helyet a consult rule számára. A Task E alapértelmezetten fut — nincs
opt-out flag. A patcher **alapból ÍR**; a `--dry-run` kapcsolóval csak
auditálhatsz.

### Szinopszis

```text
easter-hermes-sorry-skills-patch-hermes [--target DIR] [--dry-run] [--verbose] [--help]
```

### Flag-ek

| Flag | Típus | Alapértelmezett | Hatás |
|---|---|---|---|
| `--target DIR` | útvonal | `~/.hermes/hermes-agent` (MEGTAGADVA) | Felhasználói tulajdonú Hermes checkout. Az alapértelmezett a no-touch sentinel; a patcher megtagadja (`resolve()` összehasonlítás, 4-es kilépési kód). Adj meg explicit útvonalat. |
| `--dry-run` | flag | `false` (ír) | Csak audit; nem ír. |
| `--verbose` | flag | `false` | Kétnyelvű per-hely diagnosztikát ír ki. |
| `--help` / `-h` | flag | `false` | Kétnyelvű (EN + HU) súgót mutat. |

### Példa

```bash
$ easter-hermes-sorry-skills-patch-hermes --dry-run --target /path/to/user-hermes
[en] S1.cap: matched, would patch
[hu] S1.cap: illesztve, patch-elendo
[en] Task E site 1/5: matched, would patch
[hu] Task E 1/5 hely: illesztve, patch-elendo
$ echo $?
0
```

### Exit kódok

A `_patcher_consts.py:13-18` fájlban definiálva:

| Kód | Jelentés |
|---|---|
| `0` | OK |
| `1` | validáció |
| `2` | drift |
| `3` | jogosultság |
| `4` | I/O |
| `5` | user-abort |

---

## #2 `easter-hermes-sorry-skills-report`

Read-only operátori nézet: "mi van most élesítve, és mennyibe kerül?"
Jelenti az engedélyezett skilleket profilonként, token becslésekkel,
használati számlálókkal és utolsó-használat időbélyegekkel. NINCS
fájlírás (kivéve `--json PATH`); NINCS config-flip; NINCS install hívás.

### Szinopszis

```text
easter-hermes-sorry-skills-report [--profile NAME] [--sort {tokens,use_count,last_used_at}] [--format {text,json}] [--json PATH] [--verbose] [--help]
```

### Flag-ek

| Flag | Típus | Alapértelmezett | Hatás |
|---|---|---|---|
| `--profile NAME` | sztring | (minden profil) | A jelentést egy megadott profilra korlátozza. |
| `--sort` | choice | `tokens` | Sorok rendezése egyike: `tokens`, `use_count`, `last_used_at`. |
| `--format` / `--fmt` | choice | `text` | Kimeneti formátum: `text` (rich táblák) vagy `json` (géppel olvasható). |
| `--json PATH` | útvonal | `./skill-report.json` | A JSON jelentést a `PATH` útvonalra írja. Csak akkor van értelme, ha a `--format json` is át van adva. Az alapértelmezett JSON név a `DEFAULT_JSON_NAME` a `_cli_report_helpers_consts.py:42` fájlban. |
| `--verbose` | flag | `false` | Bőbeszédű diagnosztika. |
| `--help` | flag | `false` | Kétnyelvű (EN + HU) súgót mutat. |

A CLI ezen kívül elutasítja a legacy `--apply`, `--emit-migration-note` és
`--write-report` flageket (a `REJECTED_FLAGS` lista definiálja őket a
`_cli_report_helpers_consts.py:12-18` fájlban); ezek bármelyikének átadása
nem nulla kilépési kóddal kilép.

### Példa

```bash
$ easter-hermes-sorry-skills-report --format json --json ./skill-report.json --sort use_count
[en] writing report to ./skill-report.json
[hu] jelentés írása ide: ./skill-report.json
$ echo $?
0
```

### Exit kódok

| Kód | Jelentés |
|---|---|
| `0` | A jelentés renderelve (és opcionálisan kiírva). |
| `2` | Érvénytelen `--sort` vagy `--format` érték, vagy elutasított legacy flag volt átadva. |

---

## Shell wrapper-ek

Két 15 soros bash wrapper a `scripts/` alatt biztosít stabil
`./scripts/<név>.sh` belépési pontot, függetlenül attól, hogy a projekt
`.venv`-en vagy `PATH`-on keresztül van-e telepítve. Minden wrapper
`set -euo pipefail`-t használ, `cd "$(git rev-parse --show-toplevel)"`-t
futtat, és `127`-es kóddal kétnyelvű hibát ír stderr-re, ha az entry point
nem található (az üzenet az operátornak szól: `uv sync --locked --all-extras --dev`).

| Wrapper | Megfelelő CLI |
|---|---|
| `scripts/easter-hermes-sorry-skills-patch-hermes.sh` | #1 CLI |
| `scripts/easter-hermes-sorry-skills-report.sh` | #2 CLI |

### Wrapper kontraktus

```text
1. set -euo pipefail
2. cd to the git repo root (so .venv/bin/... resolves)
3. if .venv/bin/<name> exists and is executable → exec it
4. elif <name> is on PATH → exec it
5. else → print bilingual ERROR to stderr, exit 127
```

### Példa

```bash
$ ./scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
[en] S1.cap: matched, no change in dry-run
[hu] S1.cap: illesztve, dry-run módban nincs valtozas
```

---

## Forrás-ellenőrzés

- `src/easter_hermes_sorry_skills/cli_patch.py`, `_patcher_consts.py`
  (Script #1 + exit kódok)
- `src/easter_hermes_sorry_skills/cli_report.py`, `_cli_report_cmd.py`,
  `_cli_report_helpers_consts.py`, `_cli_report_helpers_parse.py`
  (Script #2)
- `pyproject.toml:33-36` (entry pointok); `scripts/*.sh` (két wrapper)
