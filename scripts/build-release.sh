#!/usr/bin/env bash
# scripts/build-release.sh — build a release artifact (shiv zipapp + tar.gz)
# See README.md "Release build" section for when to run this.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# --- Argumentumkezelés ---
ONLY_SHIV=0
ONLY_TAR=0
for arg in "$@"; do
    case "${arg}" in
        --only-shiv) ONLY_SHIV=1 ;;
        --only-tar)  ONLY_TAR=1 ;;
        -h|--help)
            echo "Usage: scripts/build-release.sh [--only-shiv] [--only-tar]"
            echo ""
            echo "  --only-shiv  Csak a shiv build (kihagyja a tar.gz csomagolást)"
            echo "  --only-tar   Csak a tar.gz (feltételezi, hogy a .pyz már létezik)"
            exit 0
            ;;
        *) echo "ERROR: ismeretlen argumentum: ${arg}" >&2; exit 2 ;;
    esac
done

# --- Verzió kiolvasása a pyproject.toml-ból ---
VERSION="$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)"
if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: pyproject.toml version is not a valid semver string: '${VERSION}'" >&2
    echo "  Expected format: X.Y.Z (digits + dots only, no shell metacharacters)" >&2
    exit 1
fi
echo ">>> Building easter-hermes-sorry-skills v${VERSION}"

mkdir -p dist/

# --- Lépés 1: uv sync + saját csomag nem-editable telepítése + shiv telepítés ---
if [ "${ONLY_TAR}" = 0 ]; then
    echo ">>> [1/4] uv sync --locked"
    uv sync --locked
    echo ">>> [2/4] uv pip install . --no-editable --reinstall --no-deps + 'shiv>=1.0,<2.0' (build-time tool)"
    uv pip install . --no-editable --reinstall --no-deps
    uv pip install 'shiv>=1.0,<2.0'
fi

# --- Lépés 2: shiv build (.pyz) ---
if [ "${ONLY_TAR}" = 0 ]; then
    PYTHON="$(command -v python3)"
    PY_VERSION="$("${PYTHON}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    SITE_PACKAGES=".venv/lib/python${PY_VERSION}/site-packages"
    SHIV="${PWD}/.venv/bin/shiv"

    if [ ! -x "${SHIV}" ]; then
        echo "ERROR: ${SHIV} not found. A 'shiv' telepítése sikertelen volt (Lépés 2 alpont 1)." >&2
        exit 1
    fi

    echo ">>> [3/4] shiv --site-packages ${SITE_PACKAGES} --python ${PYTHON} --output-file dist/easter-hermes-sorry-skills.pyz --reproducible ."
    "${SHIV}" \
        --site-packages "${SITE_PACKAGES}" \
        --python "${PYTHON}" \
        --output-file "dist/easter-hermes-sorry-skills.pyz" \
        --reproducible \
        --compressed \
        .
fi

# --- Lépés 3: tar.gz csomagolás ---
if [ "${ONLY_SHIV}" = 0 ]; then
    if [ ! -f dist/easter-hermes-sorry-skills.pyz ]; then
        echo "ERROR: dist/easter-hermes-sorry-skills.pyz not found. Run 'scripts/build-release.sh' first (without --only-tar)." >&2
        exit 1
    fi

    TARBALL="dist/easter-hermes-sorry-skills-v${VERSION}.tar.gz"
    echo ">>> [4/4] tar -czf ${TARBALL} dist/easter-hermes-sorry-skills.pyz scripts/ README.md README.hu.md"
    tar -czf "${TARBALL}" \
        dist/easter-hermes-sorry-skills.pyz \
        scripts/build-release.sh \
        scripts/easter-hermes-sorry-skills-install-profiles.sh \
        scripts/easter-hermes-sorry-skills-patch-hermes.sh \
        scripts/easter-hermes-sorry-skills-report.sh \
        README.md \
        README.hu.md

    echo ">>> Artifact contents:"
    tar -tzf "${TARBALL}" | sed 's/^/    /'
fi

# --- Summary ---
echo ">>> Done. Artifacts:"
ls -lh dist/*.pyz dist/*.tar.gz 2>/dev/null | awk '{print "    " $NF " (" $5 ")"}'