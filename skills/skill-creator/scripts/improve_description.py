"""scripts/improve_description.py — propose a new SKILL.md description.

Hermes-native port. Invokes the Hermes orchestrator with the current
description + an optional rubric and returns the proposed new description.
The migration provenance is captured in `MIGRATION.skill-port.md` (see
docs/plans/07 §T3 inventory).

TDD test cases for this module:
  test_improve_description_invokes_hermes_not_claude
  test_improve_description_unnests_hermes_guard
  test_improve_description_restores_hermes_guard_on_exit
  test_improve_description_no_op_when_guard_unset
  test_improve_description_runtime_error_mentions_hermes
  test_improve_description_help_is_bilingual
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


def _invoke_hermes(prompt: str) -> str:
    cmd = ["hermes", "-p", "--output-format", "text", prompt]
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


def propose_description(current_description: str, *, rubric: str = "") -> str:
    """Return a proposed SKILL.md description string."""
    prompt = (
        "Propose a new SKILL.md description (max 1024 chars, must start with "
        "'Use when') that improves on:\n\n"
        f"{current_description}\n\n"
        f"Rubric: {rubric or '(none)'}"
    )
    return _invoke_hermes(prompt).strip()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="improve_description.py",
        description=(
            "Propose a new SKILL.md description.\n"
            "Use when: the operator asks to rewrite / shorten / improve a "
            "skill's description for the <available_skills> system-prompt index.\n"
            "Hasznalat: az operator ujrairja / roviditi / javitja egy skill "
            "leirasat a <available_skills> rendszerprompt-index szamara."
        ),
    )
    p.add_argument("--current", required=True, help="Current description text.")
    p.add_argument("--rubric", default="", help="Optional rubric to steer the proposal.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    new = propose_description(args.current, rubric=args.rubric)
    sys.stdout.write(new + "\n")
    emit(
        f"New description proposed ({len(new)} chars)",
        f"Új leírás javaslat ({len(new)} karakter)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
