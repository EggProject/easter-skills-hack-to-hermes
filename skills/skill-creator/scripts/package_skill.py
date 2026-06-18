"""scripts/package_skill.py — tar up the skill dir for hub install.

Hermes-native port. Wraps the skill dir at `skills/skill-creator/` (or any
target) into a tarball at `--output`.

TDD test cases for this module:
  test_help_is_bilingual (parametrized over this script)
"""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

from scripts.utils import emit


def package(skill_dir: Path, output: Path) -> Path:
    """Create a tarball of `skill_dir` at `output`. Returns `output`."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as tf:
        tf.add(skill_dir, arcname=skill_dir.name)
    return output


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="package_skill.py",
        description=(
            "Tar up a skill dir for hub install.\n"
            "Use when: you want to publish the migrated skill to a private "
            "or public skill hub.\n"
            "Hasznalat: a migralt skill-et egy privat vagy nyilvanos "
            "skill hub-ra szeretned publikalni."
        ),
    )
    p.add_argument("--skill-dir", required=True, help="Path to the skill dir.")
    p.add_argument("--output", required=True, help="Path to the output tarball.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out = package(Path(args.skill_dir), Path(args.output))
    emit(
        f"Packaged: {out}",
        f"Csomagolva: {out}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
