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

@test "install-profiles: end-to-end --help behaviour" {
    run ./scripts/easter-hermes-sorry-skills-install-profiles.sh --help
    if [ -f "./dist/easter-hermes-sorry-skills.pyz" ]; then
        # .pyz exists (local dev / release-mode): wrapper invokes Click
        [ "$status" -eq 0 ]
        [[ "$output" == *"Usage"* ]]
    else
        # No .pyz (CI sandbox / dev-mode hiányzó artifact): wrapper fallback error
        [ "$status" -eq 127 ]
        [[ "$output" == *"No such file or directory"* ]]
    fi
}
