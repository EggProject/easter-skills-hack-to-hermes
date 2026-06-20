"""Diff SHA helper for the patcher atomic-write pipeline.

Split from ``_patcher_apply_atomic`` (WPS202 module surface budget). The
:func:`_diff_sha` helper computes a content-boundary hash that is stable
across equal before/after byte sequences (used to deduplicate audit
entries).
"""

from __future__ import annotations

import hashlib

from hermes_skill_creator_plugin._patcher_apply_atomic import HASH_SEPARATOR


def _diff_sha(before: bytes, after: bytes) -> str:
    """Return the hex SHA-256 of ``HASH_SEPARATOR``-joined ``before`` and ``after``."""
    joined = HASH_SEPARATOR.join([before, after])
    digest = hashlib.sha256(joined).hexdigest()
    return digest
