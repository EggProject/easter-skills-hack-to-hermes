#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-patch.sh — wrapper around `easter-hermes-sorry-skills-patch` entry point
# See /tmp/hermes-scripts-usage-report.html for Hungarian usage docs.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -x .venv/bin/easter-hermes-sorry-skills-patch ]; then
    exec .venv/bin/easter-hermes-sorry-skills-patch "$@"
elif command -v easter-hermes-sorry-skills-patch >/dev/null 2>&1; then
    exec easter-hermes-sorry-skills-patch "$@"
else
    echo "ERROR: easter-hermes-sorry-skills-patch not found. Run 'uv sync --locked --all-extras --dev' first." >&2
    exit 127
fi
