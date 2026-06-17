"""scripts/run_loop.py — long-running orchestrator for the eval pipeline.

Hermes-native port. Invokes the Hermes orchestrator (`hermes -p`); the
`--model` flag accepts a Hermes model id or is omitted (model selection is
a session config). The migration provenance is in
`MIGRATION.skill-port.md` (see docs/plans/07 §T3 inventory).

TDD test cases for this module:
  test_help_is_bilingual (parametrized over this script)
  (T3.016 + T3.017 — Anthropic-binding removal — covered by
  tests/unit/test_skill_creator_frontmatter.py against this script)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from _subprocess import hermes_subprocess_env  # noqa: E402
from scripts.utils import emit  # noqa: E402


def _invoke_hermes_loop(prompt: str, *, model: str | None = None) -> str:
    cmd = ["hermes", "-p", "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=hermes_subprocess_env(),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"hermes -p exited {proc.returncode}\n{proc.stderr}")
    return proc.stdout


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_loop.py",
        description=(
            "Long-running orchestrator that drives the eval pipeline.\n"
            "Use when: you want to iterate over many eval cases without "
            "manually re-invoking run_eval.py per case.\n"
            "Hasznalat: sok eval case-en szeretnel iterativan vegigmenni "
            "anélkül, hogy minden egyes case-re manualisan meghivd a run_eval.py-t."
        ),
    )
    p.add_argument("--model", default=None, help="Hermes model id (or omit).")
    p.add_argument("--prompt", required=True, help="Prompt text for the loop body.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out = _invoke_hermes_loop(args.prompt, model=args.model)
    sys.stdout.write(out)
    emit(
        "Loop body completed",
        "Ciklus törzs befejezve",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
