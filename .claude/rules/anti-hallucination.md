# Anti-Hallucination Protocol

## Evidence Standard
Evidence = Bash tool output from THIS conversation showing command execution and results.

## NOT Evidence
- "I ran this earlier" (cannot verify)
- "This is a trivial change" (still must verify)
- "Based on my analysis" (show the analysis output)
- Agent claims of "no issues found" (verify independently)

## Mandatory Verification Pipeline
Before claiming any task COMPLETE:

1. run all lint

If ANY command was not run in THIS conversation: STOP. Run it NOW.

## Cross-Reference Rule
- Do not trust agent claims without independent verification
- The Stop hook provides a deterministic safety net
- The code-verifier pipeline step provides an independent verification after task-executor

## Proof-Based Completion
When reporting task completion, include:
- Exact command output (not paraphrased)
- File paths that were modified
- Test results with pass/fail counts
