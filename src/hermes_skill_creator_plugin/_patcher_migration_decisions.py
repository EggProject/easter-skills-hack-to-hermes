"""Migration-note Decisions section (D1, D2, D5, D6).

Shared by all three MIGRATION*.md renderers
(``_patcher_migration_body``, ``_patcher_migration_index``,
``_skill_installer_note``) so the wording is single-sourced and the
E501 line-length / WPS202 module-member thresholds stay in spec.

Three slight variants exist (patch / index / skill-port) — see
08-migration-note-format.md §Decisions.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._patcher_migration_consts import LF

D1 = (
    "**D1. MIGRATION is a 3-file split** — top-level index + Script #1 patches "
    "+ migrated-skill T3 inventory; each file serves a different audience "
    "(see 08-migration-note-format.md §Decisions)."
)
D2_TBD = (
    "**D2. Pinned upstream commit `2a40fd2e...` is TBD until verified** — the "
    "generator emits `TBD` and the manifest sha is recomputed on each "
    "regeneration until a WebFetch re-verifies the SHA "
    "(see 08-migration-note-format.md §Decisions)."
)
D2_PINNED = (
    "**D2. Pinned upstream commit `2a40fd2e...` is TBD until verified** — the "
    "generator emits the SHA from `PINNED_UPSTREAM_COMMIT` (vendored source); "
    "the manifest sha is recomputed on each regeneration until a WebFetch "
    "re-verifies the GitHub SHA (see 08-migration-note-format.md §Decisions)."
)
D5_PATCH = (
    "**D5. Row counts are computed at runtime from the sites table** — 1 "
    "(default), 1+7=8 with `--task-e-redirect`, 1+6=7 with "
    "`--task-e-redirect --no-schema-redirect`; T3 row count == 18 "
    "(see 08-migration-note-format.md §Decisions)."
)
D5_SKILL_PORT = (
    "**D5. Row counts are computed at runtime from the sites table** — T3 row "
    "count == 18 (the number of rows in 07-skill-creator-migration.md's T3 "
    "inventory), enforced by `test_migration_note_exhaustive_skill_port` "
    "(see 08-migration-note-format.md §Decisions)."
)
_D6_HEAD = (
    "**D6. Determinism: frozen timestamp + LF endings + no trailing "
    "whitespace** — `HERMES_SKILL_CREATOR_FROZEN_TIME` makes `Generated at` "
    "stable across runs (CI always sets it); tables sorted by "
)


def _d6(sort_label: str) -> str:
    return f"{_D6_HEAD}{sort_label} (see 08-migration-note-format.md §Decisions)."


def render(lines: list[str]) -> str:
    """Render a Decisions section with heading and LF separators."""
    return f"{LF}## Decisions{LF}{LF}{LF.join(lines)}{LF}"


def patch_decisions() -> str:
    """Decisions section for ``MIGRATION.hermes-patch.md``."""
    body = [D1, D2_TBD, D5_PATCH, _d6("`site_id`")]
    return render(body)


def index_decisions() -> str:
    """Decisions section for ``MIGRATION.md`` (top-level index)."""
    body = [D1, D2_TBD, D5_PATCH, _d6("`site_id` (patch) / row number (skill-port)")]
    return render(body)


def skill_port_decisions_lines() -> list[str]:
    """Decisions section for ``MIGRATION.skill-port.md`` as a list of lines."""
    return ["## Decisions", "", D1, D2_PINNED, D5_SKILL_PORT, _d6("row number")]
