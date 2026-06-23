#!/usr/bin/env bash
# scripts/easter-hermes-sorry-skills-install.sh — wraps the broken venv entry point
# (`.venv/bin/easter-hermes-sorry-skills-install` calls `install()` with no kwargs
# and TypeErrors). The wrapper synthesizes the required kwargs via `uv run --locked python`
# with argv passing (heredoc + sys.argv) — NO shell interpolation, NO string concat,
# so values containing quotes/semicolons/glob chars are safe.
# See /tmp/hermes-scripts-usage-report.html for Hungarian usage docs.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
SKILL_SOURCE="${SKILL_SOURCE:-skills/skill-creator}"
CAP="${CAP:-}"

exec uv run --locked python - "$SKILL_SOURCE" "$HERMES_HOME" "$CAP" <<'PYEOF'
import sys
from pathlib import Path
from easter_hermes_sorry_skills.skill_installer import install
src, home, cap = sys.argv[1:4]
install(
    skill_source=Path(src),
    hermes_home=Path(home),
    cap=cap or None,
)
PYEOF
