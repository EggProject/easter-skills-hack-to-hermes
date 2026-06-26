#!/usr/bin/env bats
# tests/bats/patch-hermes.bats — smoke tests for scripts/easter-hermes-sorry-skills-patch-hermes.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "patch: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-patch-hermes.sh"
    [ "$status" -eq 0 ]
}

@test "patch: wrapper uses -c invocation (regression)" {
    run grep -qF 'exec "${PYZ_PATH}" -c' scripts/easter-hermes-sorry-skills-patch-hermes.sh
    [ "$status" -eq 0 ]
}

@test "patch: wrapper imports cli_patch module (regression)" {
    run grep -qF 'from easter_hermes_sorry_skills.cli_patch import main' scripts/easter-hermes-sorry-skills-patch-hermes.sh
    [ "$status" -eq 0 ]
}

