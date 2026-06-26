#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-patch-hermes.sh — transparent wrapper around the .pyz entry point
# See README.md "Release build" section for how to build the .pyz.
set -euo pipefail

# --- .pyz path feloldása (dev-mode VAGY release-mode) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${SCRIPT_DIR}/../dist/easter-hermes-sorry-skills.pyz" ]; then
    PYZ_PATH="${SCRIPT_DIR}/../dist/easter-hermes-sorry-skills.pyz"
elif [ -f "${SCRIPT_DIR}/dist/easter-hermes-sorry-skills.pyz" ]; then
    PYZ_PATH="${SCRIPT_DIR}/dist/easter-hermes-sorry-skills.pyz"
elif [ -f "./dist/easter-hermes-sorry-skills.pyz" ]; then
    PYZ_PATH="./dist/easter-hermes-sorry-skills.pyz"
else
    echo "ERROR: dist/easter-hermes-sorry-skills.pyz: No such file or directory" >&2
    exit 127
fi

exec "${PYZ_PATH}" -c "import sys; sys.argv[0] = 'easter-hermes-sorry-skills-patch-hermes'; from easter_hermes_sorry_skills.cli_patch import main; main(standalone_mode=True)" "$@"
