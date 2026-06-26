#!/usr/bin/env bats
# tests/bats/report.bats — smoke tests for scripts/easter-hermes-sorry-skills-report.sh
setup() {
    cd "$(git rev-parse --show-toplevel)"
}

@test "report: script is syntactically valid bash" {
    run bash -n "scripts/easter-hermes-sorry-skills-report.sh"
    [ "$status" -eq 0 ]
}

@test "report: wrapper uses -c invocation (regression)" {
    run grep -qF 'exec "${PYZ_PATH}" -c' scripts/easter-hermes-sorry-skills-report.sh
    [ "$status" -eq 0 ]
}

@test "report: wrapper imports cli_report module (regression)" {
    run grep -qF 'from easter_hermes_sorry_skills.cli_report import main' scripts/easter-hermes-sorry-skills-report.sh
    [ "$status" -eq 0 ]
}
