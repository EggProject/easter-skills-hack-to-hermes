"""Cap-state detection helpers (AST walker) for advisory.

Split from ``_advisory`` (WPS202 module surface budget).
"""

from __future__ import annotations

import ast
from pathlib import Path

from hermes_skill_creator_plugin._advisory_consts import (
    _EXTRACT_FUNC_NAME,
    _SKILL_UTILS_REL_PARTS,
    PATCHED_CAP_REFERENCE,
    PATCHED_STATE,
    UNKNOWN_STATE,
    UNPATCHED_CAP,
    UNPATCHED_STATE,
)


def detect_cap_state(target_dir: Path) -> str:
    """Return one of: 'patched', 'unpatched', 'unknown'.

    target_dir: a USER-OWNED Hermes checkout (NOT ~/.hermes/hermes-agent
    in CI). Reads agent/skill_utils.py with ast.parse; inspects the
    extract_skill_description function for the literal '60' or the
    MAX_DESCRIPTION_LENGTH reference.
    """
    skill_utils = target_dir.joinpath(*_SKILL_UTILS_REL_PARTS)
    if not skill_utils.exists():
        return UNKNOWN_STATE
    try:
        tree = _parse_skill_utils_tree(skill_utils)
    except (OSError, SyntaxError):
        return UNKNOWN_STATE
    state = _walk_tree_for_marker(tree)
    if state is None:
        return UNKNOWN_STATE
    return state


def _parse_skill_utils_tree(skill_utils: Path) -> ast.AST:
    source = skill_utils.read_text(encoding="utf-8")
    return ast.parse(source)


def _walk_tree_for_marker(tree: ast.AST) -> str | None:
    """Walk ``tree`` and return the first matching cap state, if any."""
    for node in ast.walk(tree):
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
