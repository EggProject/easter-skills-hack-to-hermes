# 📦 Üzemeltetés

[English version](operations.md) | [Dokumentáció](README.hu.md)

## Ellenőrzés Handoff Előtt

Dokumentáció vagy kód push előtt futtasd a helyi kaput:

```bash
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
```

Patch kompatibilitáshoz validáld a támogatott Hermes checkoutot:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

## Release Artifact Build

```bash
scripts/build-release.sh
```

A build ezeket írja:

| Artifact | Cél |
| --- | --- |
| `dist/easter-hermes-sorry-skills.pyz` | Single-file Python zipapp. |
| `dist/easter-hermes-sorry-skills-v0.1.0.tar.gz` | Release bundle wrapperekkel és README-kkel. |

A `dist/` mappában release-t érintő változás után a legfrissebb artifact legyen.

## Wrapper Scriptek

A release bundle tartalma:

```text
scripts/easter-hermes-sorry-skills-patch-hermes.sh
scripts/easter-hermes-sorry-skills-report.sh
```

A wrapperek közeli `dist/` helyeken keresik a `.pyz` fájlt, majd a megfelelő
entry pointot futtatják.

## CI Forma

A GitHub workflow párhuzamos jobokra bontja a munkát:

| Job | Cél |
| --- | --- |
| `lint` | Dependency sync, `.pyz` build wrapper smoke testhez, pre-commit. |
| `test-python` | Pytest futtatás 100% coverage kapuval. |
| `test-bats` | Shell wrapper smoke tesztek. |
| `static-safety` | Valódi silencer commentek ellenőrzése a forrásban. |
| `build-package` | Release zipapp build packaging smoke testként. |

## Release Checklist

1. Futtasd a teszteket és pre-commitot.
2. Futtasd a Hermes patcher dry-runt `/tmp/hermes-30e947e0a` ellen.
3. Építsd újra a `dist/` mappát, ha release-t érintő fájl változott.
4. Pushold a feature branchet és várd meg a zöld CI checkeket.

