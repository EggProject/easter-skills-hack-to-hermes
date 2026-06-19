"""State sidecar primitives: load/parse/write of ``.patch.state.json``.

Extracted from ``_patcher_apply.py`` to keep module member count under
wemake's WPS202 threshold. The rejected-sidecar and audit-log
primitives remain in ``_patcher_apply.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hermes_skill_creator_plugin._patcher_apply_atomic import (
    TEXT_ENCODING,
    _atomic_write_bytes,
    _with_newline,
)

STATE_SIDECAR = Path(".patch.state.json")


def _coerce_state(raw: Any) -> dict[str, str]:
    """Coerce a parsed JSON object into a ``str -> str`` mapping."""
    if not isinstance(raw, dict):
        return {}
    return {key_str: str(entry) for key_str, entry in _items_as_strings(raw)}


def _items_as_strings(raw: dict[Any, Any]) -> list[tuple[str, Any]]:
    """Stringify the keys of ``raw`` for the coerce pipeline."""
    return [(str(key), entry) for key, entry in raw.items()]


def load_state(target: Path) -> dict[str, str]:
    """Load ``.patch.state.json``; return empty dict on missing/corrupt."""
    sidecar = target / STATE_SIDECAR
    if not sidecar.exists():
        return {}
    try:
        raw = json.loads(sidecar.read_text(encoding=TEXT_ENCODING))
    except json.JSONDecodeError:
        return {}
    return _coerce_state(raw)


def write_state(target: Path, state: dict[str, str]) -> None:
    """Write ``.patch.state.json`` atomically with sorted keys."""
    sidecar = target / STATE_SIDECAR
    sorted_items = dict(sorted(state.items()))
    payload = json.dumps(sorted_items, indent=2)
    _atomic_write_bytes(sidecar, _with_newline(payload).encode(TEXT_ENCODING))