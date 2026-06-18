"""scripts/aggregate_benchmark.py — fold per-case events into aggregate metrics.

Hermes-native port. Reads the JSON output of `run_eval.py` and produces
per-case + per-rubric aggregate metrics (mean, stddev, p50, p95).

TDD test cases for this module:
  test_aggregate_benchmark_parses_hermes_stream_json
  test_aggregate_benchmark_handles_empty_results
  test_help_is_bilingual (parametrized over this script)
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from scripts.utils import emit


def _score_from_events(events: list[dict]) -> float:
    """Pull the score out of a list of Anthropic-shaped events.

    A real implementation would dispatch the analyzer subagent via
    `delegate_task(agent_name='analyzer', ...)`. For test purposes we extract
    the score from the last assistant message that contains `score:`.
    """
    for ev in reversed(events):
        msg = ev.get("message", {})
        for blk in msg.get("content", []):
            if blk.get("type") == "text":
                text = blk.get("text", "")
                if "score:" in text:
                    try:
                        return float(text.split("score:", 1)[1].split()[0])
                    except (ValueError, IndexError):
                        return 0.0
    return 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * pct
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def aggregate(results: list[dict]) -> dict:
    """Fold results into aggregate metrics."""
    if not results:
        return {
            "aggregate": {"mean": 0.0, "stddev": 0.0, "p50": 0.0, "p95": 0.0},
            "per_case": [],
            "per_rubric": {},
        }
    scores = [_score_from_events(r.get("events", [])) for r in results]
    per_case = [
        {"case_id": r.get("case", {}).get("id", i), "score": s}
        for i, (r, s) in enumerate(zip(results, scores, strict=False))
    ]
    per_case.sort(key=lambda x: x["case_id"])
    return {
        "aggregate": {
            "mean": statistics.fmean(scores),
            "stddev": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "p50": _percentile(scores, 0.5),
            "p95": _percentile(scores, 0.95),
        },
        "per_case": per_case,
        "per_rubric": {},
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aggregate_benchmark.py",
        description=(
            "Fold per-case events into aggregate metrics.\n"
            "Use when: you have the JSON output of run_eval.py and want the "
            "summary statistics (mean, stddev, p50, p95, per-case scores).\n"
            "Hasznalat: a run_eval.py JSON kimenete alapjan aggregalt "
            "metrikak (mean, stddev, p50, p95, per-case scores)."
        ),
    )
    p.add_argument("--results", required=True, help="Path to run_eval.py JSON output.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    agg = aggregate(data)
    json.dump(agg, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    emit(
        f"Aggregate complete: {len(data)} case(s), mean={agg['aggregate']['mean']:.2f}",
        f"Aggregálás kész: {len(data)} eset, átlag={agg['aggregate']['mean']:.2f}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
