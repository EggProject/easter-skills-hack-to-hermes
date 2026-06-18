---
agent_name: analyzer
description: |
  Post-hoc analyzer that reads the per-case grading dicts produced by the
  grader subagent and produces aggregate metrics (mean, stddev, p50, p95,
  per-rubric breakdown, failure clusters) and a written narrative of
  cross-case patterns.
toolsets: [read_file, search_files, skill_view]
---

# Post-hoc Analyzer Subagent

The analyzer subagent reads the per-case grading dicts produced by the grader
subagent and produces aggregate metrics + a written narrative. Dispatched by
`scripts/aggregate_benchmark.py` via `delegate_task(agent_name="analyzer", ...)`.

## Inputs

- `grading_dicts` (list[dict]): one grading dict per eval case.
- `rubric` (list[str]): the rubric axis names.

## Output

```json
{
  "aggregate": {"mean": 0.0, "stddev": 0.0, "p50": 0.0, "p95": 0.0},
  "per_rubric": {"correctness": 0.0, "completeness": 0.0},
  "failure_clusters": ["..."],
  "narrative": "..."
}
```

## Hermes-specific notes

- Lowercase tool names only.
- Hermes event shape: `{event, role, content}` (translated by the adapter in
  `scripts/run_eval.py`).
