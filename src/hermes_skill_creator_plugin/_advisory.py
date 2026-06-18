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


def resolve_target_dir() -> Path:
    """Return the Hermes checkout to inspect.

    Honors HERMES_HERMES_AGENT_TARGET (set by Script #1 + CI). Falls back to
    ~/.hermes/hermes-agent ONLY in interactive operator use; CI must always
    set the env var to avoid the live read.
    """
    env = os.environ.get("HERMES_HERMES_AGENT_TARGET")
    if env:
        return Path(env)
    return Path(os.path.expanduser("~/.hermes/hermes-agent"))


def detect_cap_state(target_dir: Path) -> str:
    """Return one of: 'patched', 'unpatched', 'unknown'.

    target_dir: a USER-OWNED Hermes checkout (NOT ~/.hermes/hermes-agent
    in CI). Reads agent/skill_utils.py with ast.parse; inspects the
    extract_skill_description function for the literal '60' or the
    MAX_DESCRIPTION_LENGTH reference.
    """
    skill_utils = target_dir / "agent" / "skill_utils.py"
    if not skill_utils.exists():
        return UNKNOWN_STATE
    state = _read_and_parse(skill_utils)
    if state is None:
        return UNKNOWN_STATE
    return state


def _read_and_parse(skill_utils: Path) -> str | None:
    """Read and parse ``skill_utils``; return its cap state or ``None``."""
    try:
        source = skill_utils.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return None
    return _walk_tree_for_marker(tree)


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
        is_constant = isinstance(comparator, ast.Constant)
        is_name = isinstance(comparator, ast.Name)
        if is_constant and comparator.value == UNPATCHED_CAP:
            return UNPATCHED_STATE
        if is_name and comparator.id == PATCHED_CAP_REFERENCE:
            return PATCHED_STATE
    return None


def should_emit_advisory(advisory_marker: Path) -> bool:
    """Return True iff the advisory marker is absent (one-time semantics)."""
    return not advisory_marker.exists()


def emit_advisory(advisory_marker: Path) -> None:
    """Best-effort write of the one-time marker. Never raises."""
    try:
        advisory_marker.write_text(
            "advisory shown\n",
            encoding="utf-8",
        )
    except OSError:
        # Best-effort: the marker is advisory, not a hard contract.
        return
