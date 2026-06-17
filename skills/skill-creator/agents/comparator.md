---
agent_name: comparator
description: |
  Blind comparator that reads two responses (A and B) without knowing which is
  the candidate vs the baseline, and judges which better satisfies the test
  case's expected output. Returns a verdict (A / B / tie) and reasoning.
toolsets: [read_file, search_files, skill_view]
---

# Blind Comparator Subagent

The blind comparator subagent reads two responses (A, B) without label
information and judges which better satisfies the test case's expected output.
Dispatched by `scripts/aggregate_benchmark.py` via
`delegate_task(agent_name="comparator", ...)`.

## Inputs

- `test_case` (dict): the eval case with `expected` and `rubric`.
- `response_a` (dict): the first response.
- `response_b` (dict): the second response.

## Output

```json
{
  "verdict": "A" | "B" | "tie",
  "reasoning": "..."
}
```

## Hermes-specific notes

- Lowercase tool names only.
- Hermes event shape: `{event, role, content}` (translated by the adapter).
