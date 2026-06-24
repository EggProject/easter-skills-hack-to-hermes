"""Constants for the apply + drift pipeline.

Mirrors the ``_patcher.EXIT_*`` codes and the ``state["<site>"]`` values.
Lives in its own module to keep ``_patcher_pipeline`` under the
wemake WPS202 member-count cap.
"""

from easter_hermes_sorry_skills._patcher_consts import (
    EXIT_IO as _EXIT_IO_SRC,
)
from easter_hermes_sorry_skills._patcher_consts import (
    EXIT_PERMISSION as _EXIT_PERMISSION_SRC,
)
from easter_hermes_sorry_skills._patcher_consts import (
    REASON_LINE_DRIFT as _REASON_LINE_DRIFT_SRC,
)
from easter_hermes_sorry_skills._patcher_consts import (
    STATE_DRIFTED as _STATE_DRIFTED_SRC,
)
from easter_hermes_sorry_skills._patcher_consts import (
    STATE_PATCHED as _STATE_PATCHED_SRC,
)

# Re-bind under the canonical public name so this module stays the
# public re-export surface for the apply/drift pipeline. The ``_SRC``
# suffix on the import above sidesteps pyflakes F401 (pyflakes does not
# treat ``X = X`` self-rename as a use of ``X``).
EXIT_IO = _EXIT_IO_SRC
EXIT_PERMISSION = _EXIT_PERMISSION_SRC
REASON_LINE_DRIFT = _REASON_LINE_DRIFT_SRC
STATE_DRIFTED = _STATE_DRIFTED_SRC
STATE_PATCHED = _STATE_PATCHED_SRC

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
