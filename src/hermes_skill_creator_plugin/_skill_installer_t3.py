"""Skill installer T3 inventory — per-binding replacement table.

Extracted from :mod:`.skill_installer` to keep the installer under
wemake WPS202 (module members <= 7). The 18-row table is built via the
private row builder and consumed by the installer's migration-note
renderer.

Reference: docs/plans/07-skill-creator-migration.md.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._skill_installer_consts import (
    KEY_CLAUDE,
    KEY_HERMES,
    KEY_ID,
    KEY_LOCATION,
)


def _build_t3_row(
    row_id: str,
    location: str,
    claude: str,
    hermes: str,
) -> dict[str, str]:
    return {
        KEY_ID: row_id,
        KEY_LOCATION: location,
        KEY_CLAUDE: claude,
        KEY_HERMES: hermes,
    }


# T3 inventory — per-binding replacement table (docs/plans/07).
# 18 rows. Each row: (location, claude-binding, hermes-binding, test-id).
T3_INVENTORY: list[dict[str, str]] = [
    _build_t3_row(
        "T3.001",
        "scripts/improve_description.py | main entry",
        "claude -p",
        "hermes -p",
    ),
    _build_t3_row(
        "T3.002",
        "scripts/improve_description.py | env-strip block",
        "os.environ minus CLAUDECODE",
        "hermes_subprocess_env()",
    ),
    _build_t3_row(
        "T3.003",
        "scripts/run_eval.py | invocation",
        "claude -p --output-format stream-json --verbose",
        "hermes -p --output-format stream-json --verbose",
    ),
    _build_t3_row(
        "T3.004",
        "scripts/run_eval.py | env-strip",
        "os.environ.pop('CLAUDECODE', None)",
        "hermes_subprocess_env()",
    ),
    _build_t3_row(
        "T3.005",
        "scripts/run_eval.py | commands path",
        ".claude/commands/<target>.md",
        "~/.hermes/skills/<cat>/<target>/SKILL.md",
    ),
    _build_t3_row(
        "T3.006",
        "scripts/run_eval.py | --model arg",
        "--model claude-...",
        "--model hermes-... (or omit)",
    ),
    _build_t3_row(
        "T3.007",
        "SKILL.md | claude.ai link",
        "claude.ai URL",
        "nousresearch.com/hermes (or remove)",
    ),
    _build_t3_row(
        "T3.008",
        "SKILL.md | Cowork section",
        "Cowork-specific section",
        "removed",
    ),
    _build_t3_row(
        "T3.009",
        "SKILL.md | Cowork fallback",
        "Cowork fallback",
        "removed",
    ),
    _build_t3_row(
        "T3.010",
        "SKILL.md | webbrowser open",
        "if not webbrowser.open(...)",
        "removed",
    ),
    _build_t3_row(
        "T3.011",
        "scripts/run_eval.py | NDJSON parse",
        "Anthropic {type, message:{content:[{type,text}]}}",
        "Hermes {event, role, content} (via adapter)",
    ),
    _build_t3_row(
        "T3.012",
        "agents/grader.md",
        "Anthropic subagent YAML",
        "Hermes agent_name registration",
    ),
    _build_t3_row(
        "T3.013",
        "agents/analyzer.md",
        "Anthropic subagent YAML",
        "Hermes agent_name registration",
    ),
    _build_t3_row(
        "T3.014",
        "agents/comparator.md",
        "Anthropic subagent YAML",
        "Hermes agent_name registration",
    ),
    _build_t3_row(
        "T3.015",
        "eval-viewer/generate_review.py",
        "(host-agnostic; no Claude binding)",
        "preserved unchanged (stdlib HTTP server)",
    ),
    _build_t3_row(
        "T3.016",
        "scripts/run_loop.py",
        "module docstring references claude -p",
        "module docstring references hermes -p",
    ),
    _build_t3_row(
        "T3.017",
        "scripts/run_loop.py",
        "any other claude/CLAUDECODE invocations",
        "replaced per Hermes equivalent",
    ),
    _build_t3_row(
        "T3.018",
        "scripts/improve_description.py",
        'RuntimeError(f"claude -p exited {rc}")',
        'RuntimeError(f"hermes -p exited {rc}")',
    ),
]

__all__ = [
    "T3_INVENTORY",
]