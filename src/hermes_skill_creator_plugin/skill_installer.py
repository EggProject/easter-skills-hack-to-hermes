"""hermes_skill_creator_plugin.skill_installer — installs the migrated skill-creator.

The installer:
  1. Copies `skills/skill-creator/` (worktree root) into
     `HERMES_HOME/skills/skill-creator/` (flat, top-level deliverable).
  2. Emits `MIGRATION.skill-port.md` (worktree root) from the T3 inventory
     (18 rows; see docs/plans/07-skill-creator-migration.md).

NEVER writes to `~/.hermes/hermes-agent` (the live Hermes install). The
`HERMES_HOME` env var (or `--hermes-home`) selects the target.

TDD test cases for this module:
  test_installer_copies_skill_to_hermes_home_skills_dir
  test_installer_emits_migration_skill_port_md
  test_migration_skill_port_has_18_t3_rows
  test_migration_skill_port_deterministic_under_frozen_time
  test_migration_skill_port_no_claude_invocations_outside_provenance
  test_installer_writes_only_to_hermes_home_and_worktree
  test_installer_refuses_to_write_to_live_hermes_agent
  test_installer_selects_short_or_full_description_per_active_cap
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# T3 inventory — per-binding replacement table (docs/plans/07).
# 18 rows. Each row: (location, claude-binding, hermes-binding, test-id).
T3_INVENTORY: list[dict[str, str]] = [
    {
        "id": "T3.001",
        "location": "scripts/improve_description.py | main entry",
        "claude": "claude -p",
        "hermes": "hermes -p",
    },
    {
        "id": "T3.002",
        "location": "scripts/improve_description.py | env-strip block",
        "claude": "os.environ minus CLAUDECODE",
        "hermes": "hermes_subprocess_env()",
    },
    {
        "id": "T3.003",
        "location": "scripts/run_eval.py | invocation",
        "claude": "claude -p --output-format stream-json --verbose",
        "hermes": "hermes -p --output-format stream-json --verbose",
    },
    {
        "id": "T3.004",
        "location": "scripts/run_eval.py | env-strip",
        "claude": "os.environ.pop('CLAUDECODE', None)",
        "hermes": "hermes_subprocess_env()",
    },
    {
        "id": "T3.005",
        "location": "scripts/run_eval.py | commands path",
        "claude": ".claude/commands/<target>.md",
        "hermes": "~/.hermes/skills/<cat>/<target>/SKILL.md",
    },
    {
        "id": "T3.006",
        "location": "scripts/run_eval.py | --model arg",
        "claude": "--model claude-...",
        "hermes": "--model hermes-... (or omit)",
    },
    {
        "id": "T3.007",
        "location": "SKILL.md | claude.ai link",
        "claude": "claude.ai URL",
        "hermes": "nousresearch.com/hermes (or remove)",
    },
    {
        "id": "T3.008",
        "location": "SKILL.md | Cowork section",
        "claude": "Cowork-specific section",
        "hermes": "removed",
    },
    {
        "id": "T3.009",
        "location": "SKILL.md | Cowork fallback",
        "claude": "Cowork fallback",
        "hermes": "removed",
    },
    {
        "id": "T3.010",
        "location": "SKILL.md | webbrowser open",
        "claude": "if not webbrowser.open(...)",
        "hermes": "removed",
    },
    {
        "id": "T3.011",
        "location": "scripts/run_eval.py | NDJSON parse",
        "claude": "Anthropic {type, message:{content:[{type,text}]}}",
        "hermes": "Hermes {event, role, content} (via adapter)",
    },
    {
        "id": "T3.012",
        "location": "agents/grader.md",
        "claude": "Anthropic subagent YAML",
        "hermes": "Hermes agent_name registration",
    },
    {
        "id": "T3.013",
        "location": "agents/analyzer.md",
        "claude": "Anthropic subagent YAML",
        "hermes": "Hermes agent_name registration",
    },
    {
        "id": "T3.014",
        "location": "agents/comparator.md",
        "claude": "Anthropic subagent YAML",
        "hermes": "Hermes agent_name registration",
    },
    {
        "id": "T3.015",
        "location": "eval-viewer/generate_review.py",
        "claude": "(host-agnostic; no Claude binding)",
        "hermes": "preserved unchanged (stdlib HTTP server)",
    },
    {
        "id": "T3.016",
        "location": "scripts/run_loop.py",
        "claude": "module docstring references claude -p",
        "hermes": "module docstring references hermes -p",
    },
    {
        "id": "T3.017",
        "location": "scripts/run_loop.py",
        "claude": "any other claude/CLAUDECODE invocations",
        "hermes": "replaced per Hermes equivalent",
    },
    {
        "id": "T3.018",
        "location": "scripts/improve_description.py",
        "claude": 'RuntimeError(f"claude -p exited {rc}")',
        "hermes": 'RuntimeError(f"hermes -p exited {rc}")',
    },
]

# Active-cap detection result.
SHORT_DESC_CAP = 60
FULL_DESC_CAP = 1024

# Cap-raise / cap-status detection by static AST read of
# `agent/skill_utils.py:extract_skill_description` in the active checkout.
# Returns "patched" (MAX_DESCRIPTION_LENGTH used) or "unpatched" (literal 60).
_LIVE_HERMES_AGENT = Path("~/.hermes/hermes-agent").expanduser()
PINNED_UPSTREAM_COMMIT = "2a40fd2e7c52207aa903bd33fc4c65716126966e"


def detect_active_cap(checkout: Optional[Path] = None) -> str:
    """Detect the active cap (60 vs MAX_DESCRIPTION_LENGTH) in agent/skill_utils.py.

    Reads `extract_skill_description` in the active checkout (or
    `~/.hermes/hermes-agent` if `checkout` is None and the env var
    `HERMES_HERMES_AGENT_TARGET` is unset). Returns "patched" if the literal
    `60` is replaced by `MAX_DESCRIPTION_LENGTH`, else "unpatched".

    Raises:
        FileNotFoundError: if the active checkout's `agent/skill_utils.py` is
            not present.
    """
    target = checkout or _LIVE_HERMES_AGENT
    src = target / "agent" / "skill_utils.py"
    if not src.exists():
        raise FileNotFoundError(f"agent/skill_utils.py not found in {target}")
    text = src.read_text(encoding="utf-8")
    return "patched" if "MAX_DESCRIPTION_LENGTH" in text and "if len(desc) > 60:" not in text else "unpatched"


def _select_skill_md(skill_dir: Path, *, cap: str) -> Path:
    """Select SKILL.md.short (cap=unpatched) or SKILL.md (cap=patched)."""
    if cap == "unpatched":
        short = skill_dir / "SKILL.md.short"
        if not short.exists():
            raise FileNotFoundError(
                f"SKILL.md.short not found in {skill_dir}; cannot install under 60-char cap"
            )
        return short
    return skill_dir / "SKILL.md"


def _render_migration_skill_port(*, generated_at: str, upstream_commit: str) -> str:
    """Render the body of `MIGRATION.skill-port.md` from the T3 inventory."""
    lines: list[str] = [
        "# Skill Port — Migrated skill-creator (T3 inventory)",
        "",
        "<!-- DO NOT EDIT: generated by hermes-skill-creator-plugin -->",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Source skill | skill-creator |",
        f"| Pinned upstream commit | {upstream_commit} |",
        "| Hermes nesting-guard var | HERMES_SESSION |",
        f"| Generated at | {generated_at} |",
        "",
        "## Per-binding replacements (T3)",
        "",
        "| # | location | claude-binding | hermes-binding | test-id |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, row in enumerate(T3_INVENTORY, start=1):
        lines.append(
            f"| {i} | {row['location']} | `{row['claude']}` | `{row['hermes']}` | {row['id']} |"
        )
    lines.extend(
        [
            "",
            "## Strength preservation",
            "",
            "| Strength | Artifact | Hermes equivalent | AC |",
            "| --- | --- | --- | --- |",
            "| Subagent split | agents/{grader,analyzer,comparator}.md | delegate_task + agent_name | T3.012-T3.014 |",
            "| Eval pipeline | scripts/{run_eval, aggregate_benchmark, generate_report, ...}.py | same scripts, Hermes CLI, event-shape adapter | T3.003, T3.011, T3.006 |",
            "| Eval viewer | eval-viewer/{generate_review.py, viewer.html} | generate_review.py --static, file:// URL | T3.015 |",
            "",
        ]
    )
    return "\n".join(lines)


def _generated_at() -> str:
    frozen = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME")
    if frozen:
        return frozen
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class InstallResult:
    target_dir: Path
    selected_skill_md: Path
    migration_note: Path


def install(
    *,
    skill_source: Path,
    hermes_home: Path,
    worktree_root: Path,
    cap: Optional[str] = None,
) -> InstallResult:
    """Install the migrated skill to `hermes_home/skills/skill-creator/`.

    Emits `MIGRATION.skill-port.md` to `worktree_root`. The destination is
    the flat path under HERMES_HOME so the skill appears in
    `<available_skills>`. NEVER writes to the live `~/.hermes/hermes-agent`.

    Args:
        skill_source: Path to `skills/skill-creator/` (worktree root).
        hermes_home: Path to the destination HERMES_HOME (must NOT be
            `~/.hermes/hermes-agent`).
        worktree_root: Where to write `MIGRATION.skill-port.md`.
        cap: "patched" (use SKILL.md, <= 1024) or "unpatched"
            (use SKILL.md.short, <= 60). If None, autodetect from the
            active checkout.

    Returns:
        InstallResult with the resolved paths.

    Raises:
        FileNotFoundError: if the source skill is missing.
        ValueError: if hermes_home resolves to the live install.
    """
    if hermes_home.resolve() == _LIVE_HERMES_AGENT.resolve():
        raise ValueError(
            f"refusing to install to live Hermes install: {hermes_home}. "
            "Set HERMES_HOME to a tmp_path or pass --hermes-home explicitly."
        )
    if not skill_source.exists():
        raise FileNotFoundError(f"skill source not found: {skill_source}")

    target_dir = hermes_home / "skills" / "skill-creator"
    target_dir.mkdir(parents=True, exist_ok=True)
    # Copy the whole skill dir tree.
    for child in skill_source.rglob("*"):
        rel = child.relative_to(skill_source)
        dst = target_dir / rel
        if child.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dst)

    if cap is None:
        cap = detect_active_cap()
    src_md = _select_skill_md(skill_source, cap=cap)
    target_md = target_dir / "SKILL.md"
    shutil.copy2(src_md, target_md)

    migration_note = worktree_root / "MIGRATION.skill-port.md"
    migration_note.write_text(
        _render_migration_skill_port(
            generated_at=_generated_at(),
            upstream_commit=PINNED_UPSTREAM_COMMIT,
        ),
        encoding="utf-8",
    )
    return InstallResult(
        target_dir=target_dir,
        selected_skill_md=target_md,
        migration_note=migration_note,
    )


__all__ = [
    "T3_INVENTORY",
    "InstallResult",
    "SHORT_DESC_CAP",
    "FULL_DESC_CAP",
    "PINNED_UPSTREAM_COMMIT",
    "detect_active_cap",
    "install",
]
