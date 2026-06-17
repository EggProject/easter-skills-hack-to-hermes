"""scripts/generate_report.py — write `report.md` and `feedback.json` for the viewer.

Hermes-native port. Reads the output of `aggregate_benchmark.py` and writes:
  - `report.md`  — human-readable summary
  - `feedback.json` — the viewer's data file (relative path to viewer.html)

TDD test cases for this module:
  test_eval_pipeline_end_to_end (covers generate_report via the e2e path)
  test_help_is_bilingual (parametrized over this script)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.utils import emit


def _render_markdown(agg: dict, *, title: str = "Eval Report") -> str:
    a = agg.get("aggregate", {})
    lines = [
        f"# {title}",
        "",
        "## Aggregate",
        "",
        f"- mean: {a.get('mean', 0.0):.3f}",
        f"- stddev: {a.get('stddev', 0.0):.3f}",
        f"- p50: {a.get('p50', 0.0):.3f}",
        f"- p95: {a.get('p95', 0.0):.3f}",
        "",
        "## Per-case scores",
        "",
    ]
    for pc in agg.get("per_case", []):
        lines.append(f"- {pc.get('case_id', '?')}: {pc.get('score', 0.0):.3f}")
    return "\n".join(lines) + "\n"


def generate_report(agg: dict, *, out_dir: Path, title: str = "Eval Report") -> tuple[Path, Path]:
    """Write `report.md` + `feedback.json` to `out_dir`; return both paths.

    The viewer.html (separate file, in `eval-viewer/`) reads `feedback.json`
    via a relative path under the same dir.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    feedback_path = out_dir / "feedback.json"
    report_path.write_text(_render_markdown(agg, title=title), encoding="utf-8")
    feedback_path.write_text(json.dumps(agg, indent=2, sort_keys=True), encoding="utf-8")
    return report_path, feedback_path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate_report.py",
        description=(
            "Write report.md + feedback.json from aggregate JSON.\n"
            "Use when: you have aggregate metrics and want a human-readable "
            "report alongside the viewer's data file.\n"
            "Hasznalat: van egy aggregalt JSON, es egy emberi olvasasra "
            "alkalmas jelentest + a viewer adatfajljat szeretned generalni."
        ),
    )
    p.add_argument("--aggregate", required=True, help="Path to aggregate JSON.")
    p.add_argument("--out-dir", required=True, help="Output directory.")
    p.add_argument("--title", default="Eval Report", help="Report title.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    agg = json.loads(Path(args.aggregate).read_text(encoding="utf-8"))
    report, feedback = generate_report(agg, out_dir=Path(args.out_dir), title=args.title)
    emit(
        f"Report written: {report} + {feedback.name}",
        f"Jelentés írva: {report} + {feedback.name}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
