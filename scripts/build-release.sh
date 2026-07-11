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

    RELEASE_NAME="easter-hermes-sorry-skills-v${VERSION}"
    TARBALL="dist/easter-hermes-sorry-skills-v${VERSION}.tar.gz"
    STAGE_DIR="$(mktemp -d)"
    RELEASE_ROOT="${STAGE_DIR}/${RELEASE_NAME}"
    PLUGIN_DIR="${RELEASE_ROOT}/plugin/easter-hermes-sorry-skills-plugin"

    mkdir -p \
        "${RELEASE_ROOT}/dist" \
        "${RELEASE_ROOT}/scripts" \
        "${RELEASE_ROOT}/skills" \
        "${PLUGIN_DIR}"

    cp dist/easter-hermes-sorry-skills.pyz "${RELEASE_ROOT}/dist/"
    cp scripts/build-release.sh "${RELEASE_ROOT}/scripts/"
    cp scripts/easter-hermes-sorry-skills-patch-hermes.sh "${RELEASE_ROOT}/scripts/"
    cp scripts/easter-hermes-sorry-skills-report.sh "${RELEASE_ROOT}/scripts/"
    cp README.md README.hu.md "${RELEASE_ROOT}/"
    cp -R skills/skill-creator "${RELEASE_ROOT}/skills/skill-creator"
    cp src/easter_hermes_sorry_skills/plugin.yaml "${PLUGIN_DIR}/plugin.yaml"
    cp -R src/easter_hermes_sorry_skills "${PLUGIN_DIR}/easter_hermes_sorry_skills"
    find "${PLUGIN_DIR}/easter_hermes_sorry_skills" -type d -name '__pycache__' -prune -exec rm -rf {} +
    find "${PLUGIN_DIR}/easter_hermes_sorry_skills" -type f -name '*.pyc' -delete
    cat > "${PLUGIN_DIR}/__init__.py" <<'PY'
"""Hermes directory plugin entry point for release installs."""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = str(Path(__file__).resolve().parent)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from easter_hermes_sorry_skills._register import register as register
PY

    echo ">>> [4/4] tar -czf ${TARBALL} -C ${STAGE_DIR} ${RELEASE_NAME}"
    tar -czf "${TARBALL}" -C "${STAGE_DIR}" "${RELEASE_NAME}"
    rm -rf "${STAGE_DIR}"

    echo ">>> Artifact contents:"
    tar -tzf "${TARBALL}" | sed 's/^/    /'
fi

# --- Summary ---
echo ">>> Done. Artifacts:"
ls -lh dist/*.pyz dist/*.tar.gz 2>/dev/null | awk '{print "    " $NF " (" $5 ")"}'
