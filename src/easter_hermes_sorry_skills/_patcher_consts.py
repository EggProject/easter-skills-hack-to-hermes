"""Patcher orchestrator exit codes, state strings, and failure-reason constants.

Extracted from :mod:`._patcher` to keep the orchestrator under
wemake WPS202 (module members <= 7). These are re-exported from
:mod:`._patcher` so existing imports keep working.

See: plans/04-script-1-patch.md (exit code matrix).
"""

from __future__ import annotations

# --- exit codes (per plans/04-script-1-patch.md §Exit code matrix) --------
EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_DRIFT = 2
EXIT_PERMISSION = 3
EXIT_IO = 4
EXIT_USER_ABORT = 5

# State strings used in the ``state`` dict (also referenced in tests).
STATE_MATCHED = "matched"
STATE_PATCHED = "patched"
STATE_DRIFTED = "drifted"

# Failure-reason strings emitted to the rejected sidecar.
REASON_LINE_DRIFT = "LINE_DRIFT"
REASON_TEXT_DRIFT = "TEXT_DRIFT"

# Sentinel placeholder text for missing-file / out-of-range line drift.
MISSING_FILE = "<file missing>"
NOT_FOUND = "<not found>"
OUT_OF_RANGE = "<out of range>"
