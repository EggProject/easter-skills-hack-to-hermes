# WOW Skills Plugin Hook Flowcharts

This document describes only the plugin hook behavior added by the adaptive
WOW skills feature. It does not cover release, CI, packaging, or the Hermes
core patcher.

The plugin registers two Hermes hooks:

- `on_session_start` keeps the existing advisory hook registered.
- `pre_llm_call` optionally injects a short, ephemeral skill reminder into the
  current user-message context.

## Hook Registration

```mermaid
flowchart TD
    A["Hermes loads plugin"] --> B["register(ctx) runs"]
    B --> C["Check current Hermes target cap state"]
    C --> D{"Cap patch still missing?"}
    D -->|"yes"| E["Log advisory through ctx.log"]
    D -->|"no"| F["Skip advisory log"]
    E --> G["Register on_session_start hook"]
    F --> G
    G --> H["Register pre_llm_call hook"]
    H --> I["Return from register(ctx)"]
```

The plugin does not call `ctx.register_skill`. Skill discovery stays inside
Hermes; this plugin only adds hook callbacks.

## `on_session_start` Hook

```mermaid
flowchart TD
    A["Hermes starts a session"] --> B["Invoke on_session_start callback"]
    B --> C["Callback is intentionally a no-op"]
    C --> D["Session continues normally"]
```

The advisory check happens during `register(ctx)`. The session-start callback
exists so Hermes sees the hook declared by the plugin, but it does not mutate
conversation state.

## `pre_llm_call` Hook

```mermaid
flowchart TD
    A["Hermes is about to call the LLM"] --> B["Invoke plugin pre_llm_call"]
    B --> C["Load skill_hook config"]
    C --> D{"Hook enabled and mode allows this turn?"}
    D -->|"no"| E["Return None"]
    D -->|"yes"| F{"user_message is non-empty?"}
    F -->|"no"| E
    F -->|"yes"| G["Call Hermes skills_list tool API"]
    G --> H{"API response usable?"}
    H -->|"no"| I["Use empty skill list"]
    H -->|"yes"| J["Normalize enabled skill metadata"]
    I --> K["Match current user message"]
    J --> K
    K --> L{"Any match reaches min_score?"}
    L -->|"no"| E
    L -->|"yes"| Q["Scan conversation_history for already loaded skills"]
    Q --> R["Split matches into new and already loaded"]
    R --> M["Render bounded skill reminder"]
    M --> N{"Rendered context exists?"}
    N -->|"no"| E
    N -->|"yes"| O["Return {context: rendered_text}"]
    O --> P["Hermes appends context to current user message"]
```

The returned context is ephemeral. It is not a system prompt patch and it does
not load full `SKILL.md` bodies. If a matching skill was already loaded through
`skill_view` or a Hermes skill slash command, the plugin renders only a weak
"already loaded" reminder instead of recommending another main `skill_view`
call.

## Mode Decision

```mermaid
flowchart TD
    A["Read skill_hook.enabled"] --> B{"enabled is false?"}
    B -->|"yes"| C["Skip injection"]
    B -->|"no"| D["Read skill_hook.mode"]
    D --> E{"mode value"}
    E -->|"off"| C
    E -->|"first"| F{"is_first_turn is true?"}
    F -->|"no"| C
    F -->|"yes"| G["Run matching pipeline"]
    E -->|"adaptive"| G
    G --> H{"Relevant skill match exists?"}
    H -->|"no"| C
    H -->|"yes"| I["Check current conversation_history"]
    I --> J{"Was a matched skill already loaded?"}
    J -->|"no"| K["Inject normal skill_view reminder"]
    J -->|"yes"| L["Inject weak already-loaded reminder"]
```

`first` and `adaptive` both use the same matcher. `first` only permits the
matcher on the first turn.

## Fail-open Path

```mermaid
flowchart TD
    A["pre_llm_call wrapper"] --> B{"Unexpected exception?"}
    B -->|"no"| C["Return context or None"]
    B -->|"yes"| D["Log warning without full user prompt"]
    D --> E["Return None"]
    E --> F["Hermes turn continues without plugin context"]
```

A broken hook must not break the agent turn.

## Chat Example 1: Adaptive Match Injects Context

Config:

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
  entries:
    easter-hermes-sorry-skills-plugin:
      skill_hook:
        enabled: true
        mode: adaptive
        output: shortlist
        top_k: 3
        min_score: 2
```

Enabled skill metadata returned by Hermes `skills_list()`:

```json
{
  "success": true,
  "skills": [
    {
      "name": "skill-creator",
      "description": "Use when creating or improving SKILL.md instructions.",
      "category": "skills"
    },
    {
      "name": "code-review",
      "description": "Use when reviewing code changes for bugs and regressions.",
      "category": "coding"
    }
  ]
}
```

Conversation before the LLM call:

```text
User:
Create a new Hermes skill for reviewing Python CLI changes.
```

Plugin decision:

- `mode=adaptive` allows this turn.
- `user_message` is non-empty.
- `skills_list()` succeeds.
- `skill-creator` matches through description tokens: `skill`, `creating`.
- `code-review` matches through description/category tokens:
  `reviewing`, `code`, `changes`.
- At least one match reaches `min_score`.

Context returned by the plugin:

```text
Relevant Hermes skills to consider:
- code-review: Use when reviewing code changes for bugs and regressions.
- skill-creator: Use when creating or improving SKILL.md instructions.

Use skill_view(name) only if the current task actually matches.
```

What Hermes sends into the current LLM call conceptually:

```text
User:
Create a new Hermes skill for reviewing Python CLI changes.

[Plugin context]
Relevant Hermes skills to consider:
- code-review: Use when reviewing code changes for bugs and regressions.
- skill-creator: Use when creating or improving SKILL.md instructions.

Use skill_view(name) only if the current task actually matches.
```

Expected model behavior:

```text
Assistant:
I should inspect the relevant skill before drafting this. Calling
skill_view(name="skill-creator") is appropriate because the user is asking to
create a skill.
```

## Chat Example 2: Already Loaded Skill Gets Weak Reminder

Config is the same as Example 1.

Conversation before the current LLM call:

```text
User:
Review this Python CLI patch.

Assistant tool call:
skill_view(name="code-review")

Tool result:
{
  "success": true,
  "name": "code-review",
  "content": "...full SKILL.md instructions..."
}

Assistant:
I loaded the code-review skill and will use it for the review.

User:
Now review the updated tests too.
```

Plugin decision on the second user turn:

- `mode=adaptive` allows this turn.
- `skills_list()` succeeds.
- `code-review` still matches the current user message.
- `conversation_history` shows a successful main `skill_view(name="code-review")`
  result.
- The match is treated as already loaded.

Context returned by the plugin:

```text
Already loaded relevant Hermes skills:
- code-review

Follow already loaded skill instructions; call skill_view(name) again only for linked files.
```

What Hermes sends into the current LLM call conceptually:

```text
User:
Now review the updated tests too.

[Plugin context]
Already loaded relevant Hermes skills:
- code-review

Follow already loaded skill instructions; call skill_view(name) again only for linked files.
```

Expected model behavior:

```text
Assistant:
Continue using the already loaded code-review instructions. Do not reload the
main skill content unless a linked reference file is needed.
```

## Chat Example 3: No Match Means No Context

Config is the same as Example 1.

Conversation before the LLM call:

```text
User:
What time is it in Budapest?
```

Plugin decision:

- `mode=adaptive` allows evaluation.
- `skills_list()` succeeds.
- No enabled skill metadata overlaps strongly with the user request.
- No match reaches `min_score`.

Plugin return value:

```text
None
```

What Hermes sends into the current LLM call conceptually:

```text
User:
What time is it in Budapest?
```

Expected model behavior:

```text
Assistant:
Answer normally. No skill reminder was injected, so there is no extra recency
pressure to call skill_view.
```

## Chat Example 4: `first` Mode Skips Later Turns

Config:

```yaml
plugins:
  entries:
    easter-hermes-sorry-skills-plugin:
      skill_hook:
        enabled: true
        mode: first
        output: names
```

Turn 1:

```text
User:
We will work on skill authoring today.
```

Plugin decision:

- `is_first_turn=True`.
- `mode=first` allows the matcher.
- Relevant skill metadata matches.

Possible context:

```text
Relevant Hermes skills to consider:
- skill-creator

Use skill_view(name) only if the current task actually matches.
```

Turn 2:

```text
User:
Now update the draft description.
```

Plugin decision:

- `is_first_turn=False`.
- `mode=first` blocks the hook before calling `skills_list()`.

Plugin return value on turn 2:

```text
None
```

## Chat Example 5: Hook Error Fails Open

Conversation before the LLM call:

```text
User:
Review this plugin change.
```

Runtime condition:

```text
tools.skills_tool.skills_list raises OSError
```

Plugin decision:

- The API adapter catches the error and returns an empty skill list.
- No match can be produced.
- The hook returns `None`.

What Hermes sends into the current LLM call conceptually:

```text
User:
Review this plugin change.
```

Expected model behavior:

```text
Assistant:
Continue normally. The plugin does not break the turn when skill metadata is
unavailable.
```
