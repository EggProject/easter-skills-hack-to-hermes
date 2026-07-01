# Patch sites

> 📖 [English](patches.md) · [Magyar verzió](patches.hu.md)
> ↩️ [Back to README](../README.md)

Last verified: 2026-06-25 against the canonical site table in `src/easter_hermes_sorry_skills/_patcher_sites_table.py`.

This document enumerates the eight patch sites the Script #1 patcher applies to a user-owned Hermes checkout. It exists so a reviewer can audit *what* gets written and *where*, without re-deriving the targeting rules from the orchestrator.

## Overview

The patcher (`src/easter_hermes_sorry_skills/_patcher.py`) is a one-shot, advisory mutator for a downstream Hermes source tree. It does not modify the skill-creator skill itself; it edits only the user's Hermes checkout at `agent/skill_utils.py`, `agent/prompt_builder.py`, and `agent/background_review.py`.

Operating model:

- One-time advisory: a single `--apply` runs the full site table; nothing is run on Hermes startup or per-invocation.
- All-or-nothing: if any site fails validation, the patcher writes `.patch.rejected` and exits non-zero with zero bytes touched on the target.
- Idempotent: re-running against an already-patched checkout is a no-op (each site has an `expected_replacement` check).
- Multi-signal targeting: every site is located by both an 8+ character physical-line anchor and a 1-based line number. Both must match — a partial match is drift, not a patch.

The patcher always applies the full site table: `S1.cap` (or its fallback) plus all six Task E sites (`E0`, `E1`, `E2`, `E4b`, `E4`, `E5`). There is no opt-out flag.

## Cap raise

The S1 pair replaces two physical lines in `agent/skill_utils.py` that hard-code a 60-character description cap. Skill descriptions longer than 60 characters are silently truncated at runtime, which makes the consulted rule and richer skill descriptions unusable. The replacement uses a local `_MAX_DESCRIPTION_LENGTH = 1024` constant inside the function so `agent/skill_utils.py` stays import-light.

### S1.cap — raise the 60-char cap

- **Site ID:** `S1.cap`
- **Target:** `agent/skill_utils.py` lines 688–689
- **Action:** two-line atomic replace (`kind="cap"`); both anchors must match for the site to count as patched
- **Anchor A (line 688):** `    if len(desc) > 60:`
- **Anchor B (line 689):** `        return desc[:57] + "..."`
- **Replacement:**

  ```python
      _MAX_DESCRIPTION_LENGTH = 1024
      if len(desc) > _MAX_DESCRIPTION_LENGTH:
          return desc[:_MAX_DESCRIPTION_LENGTH - 3] + "..."
  ```

- **Why:** the `60` literal lives deep in the truncation branch; raising it to the same `1024` value used by the tools-layer validators keeps the system prompt index aligned without importing `tools.skills_tool` into Hermes's lightweight `agent/skill_utils.py`.

### S1.cap_fallback — circular-import fallback

- **Site ID:** `S1.cap_fallback`
- **Target:** same file, same anchors (lines 688–689)
- **Action:** compatibility site with the same local-constant replacement as `S1.cap`
- **Trigger:** the pre-flight circular-import detector (`_check_circular_import` in `_patcher_internals.py:74-89`) walks `agent/skill_utils.py`'s existing `from tools.skills_tool import …` chain. If a cycle is detected, the orchestrator swaps `S1.cap` for `S1.cap_fallback` so the patch still proceeds without importing the cross-module `MAX_DESCRIPTION_LENGTH`
- **Why:** keeps the circular-import branch explicit while preserving the same import-free runtime shape as `S1.cap`.

## Prompt-injection sites

The four `E*` sites inject the `SKILL_CREATOR_CONSULT_RULE` constant (or a reference to it) into Hermes's prompt-building path. The constant is the single source of truth for the rule's wording; it is defined once by `E0` and referenced by name everywhere else.

The sites are applied in **descending line order** so that the top-of-file insertions (`E0`, `E4b`) run last and do not shift the higher-line anchors the orchestrator already validated against.

### E0.consult_rule_def

- **Site ID:** `E0.consult_rule_def`
- **Target:** `agent/prompt_builder.py` line 1
- **Action:** append a module-level constant immediately after the L1 docstring anchor (`kind="append"`)
- **Anchor text:** the L1 docstring of `agent/prompt_builder.py`
- **Insertion (verbatim, after the docstring):**

  ```python

  SKILL_CREATOR_CONSULT_RULE = (
      "When creating or editing a skill — use skill-creator. Persist with skill_manage. Small targeted fixes (one-file, < ~20 lines, no schema change) stay patch-first."
  )

  ```

- **Why:** defines the constant at module level in the same file that uses it; E1 and E2 then reference the name without needing an import.

### E1.skills_guidance

- **Site ID:** `E1.skills_guidance`
- **Target:** `agent/prompt_builder.py` line 179
- **Action:** append a single source line directly after the anchor (additive — surrounding literals stay verbatim)
- **Anchor text:** the closing line of an implicit-concat block about skills not being maintained
- **Insertion (one line):**

  ```python
      " " + SKILL_CREATOR_CONSULT_RULE
  ```

- **Why:** surfaces the consult rule inside the skills guidance prompt so the model sees it when picking between skill-creator, skill_manage, and patch-first paths.

### E2.memory_guidance

- **Site ID:** `E2.memory_guidance`
- **Target:** `agent/prompt_builder.py` line 158
- **Action:** append a single source line directly after the anchor
- **Anchor text:** the memory-guidance literal ending with `"necessary later, save it as a skill with the skill tool.\n"`
- **Insertion (one line):**

  ```python
      " " + SKILL_CREATOR_CONSULT_RULE + "\n"
  ```

- **Why:** same prompt-injection goal as `E1`, but inside the memory guidance block — covers prompts that route through memory rather than the skills surface.

## Background-review sites

The `E4b` / `E4` / `E5` triple edits `agent/background_review.py`. `E4b` adds the cross-module import that makes the constant resolvable there; `E4` and `E5` then inject it into the two background-review prompt templates.

### E4b.consult_rule_import

- **Site ID:** `E4b.consult_rule_import`
- **Target:** `agent/background_review.py` line 1
- **Action:** append a single top-of-file import immediately after the L1 docstring
- **Anchor text:** the L1 docstring of `agent/background_review.py`
- **Insertion (one line):**

  ```python
  from agent.prompt_builder import SKILL_CREATOR_CONSULT_RULE
  ```

- **Why:** the constant lives in `agent/prompt_builder.py`; this import is the bridge that lets `E4` and `E5` reference the name in a different module without re-defining it.

### E4.skill_review_prompt_opt4

- **Site ID:** `E4.skill_review_prompt_opt4`
- **Target:** `agent/background_review.py` line 105
- **Action:** append a single source line inside the skill-review prompt template
- **Anchor text:** the closing line of an implicit-concat block about today's task being wrong
- **Insertion (one line):**

  ```python
      SKILL_CREATOR_CONSULT_RULE + "\n\n"
  ```

- **Why:** the `"\n\n"` is a Python string literal (load-bearing — the source must end with the literal `\n\n`, not two actual newlines); it appends the rule to the skill-review prompt with a blank-line separator.

### E5.combined_review_prompt_opt4

- **Site ID:** `E5.combined_review_prompt_opt4`
- **Target:** `agent/background_review.py` line 194
- **Action:** append a single source line inside the combined-review prompt template
- **Anchor text:** the closing line of an implicit-concat block referring back to options (1)/(2)/(3)
- **Insertion (one line):**

  ```python
      SKILL_CREATOR_CONSULT_RULE + "\n\n"
  ```

- **Why:** same prompt-injection goal as `E4`, applied to the combined-review prompt that runs after both skill and memory review pass.

## Apply mechanics

The orchestrator (`_patcher.py:124-255`) follows a fixed pipeline:

1. **Preflight** — refuses to run if `--target` resolves to `~/.hermes/hermes-agent` (the upstream repo), with exit code 4 and a bilingual diagnostic. See `_patcher.py:1-45` for the refusal-rule contract.
2. **Circular-import check** — `file_has_circular_import` (in `_patcher_helpers`) walks the existing import graph of `agent/skill_utils.py`. A detected cycle swaps `S1.cap` for `S1.cap_fallback` (the patch proceeds, the cross-module import is avoided). See `_patcher_internals.py:74-89`.
3. **Per-site validation** — every site is matched against the file's raw bytes using the multi-signal anchor (8+ chars + 1-based line). A mismatch is `LINE_DRIFT` or `TEXT_DRIFT` (constants in `_patcher_consts.py:26-27`).
4. **Atomic write** — successful sites are written through `<file>.patch.tmp` + `os.replace` (`_patcher_apply_atomic.py:47-71`). POSIX-atomic on the same filesystem; mode bits are preserved via `os.chmod`. The temp file is unlinked on any exception so the original is left untouched.
5. **State sidecar** — `.patch.state.json` (in `_patcher_apply_state.py`) records which sites are `matched`, `patched`, or `drifted`. The next run reads it to detect already-applied sites.
6. **Rejected sidecar** — `.patch.rejected` (built in `_patcher_apply.py:64-102`) is the bilingual-machine-readable failure record emitted on any drift. It is never written on success.
7. **Audit log** — `~/.hermes/patch-audit.log` (the path comes from `AUDIT_LOG_NAME` in `_patcher_apply.py:42`) is appended only on successful `--force` runs (one line per invocation, with timestamp + combined diff sha256). Normal `--apply` runs do not append.
8. **Cache purge** — after a successful apply, `_patcher_pipeline_purge.py:48-59` deletes `~/.hermes/.skills_prompt_snapshot.json`. The snapshot tracks only `SKILL.md` / `DESCRIPTION.md` mtimes; it does not notice that `prompt_builder.py` was modified by the patcher. A purge forces a cold rebuild on the next Hermes run.

### Exit codes

From `_patcher_consts.py:13-18`:

| Code | Meaning             |
|-----:|---------------------|
|    0 | OK                  |
|    1 | Validation          |
|    2 | Drift               |
|    3 | Permission          |
|    4 | I/O                 |
|    5 | User-abort          |

## Rollback

The patcher is one-shot, but every successful apply writes a durable state sidecar, so rollback is mechanical.

1. **Inspect the state file.** `cat .patch.state.json` next to the patched target lists each site and its current `state` (`matched` / `patched` / `drifted`).
2. **Inspect the audit log.** `~/.hermes/patch-audit.log` records every successful `--force` run with timestamp and diff hash. Combine with `git log` to find the commit that introduced the patched state.
3. **Revert via `git checkout`.** Every patched file is a tracked file in the user's Hermes checkout. `git checkout HEAD -- agent/skill_utils.py agent/prompt_builder.py agent/background_review.py` is the canonical revert; the patcher's anchors are designed to match upstream text, so the revert will not collide with a future re-apply.
4. **Re-apply.** A clean checkout can be re-patched by re-running the patcher; the state sidecar from the rolled-back attempt is overwritten on the next run.

Do **not** hand-edit `.patch.state.json` to "force" a re-apply. The state file is a record, not a switch; `--force` retries drifted sites at apply time and a fresh drift still exits 2 unless the operator manually resolves the underlying drift first (see `_patcher.py:206-210`).
