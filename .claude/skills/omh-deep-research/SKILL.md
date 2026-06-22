---
name: omh-deep-research
description: Use when the task requires multi-source web research on any topic and you need cited, fact-checked findings before drawing a conclusion. Wraps the minimax MCP web_search tool (`mcp__minimax-mcp-server__web_search`) with a fan-out-then-synthesize workflow. Ideal for fact-finding, library comparisons, current-version checks, and any claim that needs a primary source plus independent confirmation. Do NOT use for trivial lookups or anything answerable from already-loaded context.
license: MIT
allowed-tools: mcp__minimax-mcp-server__web_search
metadata:
  hermes:
    tags: [research, web, search, mcp, minimax]
    related_skills: [deep-research, sequential-thinking]
---

# OMH Deep Research

Multi-source web research harness for Hermes Agent, built on top of the `minimax-mcp-server` `web_search` tool. Produces cited findings rather than un-sourced assertions.

## When to Use

Invoke `omh-deep-research` when:

- A claim must be backed by a **primary source** plus **2 independent confirming links** (project rule).
- The question is about a fast-moving topic (library versions, API behavior, recent releases) and training data may be stale.
- You need to compare multiple options (libraries, tools, services) and want side-by-side evidence.
- A user request explicitly says "research", "look up", "find out", "what is the latest", or asks for citations.

**Don't use for**: trivial single-fact lookups, anything already in this conversation's context, or opinions/preferences.

## Input Contract

The skill accepts one argument: a natural-language research question (string).

Example invocations:

```
/omh-deep-research what is the latest stable release of pydantic as of 2026?
/omh-deep-research compare ruff and wemake-python-styleguide for a uv-based Python project
/omh-deep-research does the minimax MCP web_search tool support date filtering
```

Refine the question before invoking when it is underspecified (missing budget, region, timeframe, or use case). A good research question names the **decision** to be made.

## Output Contract

The synthesized report must include:

1. **Direct answer** — one paragraph that answers the original question.
2. **Evidence table** — markdown table with columns: `claim | source | url | retrieved`.
3. **Confidence** — `high` / `medium` / `low` with a one-line justification.
4. **Unverified claims** — any claim that could not be confirmed by 2 independent sources must be listed explicitly here (per project rule: no 2 confirmations → claim is unverified, surface it instead of asserting).

## The Tool

The Hermes MCP tool `mcp__minimax-mcp-server__web_search` accepts:

- `query` (string, required) — 3-5 keyword search query. Include the current year for time-sensitive topics.

Returns a JSON object:

```json
{
  "organic": [
    {"title": "...", "link": "...", "snippet": "...", "date": "..."}
  ],
  "related_searches": [{"query": "..."}],
  "base_resp": {"status_code": 0, "status_msg": "..."}
}
```

## Workflow: Fan-out then Synthesize

```
1. Decompose the question into 3-5 sub-questions.
2. For each sub-question, issue ONE web_search call.
   - Use 3-5 keywords.
   - Include the current year for time-sensitive facts.
3. From each result set, pick the most authoritative-looking link.
4. For each load-bearing claim, fetch the primary source PLUS 2 independent confirmations
   (per project rule: every claim requires primary source + 2 confirming links).
5. Write the Output Contract above.
6. Mark any unverified claim in the "Unverified claims" section — do NOT bury it.
```

### Invocation Examples

**Single-query (simple lookup)**:

```
Question: "What is the current Python version on 2026-06-22?"

Call:
  mcp__minimax-mcp-server__web_search(query="latest stable Python release 2026")

Output: direct answer + 1-2 source links.
```

**Multi-query fan-out (comparison research)**:

```
Question: "Should I use ruff or wemake-python-styleguide for a uv-based Python project in 2026?"

Sub-queries:
  1. mcp__minimax-mcp-server__web_search(query="ruff 2026 latest stable")
  2. mcp__minimax-mcp-server__web_search(query="wemake-python-styleguide 2026 active maintenance")
  3. mcp__minimax-mcp-server__web_search(query="ruff vs wemake-python-styleguide comparison 2026")
  4. mcp__minimax-mcp-server__web_search(query="uv pre-commit ruff wemake integration")

Synthesize: pick a recommendation backed by 2+ independent sources.
```

**Time-sensitive fact-check**:

```
Question: "Does the minimax MCP web_search tool support a `date` parameter?"

Sub-queries:
  1. mcp__minimax-mcp-server__web_search(query="minimax-coding-plan-mcp web_search parameters")
  2. mcp__minimax-mcp-server__web_search(query="minimax MCP server tools documentation")

Confirm from 2 independent sources before stating "yes" or "no".
```

## Tips

- **3-5 keywords per query.** Longer queries dilute recall; shorter queries lose precision.
- **Include the year** for any version, release-date, or "current best practice" claim.
- **Prefer official sources first** (project docs, GitHub releases, official changelogs).
- **Cross-check dates** — if two sources disagree on a date, surface that explicitly.
- **Do not paraphrase a quote** — quote it verbatim and cite.
- **Stop early if scope blows up** — narrow the question and re-invoke rather than dumping 20 raw results.
