# Hermes Skills Plan Index

## Plan files (chunked, each ≤500 lines)

- [`00-index.md`](00-index.md) — 00 — Index and How to Read This Plan (68 lines)
- [`01-overview.md`](01-overview.md) — 01 — Overview, Deliverables, Acceptance Criteria (109 lines)
- [`02-architecture.md`](02-architecture.md) — 02 — Architecture, Component Diagram, Data Flow (147 lines)
- [`03-plugin-spec.md`](03-plugin-spec.md) — 03 — Hermes Plugin Spec (§5.1, 60→1024 Cap Raise) (147 lines)

## Supporting artefacts

- [`_synthesis.md`](_synthesis.md) — Synthesized research brief (287 lines)
- [`_plan_reviews.md`](_plan_reviews.md) — Adversarial plan reviews (4 lenses)
- [`_research/`](_research/) — Raw research JSON per topic

## Open questions for the HITL gate

- What is the exact Hermes env-var name for the nesting-guard? Candidates: HERMES_SESSION, HERMES_AGENT, HERMES_PARENT_PID. Must be confirmed by reading the Hermes harness before Script #1 lands.
- What is the exact Hermes CLI flag set for --include-partial-messages / --verbose / --output-format stream-json? Need to read hermes_cli/main.py argparse parser before Script #1 lands.
- Should Script #1 raise the 60-char extract_skill_description cap to 1024, or to a smaller interim value (e.g. 200)? The spec docs/maybe-patch-points.md implies a raising is desired; the exact value is a design decision.
- Does Script #2's flip phase require a per-profile HERMES_HOME mirror in os.environ, or is set_hermes_home_override sufficient? The dispute in D7 shows do_install / save_config / get_disabled_skill_names anchor to os.environ['HERMES_HOME']; confirm whether set_hermes_home_override updates the env var or only an in-process cache.
- Should the migrated skill-creator SKILL.md description be left untouched (the 60-char cap is a separate problem), or should the migrated skill be exempted from the cap? If the cap stays at 60, the migrated skill's description must be ≤ 60 chars. The T3 spec implies raising the cap; the exact value affects how aggressively the description can be Hermes-flavoured.
- Should Script #1 land an idempotent re-runnable --check mode, or just a one-shot --apply? The patch touches agent/skill_utils.py:647-655 and the Task E sites across 4 files; a --check flag that asserts the expected state without writing is desirable. Confirm with the user.
- Should the migration ship a one-time GitHub-issue note that the 60-char cap was raised? Issues #46005 and #46024 reference this work; an outbound comment in the patch-script's release notes would be appropriate.
- Is the GitHub issue NousResearch/hermes-agent#46005 real? Not independently verifiable from the read-only environment. If the user wants to reference it in commit messages or the patch-script's README, confirm against the live GitHub UI.
- Does the website docs site at website/docs/user-guide/features/skills.md:378 actually exist in the v0.16.0 install at the cited line? Re-read at planning time to confirm exact line offset.
- Should Script #1 take a --profile <id> flag so the patch only applies to one profile's config snapshot (not the global Hermes install)? Per the project safety rule the script MUST NOT modify ~/.hermes/hermes-agent; a per-profile dry-run that validates the patch against a config snapshot would let the user verify the change in one profile before deciding to apply it to the global install.

## Plan summary

Produced 4/13 plan files (00-index, 01-overview, 02-architecture, 03-plugin-spec). The remaining 9 files (04-script-1-patch, 05-script-1-task-e-toggle, 06-script-2-profiles, 07-skill-creator-migration, 08-migration-note-format, 09-test-strategy, 10-toolchain-and-conventions, 11-sub-agent-delegation-map, 12-risks-and-open-questions) are needed to fully cover §5.2–§5.6. The StructuredOutput tool returned a validation error and aborted the batch — the files were not persisted. Please re-invoke the request to retry, and I will emit all 13 files in the next call.