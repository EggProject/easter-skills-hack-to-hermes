#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-install-profiles.sh — wrapper around .pyz entry point
# See README.md "Release build" section for how to build the .pyz.
set -euo pipefail

# --- .pyz path feloldása (dev-mode VAGY release-mode) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${SCRIPT_DIR}/../dist/easter-hermes-sorry-skills.pyz" ]; then
    # release-mode: a .pyz a scripts/ mappa szülő mappájának dist/-ben van
    PYZ_PATH="${SCRIPT_DIR}/../dist/easter-hermes-sorry-skills.pyz"
elif [ -f "${SCRIPT_DIR}/dist/easter-hermes-sorry-skills.pyz" ]; then
    # dev-mode (ritka): a .pyz a scripts/ mappa melletti dist/-ben van
    PYZ_PATH="${SCRIPT_DIR}/dist/easter-hermes-sorry-skills.pyz"
elif [ -f "./dist/easter-hermes-sorry-skills.pyz" ]; then
    # dev-mode (gyakori): `bash scripts/*.sh` a repo gyökeréből
    PYZ_PATH="./dist/easter-hermes-sorry-skills.pyz"
else
    echo "ERROR: dist/easter-hermes-sorry-skills.pyz not found." >&2
    echo "  Ha release artifact-ot töltöttél le: a dist/ mappa a scripts/ mappa mellett kell legyen." >&2
    echo "  Ha fejlesztő vagy: futtasd a 'scripts/build-release.sh'-t a release artifact építéséhez." >&2
    echo "  Részletek: README.md 'Release build' szekció." >&2
    exit 127
fi

exec "${PYZ_PATH}" easter-hermes-sorry-skills-install-profiles "$@"
