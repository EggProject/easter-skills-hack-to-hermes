#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-report.sh — wrapper around `easter-hermes-sorry-skills-report` entry point
# See /tmp/hermes-scripts-usage-report.html for Hungarian usage docs.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -x .venv/bin/easter-hermes-sorry-skills-report ]; then
    exec .venv/bin/easter-hermes-sorry-skills-report "$@"
elif command -v easter-hermes-sorry-skills-report >/dev/null 2>&1; then
    exec easter-hermes-sorry-skills-report "$@"
else
    echo "ERROR: easter-hermes-sorry-skills-report not found. Run 'uv sync --locked --all-extras --dev' first." >&2
    exit 127
fi
