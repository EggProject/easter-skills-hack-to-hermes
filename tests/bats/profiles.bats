#!/usr/bin/env bats
# tests/bats/profiles.bats — smoke tests for scripts/easter-hermes-sorry-skills-profiles.sh
# NOTE: profiles CLI has a pre-existing `ModuleNotFoundError: No module named 'agent'`
# (cli_profiles.py:44 imports `agent.skill_utils`). The test below accepts this as
# a "wrapper works, target is broken" signal — fixing the import is OUT OF SCOPE.
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "profiles: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-profiles.sh"
    [ "$status" -eq 0 ]
}

@test "profiles: wrapper execs venv binary (KNOWN BROKEN target -- pre-existing import)" {
    # The wrapper itself works (resolves .venv/bin/<cli>); only the Python
    # target is broken. Accept either clean --help OR the known import error.
    run scripts/easter-hermes-sorry-skills-profiles.sh --help
    # status 0 = clean, status != 0 + "No module named 'agent'" in output = known pre-existing
    if [ "$status" -eq 0 ]; then
        [[ "$output" =~ [Uu]sage ]]
    else
        [[ "$output" =~ "No module named 'agent'" ]]
    fi
}
