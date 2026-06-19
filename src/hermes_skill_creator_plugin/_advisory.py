"""Static AST-based cap-state detection. NO runtime mutation. NO setattr.

The actual cap-raise is performed by Script #1 against a user-owned Hermes
checkout. This module only DETECTS the cap state; it NEVER mutates the target.

TDD test cases for this module:
    test_detect_cap_state_patched
    test_detect_cap_state_unpatched
    test_detect_cap_state_unknown_no_file
    test_detect_cap_state_unknown_syntax_error
    test_detect_cap_state_no_extract_function
    test_detect_cap_state_other_function_with_60_is_unpatched
    test_resolve_target_dir_prefers_env_var
    test_resolve_target_dir_falls_back_to_default
    test_should_emit_advisory_first_time
    test_should_emit_advisory_after_marker
    test_emit_advisory_writes_marker
    test_emit_advisory_idempotent
    test_emit_advisory_re_emits_when_marker_deleted
    test_emit_advisory_swallows_oserror
    test_advisory_no_setattr_on_skill_utils
    test_advisory_pin_values

See also: docs/plans/03-plugin-spec.md
(Cap-raise mechanism, static-AST, NOT runtime)
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

# Pin: the cap value in the unpatched agent/skill_utils.py.
UNPATCHED_CAP = 60
# Pin: the constant the patched function uses.
PATCHED_CAP_REFERENCE = "MAX_DESCRIPTION_LENGTH"
# Sentinel return values (public so register() can compare without importing
# leading-underscore names from another module).
PATCHED_STATE = "patched"
UNPATCHED_STATE = "unpatched"
UNKNOWN_STATE = "unknown"

# Target function whose Compare nodes carry the cap marker.
_EXTRACT_FUNC_NAME = "extract_skill_description"
_TARGET_ENV_KEY = "HERMES_HERMES_AGENT_TARGET"
_DEFAULT_TARGET_SUFFIX = "~/.hermes/hermes-agent"
_SKILL_UTILS_REL_PARTS = ("agent", "skill_utils.py")
_MARKER_PAYLOAD = "advisory shown\n"


def resolve_target_dir() -> Path:
    """Return the Hermes checkout to inspect.

    Honors HERMES_HERMES_AGENT_TARGET (set by Script #1 + CI). Falls back
    to ~/.hermes/hermes-agent ONLY in interactive operator use; CI must
    always set the env var to avoid the live read.
    """
    env = os.environ.get(_TARGET_ENV_KEY)
    if env:
        return Path(env)
    return Path(os.path.expanduser(_DEFAULT_TARGET_SUFFIX))


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


def should_emit_advisory(advisory_marker: Path) -> bool:
    """Return True iff the advisory marker is absent (one-time semantics)."""
    return not advisory_marker.exists()


def emit_advisory(advisory_marker: Path) -> None:
    """Best-effort write of the one-time marker. Never raises."""
    try:
        advisory_marker.write_text(_MARKER_PAYLOAD, encoding="utf-8")
    except OSError:
        # Best-effort: the marker is advisory, not a hard contract.
        return
