#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-install-profiles.sh — wrapper around `easter-hermes-sorry-skills-install-profiles` entry point
# See /tmp/hermes-scripts-usage-report.html for Hungarian usage docs.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -x .venv/bin/easter-hermes-sorry-skills-install-profiles ]; then
    exec .venv/bin/easter-hermes-sorry-skills-install-profiles "$@"
elif command -v easter-hermes-sorry-skills-install-profiles >/dev/null 2>&1; then
    exec easter-hermes-sorry-skills-install-profiles "$@"
else
    echo "ERROR: easter-hermes-sorry-skills-install-profiles not found. Run 'uv sync --locked --all-extras --dev' first." >&2
    exit 127
fi