# 🧰 Parancsok

[English version](commands.md) | [Dokumentáció](README.hu.md)

## `easter-hermes-sorry-skills-patch-hermes`

Hermes checkoutot patchel. Alapból ír; a `--dry-run` csak validálásra váltja a
futast.

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run \
  --target /tmp/hermes-30e947e0a
```

| Opció | Jelentés |
| --- | --- |
| `--target PATH` | Az ellenőrzendő vagy patchelendő Hermes checkout. Alapból a Hermes live checkout pathja. |
| `--dry-run` | Patch terv és anchor validálás írás nélkül. |
| `--verbose` | Részletes diagnosztika. |
| `--lang en\|hu` | Command output nyelve. |

A patcher a lokális skill description limitet 1024 karakterre emeli, és
alkalmazza a csomaghoz tartozó prompt guidance site-okat.

## `easter-hermes-sorry-skills-report`

Hermes profile és skill metadata alapján használati riportot ír ki.

```bash
uv run --locked easter-hermes-sorry-skills-report \
  --sort tokens \
  --format text
```

| Opció | Jelentés |
| --- | --- |
| `--profile NAME` | Riport szűkítése egy profilra. |
| `--sort tokens\|use_count\|last_used_at` | Sorbarendezes. |
| `--format text\|json` | Kimeneti formátum. |
| `--json PATH` | JSON output írása `PATH` helyre, ha `--format json` aktív. |
| `--verbose` | Részletes diagnosztika. |
| `--lang en\|hu` | Command output nyelve. |

A reporter nem flippel configot, nem installál skillt, és nem patchel Hermest.

## Release Wrapper-ek

A release tarball tartalmazza a `scripts/` shell wrappereket. Ezek megkeresik a
`dist/easter-hermes-sorry-skills.pyz` fájlt a wrapper mellett vagy az aktuális
checkoutban, majd a megfelelő Python entry pointot futtatják.
