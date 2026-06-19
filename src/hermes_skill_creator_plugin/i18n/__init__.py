"""Re-export the English i18n strings used by the patcher pipeline.

The patcher pipeline and several other modules import many message
strings from ``i18n.messages_en``. Importing them as ``_i18n.X`` keeps
the wemake WPS235 "too many imported names" cap from triggering
without losing type-checker visibility.
"""

from hermes_skill_creator_plugin.i18n.messages_en import (
    CROSS_FS_WARN,
    FORCE_AUDIT_LOG,
    IO_ERROR,
    LINE_DRIFT,
    OK_ALREADY_PATCHED,
    OK_PATCHED,
    PERMISSION_DENIED,
    TEXT_DRIFT,
    VALIDATION_FAILED,
)

__all__ = [
    "CROSS_FS_WARN",
    "FORCE_AUDIT_LOG",
    "IO_ERROR",
    "LINE_DRIFT",
    "OK_ALREADY_PATCHED",
    "OK_PATCHED",
    "PERMISSION_DENIED",
    "TEXT_DRIFT",
    "VALIDATION_FAILED",
]
