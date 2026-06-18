"""scripts/run_eval.py — invoke hermes -p per eval case.

Hermes-native port. The migration provenance for the per-binding
replacements is captured in `MIGRATION.skill-port.md` (see docs/plans/07
§T3 inventory). The Hermes event-shape adapter is local; the rest of the
pipeline consumes the Anthropic-shaped dict the adapter produces.

TDD test cases for this module:
  test_run_eval_unnests_hermes_guard
  test_run_eval_restores_hermes_guard_on_exit
  test_run_eval_no_op_when_guard_unset
  test_run_eval_event_shape_adapter_normalizes_hermes_shape
  test_run_eval_uses_hermes_subprocess_env
  test_run_eval_writes_skill_md_to_hermes_home_not_dot_claude
  test_event_shape_adapter_handles_known_shapes
  test_eval_pipeline_end_to_end
  test_help_is_bilingual (parametrized over this script)
  test_console_log_lines_match_bilingual_regex
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `_subprocess` is importable

from _subprocess import hermes_subprocess_env  # noqa: E402
from scripts.utils import emit  # noqa: E402

# Path to the migrated skill body that becomes the eval target SKILL.md.
EVAL_TARGET_TEMPLATE = "{hermes_home}/skills/{category}/{target}/SKILL.md"


def _hermes_event_to_anthropic(event: dict) -> dict:
    """Adapter: Hermes event shape -> Anthropic-shaped dict (T3.011).

    Hermes shape:  {"event": "...", "role": "...", "content": ...}
    Anthropic shape:  {"type": "...", "message": {"content": [...]}}

    The adapter is the single point of translation; the rest of the pipeline
    sees only Anthropic-shaped dicts.
    """
    etype = event.get("event", event.get("type", "message"))
    role = event.get("role", "assistant")
    content = event.get("content", "")
    if not isinstance(content, list):
        content = [{"type": "text", "text": str(content)}]
    return {
        "type": etype,
        "message": {"role": role, "content": content},
    }


def _invoke_hermes(prompt: str, model: str | None) -> str:
    """Invoke `hermes -p` with the stripped env; return stdout.

    NEVER pops HERMES_SESSION from the parent. Uses hermes_subprocess_env()
    to construct the child env.
    """
    cmd = ["hermes", "-p", "--output-format", "stream-json", "--verbose"]
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


def _ensure_eval_target(hermes_home: Path, category: str, target: str, body: str) -> Path:
    """Write the eval target SKILL.md to the flat path under HERMES_HOME.

    The eval target is registered by writing the skill body to
    `<hermes_home>/skills/<cat>/<target>/SKILL.md` (the Hermes flat path).
    """
    target_dir = hermes_home / "skills" / category / target
    target_dir.mkdir(parents=True, exist_ok=True)
    target_skill = target_dir / "SKILL.md"
    target_skill.write_text(body, encoding="utf-8")
    return target_skill


def run_eval(
    cases: list[dict],
    *,
    hermes_home: Path,
    category: str,
    target: str,
    model: str | None = None,
) -> list[dict]:
    """Run a list of eval cases against the eval target SKILL.md.

    Returns a list of per-case result dicts with the Anthropic-shaped events
    translated by the adapter.
    """
    body = f"---\nname: {target}\ndescription: eval target\n---\n# {target}\n"
    ensure_target = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME") is None
    if ensure_target:
        _ensure_eval_target(hermes_home, category, target, body)

    results: list[dict] = []
    for case in cases:
        prompt = json.dumps(case)
        stdout = _invoke_hermes(prompt, model)
        # Each line of stdout is a Hermes NDJSON event.
        events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
        anthropic_events = [_hermes_event_to_anthropic(e) for e in events]
        results.append({"case": case, "events": anthropic_events})

    emit(
        f"Eval pipeline complete: {len(cases)} case(s)",
        f"Eval folyamat kész: {len(cases)} eset",
    )
    return results


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_eval.py",
        description=(
            "Run a benchmark of eval cases against a candidate skill.\n"
            "Use when: you have written/edited a skill and want to measure its "
            "correctness + completeness against a held-out test set.\n"
            "Hasznalat: van egy frissen irt/szerkesztett skill, es merni "
            "szeretned a pontossagat + teljesseget egy tesztkeszleten."
        ),
    )
    p.add_argument("--cases", required=True, help="Path to JSON file with eval cases.")
    p.add_argument("--hermes-home", required=True, help="HERMES_HOME root.")
    p.add_argument("--category", default="default", help="Skill category.")
    p.add_argument("--target", required=True, help="Eval target skill name.")
    p.add_argument("--model", default=None, help="Hermes model id (or omit).")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        cases = [cases]
    results = run_eval(
        cases,
        hermes_home=Path(args.hermes_home),
        category=args.category,
        target=args.target,
        model=args.model,
    )
    json.dump(results, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
