#!/usr/bin/env bash
# mypy_wrapper.sh — runs mypy on B-plugin owned files with MYPYPATH=src.
#
# This wrapper exists because pre-commit-mypy ignores the MYPYPATH env var
# and cannot run with pass_filenames: false + a package name on the CLI
# without a MYPYPATH hint. The wrapper sets MYPYPATH=src explicitly and
# invokes mypy on the two owned files.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Prefer the project venv's mypy; fall back to PATH.
if [[ -x ".venv/bin/mypy" ]]; then
    MYPYPATH=src .venv/bin/mypy --strict --explicit-package-bases \
        src/easter_hermes_sorry_skills/__init__.py \
        src/easter_hermes_sorry_skills/_advisory.py
else
    MYPYPATH=src mypy --strict --explicit-package-bases \
        src/easter_hermes_sorry_skills/__init__.py \
        src/easter_hermes_sorry_skills/_advisory.py
fi
