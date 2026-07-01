# Fejlesztés

> [English](development.md)
> [Vissza a README-hez](../README.hu.md)

Ez az oldal az `easter-hermes-sorry-skills` helyi teszt-, lint- és CI-beállítását írja le. PR nyitása előtt olvasd el — az itt felsorolt kapuk mind a GitHub CI workflow-ban érvényesülnek.

---

## Elrendezés

A tesztkészlet négy rétegre van bontva. Minden rétegnek egy felelőssége és egy külön futtató parancsa van.

- `tests/unit/` — 11 Python unit teszt (`pytest`). Lefedi a `cli_patch`-et, a profiles CLI-t, a patcher-t, a safety dekorátort, a scope-ot, a conftest sentinelt és a subprocess placeholdert.
- `tests/report/` — 9 reporter teszt + `_fixtures.py`. Lefedi a `cli_report`-ot, a reporter formátumot, a token-számolást, a verbose módot, valamint a readonly + branch felületeket.
- `tests/meta/` — 3 meta-teszt a `tools/` helperjeihez. Lefedi a `check_bilingual.py`-t, a `check_line_count.py`-t és a meta conftest-et.
- `tests/bats/` — bash smoke tesztek (`patch-hermes.bats`, `report.bats`). Végigmegy a shell wrapper-eken.

A felső szintű tesztek (`test_register.py`, `test_advisory.py`, `test_i18n_bilingual.py`) a `tests/conftest.py` összevont fixture fájl mellett élnek. A conftest a következő fixture-öket biztosítja: `hermes_home`, `hermes_checkout`, `skill_creator_home` és `real_hermes_agent_sentinel`. Import-időben előre regisztrálja a `hermes_cli.profiles` és `hermes_cli.skills_config` stub modulokat, hogy a `tests/unit/*.py` a valódi Hermes futtatókörnyezet nélkül is importálhassa a tesztelt gyártási kódot.

A stubok a `tests/stubs/` alatt élnek (`agent`, `hermes_cli`, `rich`, `tools` típus `.pyi` fájlok, valamint `hermes_constants.pyi` és `yaml.pyi`). A minimál-Hermes fixture a `tests/fixtures/minimal_hermes/seed_minimal.py` címen található, és a `MINIMAL_HERMES_FILES` + `seed_minimal()` szimbólumokat exportálja.

---

## Tesztek futtatása

Az egyesített kapu egyetlen futtatással végigmegy minden hookon és tesztrétegen:

```bash
uv run --locked pre-commit run --all-files
```

Rétegenkénti futtatás:

```bash
uv run --locked pytest                  # Python tests (unit + report + meta + top-level)
bats tests/bats/                        # shell smoke tests
uv run --locked ruff check              # ruff lint
uv run --locked black --check           # black format check
uv run --locked mypy                    # static type check (calls mypy_wrapper.sh)
uv sync --all-extras --dev              # one-time: install every dependency
```

Minden Python parancsot `uv run --locked` prefix-szel kell futtatni (a `.claude/rules/worktree-pr-workflow.md` szerint); ez tartja autoritatívnek az `uv.lock`-ot. Soha ne hívd közvetlenül a `pytest`, `ruff`, `mypy`, `black`, `wemake-python-styleguide` vagy `pre-commit` parancsokat.

A lefedettség 100%-os branch coverage kapuval fut a `pyproject.toml` alapján (`--cov-fail-under=100`). A Python gate a csomagot, a `tools/` fájlokat és a közös teszt fixture-öket fedi; a bats smoke tesztek külön fedik a shell wrapper-eket.

---

## Lint és típusellenőrzés

A `.pre-commit-config.yaml` a kapu egyetlen forrása. A hook-ok a legszigorúbbtól a legkevésbé szigorú felé haladnak:

1. `check-line-count` (lokális) — 500-soros fájlonkénti cap-et és három további invariánst kényszerít ki a tervezési markdown könyvtáron (a glob a `tools/check_line_count.py:37` fájlban konfigurálható). Kihagyja a `docs/research/` mappát (az upstream skill-creator referencia).
2. `bats` (lokális) — futtatja a `tests/bats/` mappát.
3. `wemake-python-styleguide` 1.6.2 — a legszigorúbb Python linter. Hatókör: `src/`.
4. `flake8` 7.1.1 — másodlagos legszigorúbb Python lint. Hatókör: `src/`.
5. `ruff` 0.11.9 + `ruff-format` — gyors lint + formázás. Hatókör: `src/`, `tests/`, `tools/`.
6. `black` 25.11.0 — másodlagos formázó (sorhossz 120). Hatókör: `src/`, `tests/`, `tools/`.
7. `mypy` v1.11.2 `--strict` — statikus típusellenőrzés. Hatókör: `src/`.
8. `shellcheck` (lokális bináris) — `scripts/*.sh` lint. Súlyosság = warning.

A pre-commit konfig szándékosan mellőzi a `check_bilingual.py`-t, mert a migrált skill angol marad (operator-authorized deviation).

---

## CI workflow

A `.github/workflows/ci.yml` `main`-re push és minden pull request esetén fut. Több külön jobot használ, így a független checkek párhuzamosan futhatnak:

1. `lint` — `uv sync --locked --all-extras --dev`, system `bats` + `shellcheck`, Linux-kompatibilis `.pyz` a wrapper smoke tesztekhez, majd `uv run --locked pre-commit run --all-files --show-diff-on-failure`.
2. `test-python` — `uv run --locked pytest -q`, a `pyproject.toml` 100%-os branch coverage kapujával.
3. `test-bats` — Linux-kompatibilis `.pyz` build, majd `bats tests/bats/`.
4. `static-safety` — ellenőrzi, hogy `# noqa`, `# type: ignore` vagy `# pragma: no cover` sor NEM létezik az `src/`-ben.
5. `build-package` — `scripts/build-release.sh --only-shiv` release-artifact smoke build.

Piros CI-t mutató pull requesteket TILOS `--admin` flag-gel mergelni. Várjuk meg a CI-t, vagy kérjünk explicit operator override-ot.

---

## Egyedi tool-ok

### `tools/check_bilingual.py`

AST-walk az `src/`, `scripts/` és `skills/` mappákon. Minden `print(...)` és `logger.{info,warning,error,...}(...)` hívásra, amelynek első argumentuma statikus string, ellenőrzi, hogy a formátum-string illeszkedik a `^\[en\] .+?/ \[hu\] .+?$` mintára — vagyis az `[en] ... / [hu] ...` egysoros kétnyelvű felületre (`tools/check_bilingual.py:44`). A nem-statikus stringek (változók, nem-literális placeholder-eket tartalmazó f-stringek) kimaradnak; a hívónak futásidőben kell kétnyelvű kimenetet előállítania.

A tool a Click parancsok docstringjeit is végigjárja, és ellenőrzi, hogy mind a `Usage (English)`, mind a `Használat (magyar)` szekció jelen van (`tools/check_bilingual.py:45-46`). Az egyik szekciót nélkülöző help docstringek finding-ként jelennek meg.

A pre-commit-ból jelenleg ki van véve (operator döntés szerint, lásd `.pre-commit-config.yaml:25-30`).

### `tools/check_line_count.py`

Négy invariánst kényszerít ki a tervezési markdown könyvtáron. A könyvtár glob és a négy invariáns a modul docstring-ben van konfigurálva a `tools/check_line_count.py:1-23` fájlban; a fájlonkénti sor cap a `PER_FILE_CAP = 500` (`tools/check_line_count.py:36`):

1. **Per-file cap** — minden tervfájl KÖTELEZŐEN `<= 500` sor (`PER_FILE_CAP = 500`, `tools/check_line_count.py:36`).
2. **Footer drift** — minden nem-index tervfájl KÖTELEZŐEN a `<!-- end of file: NN lines (budget BB) -->` sorral végződik, ahol `NN == wc -l`. A `00-index.md` KÖTELEZŐEN a csupasz `<!-- end of file -->` markert használja.
3. **Budget-table Total** — a `00-index.md` `**Total**` cellája ÉS minden `Sum NNNN < Total` prózai szakasz KÖTELEZŐEN egyenlő az élő `wc -l` összeggel minden tervfájlon (az index-szel együtt).
4. **Per-cell guard** — a file-map tábla minden sorára az `Actual` KÖTELEZŐEN egyenlő a hivatkozott útvonal `wc -l` értékével, a `Budget` pedig KÖTELEZŐEN `>= Actual`.

CLI flagek: `--no-footer`, `--no-budget-table`, `--no-per-cell` kikapcsolják az egyes invariánsokat; `--enforce-X` visszakapcsolja őket (alapértelmezetten be).

### `tools/mypy_wrapper.sh`

A mypy-t a `src/easter_hermes_sorry_skills/__init__.py`-n és a `src/easter_hermes_sorry_skills/_advisory.py`-n futtatja, `MYPYPATH=src` és `--strict --explicit-package-bases` beállítással (`tools/mypy_wrapper.sh:1-22`). Azért létezik, mert a pre-commit-mypy figyelmen kívül hagyja a `MYPYPATH` környezeti változót, és `pass_filenames: false` + csomagnév kombinációval a CLI-n nem tud futni nélküle. Előnyben részesíti a `.venv/bin/mypy`-t, és a PATH-ra esik vissza.

---

## Közreműködési workflow

> Megjegyzés: Az alábbi `.claude/rules/*.md` útvonalak a projekt belső rule-fájljaira mutatnak, amelyek a repo-ba vannak commitolva. Ezek a worktree+PR workflow-t szabályozzák, és nem külső függőségek.

Minden változtatás dedikált worktree-ben, dedikált branch-en történik; semmi sem kerül közvetlenül a `main`-re.

1. Worktree létrehozása: `git worktree add .claude/worktrees/<branch> -b <branch>`.
2. Azonnal futtasuk az `uv sync --locked` parancsot, hogy a `.venv` a zárolt függőségekkel települjön.
3. Változtatás elkészítése. MINDEN ezt követő parancshoz `uv run --locked <command>` prefixet kell használni.
4. Az egyesített kapu helyi futtatása: `uv run --locked pre-commit run --all-files`.
5. Commit. PR megnyitása.
6. **Kövesd a PR-t, amíg merge-ölve nem lesz.** A megnyitott és elfeledett (vagy merge nélkül bezárt) PR a `.claude/rules/follow-up-pr-until-merged.md` megsértése. Ha a CI blokkolja a PR-t, javítsd a blokkoló okot — ne zárd be. Ha egy CI hiba nem a te változtatásodhoz kapcsolódik, rebaselj és futtasd újra.
7. Minden PR merge után futtasuk a `git pull origin main` parancsot, hogy frissüljön a helyi `origin/main` referencia.

Amikor maga a `.claude/` változik (CLAUDE.md, rules, agents, skills), REBASE-eld MINDEN aktív worktree-t a main-re, ÉS indíts ÚJ AGENTET, hogy az új utasítások tisztán betöltődjenek.

PR megnyitásakor hivatkozz arra az EN dokra, amit a változtatásod dokumentál; a HU tükör ugyanazt az életciklust követi, mint testvérfájl.
