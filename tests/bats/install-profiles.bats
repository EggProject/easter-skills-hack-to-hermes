#!/usr/bin/env bats
# tests/bats/install-profiles.bats — smoke tests for scripts/easter-hermes-sorry-skills-install-profiles.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "install-profiles: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-install-profiles.sh"
    [ "$status" -eq 0 ]
}
