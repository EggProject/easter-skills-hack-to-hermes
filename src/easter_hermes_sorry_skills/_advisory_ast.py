"""AST-walker helpers for the cap-state detector.

Extracted from :mod:`._advisory` to keep the parent module under wemake
WPS202 (module members <= 7).
"""

from __future__ import annotations

import ast
from pathlib import Path

# Pin: the cap value in the unpatched agent/skill_utils.py.
UNPATCHED_CAP = 60
# Pin: the shared constant patched in current Hermes.
PATCHED_CAP_REFERENCE = "SKILL_PROMPT_DESC_LIMIT"
_PATCHED_CAP = 1024
# Sentinel return values (public so register() can compare without importing
# leading-underscore names from another module).
PATCHED_STATE = "patched"
UNPATCHED_STATE = "unpatched"
UNKNOWN_STATE = "unknown"

# Target function whose Compare nodes carry the cap marker.
_EXTRACT_FUNC_NAME = "extract_skill_description"


def _parse_skill_utils_tree(skill_utils: Path) -> ast.AST:
    source = skill_utils.read_text(encoding="utf-8")
    return ast.parse(source)


def _walk_tree_for_marker(tree: ast.AST) -> str | None:
    """Walk ``tree`` and return the first matching cap state, if any."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if not isinstance(target, ast.Name) or target.id != PATCHED_CAP_REFERENCE:
                    continue
                if isinstance(node.value, ast.Constant) and node.value.value == _PATCHED_CAP:
                    return PATCHED_STATE
                if isinstance(node.value, ast.Constant) and node.value.value == UNPATCHED_CAP:
                    return UNPATCHED_STATE
                return None
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != _EXTRACT_FUNC_NAME:
            continue
        state = _scan_func_for_marker(node)
        if state is not None:
            return state
    return None


def _scan_func_for_marker(func: ast.FunctionDef) -> str | None:
    """Return the cap state encoded in any Compare inside ``func``."""
    for sub in ast.walk(func):
        if not isinstance(sub, ast.Compare):
            continue
        state = _scan_comparators(sub.comparators)
        if state is not None:
            return state
    return None


def _scan_comparators(comparators: list[ast.expr]) -> str | None:
    """Map a Compare's comparator list to its cap state, or ``None``."""
    for comparator in comparators:
        state = _match_comparator(comparator)
        if state is not None:
            return state
    return None


def _match_comparator(comparator: ast.expr) -> str | None:
    """Return the cap state for one Compare comparator, or ``None``."""
    is_unpatched = isinstance(comparator, ast.Constant) and comparator.value == UNPATCHED_CAP
    if is_unpatched:
        return UNPATCHED_STATE
    is_patched = isinstance(comparator, ast.Name) and comparator.id == PATCHED_CAP_REFERENCE
    if is_patched:
        return PATCHED_STATE
    return None
