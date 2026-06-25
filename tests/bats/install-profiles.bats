#!/usr/bin/env bats
# tests/bats/install-profiles.bats — smoke tests for scripts/easter-hermes-sorry-skills-install-profiles.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "install-profiles: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-install-profiles.sh"
    [ "$status" -eq 0 ]
}

@test "install-profiles: --help exits 0 and prints usage" {
    run scripts/easter-hermes-sorry-skills-install-profiles.sh --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ [Uu]sage ]]
}
