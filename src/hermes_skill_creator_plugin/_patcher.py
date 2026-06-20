"""Script #1 patcher orchestrator: cap-raise + opt-in Task E sites.

Idempotent, all-or-nothing patcher for a user-owned Hermes checkout.
This module is the ORCHESTRATOR; the site table, the apply-side
primitives, the migration note renderer, and the pure-function
helpers live in sibling modules to keep each file under the 500-line
hard cap (plans/10 D1):

- :mod:`._patcher_sites` — Site dataclass, the S1.cap two-anchor
  atomic pair, the 7 Task E sites, and the shared
  ``SKILL_CREATOR_CONSULT_RULE`` constant.
- :mod:`._patcher_apply` — atomic write (``<file>.patch.tmp`` +
  ``os.replace``), the state / rejected / audit sidecars.
- :mod:`._patcher_migration` — ``MIGRATION.hermes-patch.md`` and
  ``MIGRATION.md`` rendering.
- :mod:`._patcher_helpers` — pure-function helpers (anchor locator,
  circular-import pre-flight, cross-FS detector, ISO timestamp).
- :mod:`._patcher_consts` — exit codes, state strings, drift reasons.
- :mod:`._patcher_preflight` — refusal-rule preflight.
- :mod:`._patcher_validation` — per-site drift detection.
- :mod:`._patcher_run` — inner driver + circular-import hook.
- :mod:`._patcher_inputs` — :class:`PatchRunInputs` dataclass.

The orchestrator's public API (``run_patch``, ``PatcherResult``, the
``Anchor`` / ``Site`` dataclasses, the site constants, exit codes,
``_atomic_write_bytes`` for tests, ``_render_cap_row`` /
``_render_task_e_row`` for tests) is re-exported from this module so
existing imports (``from hermes_skill_creator_plugin._patcher import
...``) keep working.

The patcher:

1. Refuses to run when ``--target`` resolves to ``~/.hermes/hermes-agent``
   (exit code 4, bilingual diagnostic).
2. Pre-validates every site in a single pass against the file's raw bytes
   (multi-signal targeting: 8+ char anchor + 1-based line number).
3. On a cycle-detection pre-flight against ``agent/skill_utils.py``'s
   existing imports from ``tools.skills_tool``, refuses to write and exits
   with code 4.
4. On validation failure for ANY site, writes a ``.patch.rejected`` JSON
   sidecar and exits non-zero with ZERO bytes touched on the target.
5. On success, performs the atomic-write protocol
   (``<file>.patch.tmp`` + ``os.replace``), preserves file mode bits,
   and updates ``.patch.state.json``.
6. Emits a ``.patch.audit.log`` line on every successful ``--force`` run.

See also: plans/04-script-1-patch.md, plans/05-script-1-task-e-toggle.md,
plans/08-migration-note-format.md, plans/10-toolchain-and-conventions.md,
plans/09-test-strategy.md.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_skill_creator_plugin._patcher_apply import (
    REJECTED_SIDECAR as REJECTED_SIDECAR,
)
from hermes_skill_creator_plugin._patcher_apply import (
    write_rejected as write_rejected,
)

# Re-export moved symbols (WPS202 module split) for backward-compatible imports.
# Use ``as`` aliasing so mypy --strict (no_implicit_reexport) treats each as
# an explicit re-export.
from hermes_skill_creator_plugin._patcher_apply_atomic import _atomic_write_bytes as _atomic_write_bytes
from hermes_skill_creator_plugin._patcher_apply_state import (
    STATE_SIDECAR as STATE_SIDECAR,
)
from hermes_skill_creator_plugin._patcher_apply_state import (
    load_state as load_state,
)
from hermes_skill_creator_plugin._patcher_apply_state import (
    write_state as write_state,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_DRIFT as EXIT_DRIFT,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_IO as EXIT_IO,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_OK as EXIT_OK,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_PERMISSION as EXIT_PERMISSION,
)
from hermes_skill_creator_plugin._patcher_consts import (
    EXIT_USER_ABORT as EXIT_USER_ABORT,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    _cross_filesystem as _cross_filesystem,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    file_has_circular_import as file_has_circular_import,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    hermes_agent_path as hermes_agent_path,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    is_hermes_agent as is_hermes_agent,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    locate_anchor as locate_anchor,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    site_already_patched as site_already_patched,
)
from hermes_skill_creator_plugin._patcher_helpers import (
    site_in_state as site_in_state,
)
from hermes_skill_creator_plugin._patcher_inputs import PatchRunInputs as PatchRunInputs
from hermes_skill_creator_plugin._patcher_migration import (
    generate_migration_note as generate_migration_note,
)
from hermes_skill_creator_plugin._patcher_migration import (
    migration_rows_for_mode as migration_rows_for_mode,
)
from hermes_skill_creator_plugin._patcher_migration_render import _render_cap_row as _render_cap_row
from hermes_skill_creator_plugin._patcher_migration_task_e import _render_task_e_row as _render_task_e_row
from hermes_skill_creator_plugin._patcher_preflight import run_preflight as _run_preflight
from hermes_skill_creator_plugin._patcher_run import (
    _check_circular_import,
    _drive_pipeline,
    _PatchBodyState,
)
from hermes_skill_creator_plugin._patcher_sites import (
    ALL_TASK_E_SITES as ALL_TASK_E_SITES,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E1_SKILLS_GUIDANCE as E1_SKILLS_GUIDANCE,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E2_MEMORY_GUIDANCE as E2_MEMORY_GUIDANCE,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E3_BUILD_SKILLS_PROMPT as E3_BUILD_SKILLS_PROMPT,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E4_SKILL_REVIEW_PROMPT as E4_SKILL_REVIEW_PROMPT,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E5_COMBINED_REVIEW_PROMPT as E5_COMBINED_REVIEW_PROMPT,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E6_SKILL_MANAGE_SCHEMA_DESC as E6_SKILL_MANAGE_SCHEMA_DESC,
)
from hermes_skill_creator_plugin._patcher_sites import (
    E7_SKILLS_DOC_SECTION as E7_SKILLS_DOC_SECTION,
)
from hermes_skill_creator_plugin._patcher_sites import (
    S1_CAP_SITE as S1_CAP_SITE,
)
from hermes_skill_creator_plugin._patcher_sites import (
    SKILL_CREATOR_CONSULT_RULE as SKILL_CREATOR_CONSULT_RULE,
)
from hermes_skill_creator_plugin._patcher_sites import (
    Anchor as Anchor,
)
from hermes_skill_creator_plugin._patcher_sites import (
    Site as Site,
)

if TYPE_CHECKING:
    pass

__all__ = [
    "PatcherResult",
    "PatchRunInputs",
    "ALL_TASK_E_SITES",
    "E1_SKILLS_GUIDANCE",
    "E2_MEMORY_GUIDANCE",
    "E3_BUILD_SKILLS_PROMPT",
    "E4_SKILL_REVIEW_PROMPT",
    "E5_COMBINED_REVIEW_PROMPT",
    "E6_SKILL_MANAGE_SCHEMA_DESC",
    "E7_SKILLS_DOC_SECTION",
    "S1_CAP_SITE",
    "SKILL_CREATOR_CONSULT_RULE",
    "STATE_SIDECAR",
    "REJECTED_SIDECAR",
    "EXIT_OK",
    "EXIT_DRIFT",
    "EXIT_IO",
    "EXIT_PERMISSION",
    "EXIT_USER_ABORT",
    "Anchor",
    "Site",
    "hermes_agent_path",
    "is_hermes_agent",
    "file_has_circular_import",
    "locate_anchor",
    "site_already_patched",
    "site_in_state",
    "_cross_filesystem",
    "_atomic_write_bytes",
    "_render_cap_row",
    "_render_task_e_row",
    "generate_migration_note",
    "migration_rows_for_mode",
    "load_state",
    "write_state",
    "write_rejected",
    "run_patch",
]


@dataclasses.dataclass(frozen=True)
class PatcherResult:
    """Outcome of a patcher run.

    ``exit_code`` follows the matrix in plans/04 (0..5).
    ``sites_patched`` is the list of site_ids touched by THIS run.
    ``sites_already`` is the list of site_ids that were already patched
    BEFORE this run (idempotency).
    ``state`` is the updated ``.patch.state.json`` mapping
    ``{site_id: "matched" | "drifted" | "patched" | "already"}``.
    ``diagnostics`` is the list of bilingual messages emitted.
    """

    exit_code: int
    sites_patched: tuple[str, ...]
    sites_already: tuple[str, ...]
    state: dict[str, str]
    diagnostics: tuple[str, ...]
    rejected_path: Path | None = None


def _empty_result(diagnostics: list[str], exit_code: int) -> PatcherResult:
    """Build a PatcherResult with no sites touched and the given diagnostics."""
    return PatcherResult(
        exit_code=exit_code,
        sites_patched=(),
        sites_already=(),
        state={},
        diagnostics=tuple(diagnostics),
    )


def run_patch(inputs: PatchRunInputs) -> PatcherResult:
    """Run the patcher.

    Returns a :class:`PatcherResult`; the caller (CLI) is responsible
    for translating ``exit_code`` into a ``SystemExit``. This function
    never raises SystemExit; it returns a result.
    """
    state = _PatchBodyState()
    early = _check_preflight(inputs, state)
    if early is not None:
        return early
    assert inputs.target is not None  # narrowed by preflight
    target_path = inputs.target.resolve()
    circular = _check_circular_import(target_path, state)
    if circular is not None:
        return circular
    return _drive_pipeline(inputs, target_path, state)


def _check_preflight(
    inputs: PatchRunInputs,
    state: _PatchBodyState,
) -> PatcherResult | None:
    preflight = _run_preflight(inputs.target, inputs.force, inputs.i_accept_line_drift)
    if preflight is None:
        return None
    return _empty_result([*state.diagnostics, preflight[1]], preflight[0])
