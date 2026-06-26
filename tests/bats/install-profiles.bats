#!/usr/bin/env bats
# tests/bats/install-profiles.bats — smoke tests for scripts/easter-hermes-sorry-skills-install-profiles.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "install-profiles: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-install-profiles.sh"
    [ "$status" -eq 0 ]
}

@test "install-profiles: wrapper uses -c invocation (regression)" {
    run grep -qF 'exec "${PYZ_PATH}" -c' scripts/easter-hermes-sorry-skills-install-profiles.sh
    [ "$status" -eq 0 ]
}

@test "install-profiles: wrapper imports cli_profiles module (regression)" {
    run grep -qF 'from easter_hermes_sorry_skills.cli_profiles import main' scripts/easter-hermes-sorry-skills-install-profiles.sh
    [ "$status" -eq 0 ]
}
