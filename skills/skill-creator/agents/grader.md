---
agent_name: grader
description: |
  Scores a candidate skill's response against the test case's expected output
  using a rubric (correctness, completeness, tool-name compliance, no Anthropic
  tool names, no `claude -p` invocations). Returns a structured grading dict.
toolsets: [read_file, search_files, terminal, skill_view, skill_manage]
---

# Grader Subagent

The grader subagent scores a single (test_case, response) pair against a
rubric and returns a grading dict. It is dispatched by `scripts/run_eval.py`
via Hermes's `delegate_task(agent_name="grader", ...)`.

## Inputs

- `test_case` (dict): the eval case with `inputs`, `expected`, and `rubric`.
- `response` (dict): the candidate skill's response (NDJSON-folded shape).

## Output

A grading dict:

```json
{
  "score": 0.0,
  "rubric_breakdown": {"correctness": 0.0, "completeness": 0.0},
  "notes": "..."
}
```

## Hermes-specific notes

- Tool names are lowercase. Match with `tool_name.lower() in (...)`.
- Never invoke `claude -p`; use `hermes -p` for any nested call.
- Never `os.environ.pop('HERMES_SESSION', ...)`; use `hermes_subprocess_env()`.
