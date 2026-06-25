#!/usr/bin/env bats
# tests/bats/report.bats — smoke tests for scripts/easter-hermes-sorry-skills-report.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "report: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-report.sh"
    [ "$status" -eq 0 ]
}

@test "report: --help exits 0 and prints usage" {
    run scripts/easter-hermes-sorry-skills-report.sh --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ [Uu]sage ]]
}
