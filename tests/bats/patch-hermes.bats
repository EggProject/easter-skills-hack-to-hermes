#!/usr/bin/env bats
# tests/bats/patch-hermes.bats — smoke tests for scripts/easter-hermes-sorry-skills-patch-hermes.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "patch: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-patch-hermes.sh"
    [ "$status" -eq 0 ]
}

