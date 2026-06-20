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

# Re-export moved symbols (WPS202 module split) for backward-compatible imports.
