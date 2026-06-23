#!/usr/bin/env bats
# tests/bats/install.bats — smoke tests for scripts/easter-hermes-sorry-skills-install.sh
# NOTE: install.sh is a DP2 deviation — it wraps a plain function via
# heredoc + sys.argv (not a click CLI, not a `python -c` string-interp).
# There is no --help. The test asserts the wrapper reaches the
# `uv run --locked python` line and exits non-zero (the install function
# would otherwise write to HERMES_HOME).
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "install: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-install.sh"
    [ "$status" -eq 0 ]
}

@test "install: wrapper reaches uv run python -c and errors out cleanly" {
    # Set HERMES_HOME to a non-existent dir; the install function will raise
    # FileNotFoundError or similar. We assert the wrapper exits non-zero
    # AND the error message contains either "uv" or the install function's
    # expected error, NOT a "command not found" (which would mean the wrapper
    # failed to resolve the venv binary).
    HOME=/tmp HERMES_HOME=/nonexistent SKILL_SOURCE=skills/skill-creator \
        run scripts/easter-hermes-sorry-skills-install.sh
    [ "$status" -ne 0 ]
    [[ "$output" =~ (FileNotFoundError|does not exist) ]]
}
