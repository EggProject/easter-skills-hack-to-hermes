#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-patch-hermes.sh — wrapper around .pyz entry point
# See README.md "Release build" section for how to build the .pyz.
set -euo pipefail

# --- Help flag: saját usage kiírása és exit 0 (a .pyz PATH feloldása ELŐTT) ---
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: $(basename "${BASH_SOURCE[0]}") [args...]"
    echo ""
    echo "Wrapper around the easter-hermes-sorry-skills-patch-hermes entry point in dist/easter-hermes-sorry-skills.pyz"
    echo ""
    echo "The .pyz is built by scripts/build-release.sh (see README 'Release build' section)."
    echo "If dist/easter-hermes-sorry-skills.pyz is missing, run scripts/build-release.sh first."
    exit 0
fi

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

exec "${PYZ_PATH}" easter-hermes-sorry-skills-patch-hermes "$@"
