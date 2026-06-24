"""Constants for the apply + drift pipeline.

Mirrors the ``_patcher.EXIT_*`` codes and the ``state["<site>"]`` values.
Lives in its own module to keep ``_patcher_pipeline`` under the
wemake WPS202 member-count cap.
"""

# State strings used in the ``state`` dict (mirrored in ``_patcher``).
STATE_PATCHED = "patched"
STATE_DRIFTED = "drifted"

# Failure-reason strings emitted to the rejected sidecar.
REASON_LINE_DRIFT = "LINE_DRIFT"

# Exit-code constants used in the ``_apply_one_site`` IO-error branch.
# (Mirrors ``_patcher.EXIT_PERMISSION`` / ``_patcher.EXIT_IO``.)
EXIT_PERMISSION = 3
EXIT_IO = 4

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
