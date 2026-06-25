"""Default remediation text for the apply + drift pipeline (EN/HU).

Lives in its own module so :mod:`._patcher_pipeline_emit` and the
rejected-sidecar writer can share these strings without inlining them
in the orchestrator. Exit codes, state strings, and failure-reason
constants live in :mod:`._patcher_consts` and are imported directly
from there by consumers.
"""

# Default remediation text for line-drift rejected sidecars (EN/HU).
# Phase 7A.5 removed ``--force --i-accept-line-drift``; drift is now terminal.
# Recovery: manually fix the drifted line, then re-run without ``--dry-run``.
REMEDIATION_EN = (
    "Drift is terminal (EXIT_DRIFT). Manually fix the drifted line, then re-run without --dry-run (default writes)."
)
REMEDIATION_HU = (
    "A drift terminális (EXIT_DRIFT). Javítsd manuálisan az eltérő sort, "
    "majd futtasd újra --dry-run nélkül (alap: írás)."
)
