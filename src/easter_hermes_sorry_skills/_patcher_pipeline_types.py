"""Result and bundle types for the patcher pipeline.

Extracted from ``_patcher.py`` so the pipeline sibling modules
(``_patcher_pipeline_apply``, ``_patcher_pipeline_emit``,
``_patcher_pipeline_results``, ``_patcher_pipeline_finalize``,
``_patcher_pipeline_purge``, ``_patcher_pipeline``) can import the
``PatcherResult`` dataclass at top level WITHOUT triggering the
``_patcher`` -> ``_patcher_pipeline`` -> ... -> ``_patcher`` cycle.

Previously every consumer either (a) deferred the ``PatcherResult``
import to runtime via ``from easter_hermes_sorry_skills._patcher
import PatcherResult`` inside the function body, or (b) gated the
import under ``if TYPE_CHECKING:``. Both patterns resolved the symbol
on every hot-path call (runtime imports) or repeated the gating block
in 7 files (TYPE_CHECKING). By moving the dataclass to this leaf
module — which has no outbound dependencies on any ``_patcher*`` module
— top-level imports are safe and resolve exactly once at module load.

The orchestrator (``_patcher.py``) re-exports ``PatcherResult`` as
``PatcherResult = _pipeline_types.PatcherResult`` so the public API
(``from easter_hermes_sorry_skills._patcher import PatcherResult``)
is unchanged for external callers.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path


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
