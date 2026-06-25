#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-patch-hermes.sh — wrapper around `easter-hermes-sorry-skills-patch-hermes` entry point
# See /tmp/hermes-scripts-usage-report.html for Hungarian usage docs.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -x .venv/bin/easter-hermes-sorry-skills-patch-hermes ]; then
    exec .venv/bin/easter-hermes-sorry-skills-patch-hermes "$@"
elif command -v easter-hermes-sorry-skills-patch-hermes >/dev/null 2>&1; then
    exec easter-hermes-sorry-skills-patch-hermes "$@"
else
    echo "ERROR: easter-hermes-sorry-skills-patch-hermes not found. Run 'uv sync --locked --all-extras --dev' first." >&2
    exit 127
fi
