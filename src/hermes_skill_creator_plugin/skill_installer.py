"""hermes_skill_creator_plugin.skill_installer — installs the migrated skill-creator.

The installer:
  1. Copies `skills/skill-creator/` (worktree root) into
     `HERMES_HOME/skills/skill-creator/` (flat, top-level deliverable).
  2. Emits `MIGRATION.skill-port.md` (worktree root) from the T3 inventory
     (18 rows; see docs/plans/07-skill-creator-migration.md).

NEVER writes to `~/.hermes/hermes-agent` (the live Hermes install). The
`HERMES_HOME` env var (or `--hermes-home`) selects the target.

TDD test cases for this module:
  test_skill_creator_home_has_skills_and_profiles_dirs
  test_installer_copies_skill_to_hermes_home_skills_dir
  test_installer_emits_migration_skill_port_md
  test_migration_skill_port_has_18_t3_rows
  test_migration_skill_port_deterministic_under_frozen_time
  test_migration_skill_port_mentions_anthropic_provenance
  test_installer_writes_only_to_hermes_home_and_worktree
  test_installer_refuses_to_write_to_live_hermes_agent
  test_installer_selects_short_or_full_description_per_active_cap
  test_detect_active_cap_raises_when_skill_utils_missing
  test_install_raises_when_skill_source_missing
  test_install_raises_when_short_skill_md_missing
  test_install_autodetects_cap
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_KEY_ID = "id"
_KEY_LOCATION = "location"
_KEY_CLAUDE = "claude"
_KEY_HERMES = "hermes"
_STATE_PATCHED = "patched"
_STATE_UNPATCHED = "unpatched"
_PATCHED_MARKER = "MAX_DESCRIPTION_LENGTH"
_UNPATCHED_MARKER = "if len(desc) > 60:"
_LIVE_HERMES_AGENT_SUFFIX = "~/.hermes/hermes-agent"
_PINNED_UPSTREAM_COMMIT = "2a40fd2e7c52207aa903bd33fc4c65716126966e"
_FROZEN_TIME_ENV_KEY = "HERMES_SKILL_CREATOR_FROZEN_TIME"
_TEXT_ENCODING = "utf-8"
_SKILL_UTILS_REL_PARTS = ("agent", "skill_utils.py")
_SKILL_DEST_REL_PARTS = ("skills", "skill-creator")
_SHORT_DESC_CAP = 60
_FULL_DESC_CAP = 1024
_SHORT_SKILL_MD_NAME = "SKILL.md.short"
_FULL_SKILL_MD_NAME = "SKILL.md"
_MIGRATION_NOTE_NAME = "MIGRATION.skill-port.md"


def _build_t3_row(
    row_id: str,
    location: str,
    claude: str,
    hermes: str,
) -> dict[str, str]:
    return {
        _KEY_ID: row_id,
        _KEY_LOCATION: location,
        _KEY_CLAUDE: claude,
        _KEY_HERMES: hermes,
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

# Active-cap detection result.
SHORT_DESC_CAP = _SHORT_DESC_CAP
FULL_DESC_CAP = _FULL_DESC_CAP

# Cap-raise / cap-status detection by static AST read of
# `agent/skill_utils.py:extract_skill_description` in the active checkout.
# Returns "patched" (MAX_DESCRIPTION_LENGTH used) or "unpatched" (literal 60).
_LIVE_HERMES_AGENT = Path(_LIVE_HERMES_AGENT_SUFFIX).expanduser()
PINNED_UPSTREAM_COMMIT = _PINNED_UPSTREAM_COMMIT


def detect_active_cap(checkout: Path | None = None) -> str:
    """Detect the active cap (60 vs MAX_DESCRIPTION_LENGTH) in agent/skill_utils.py.

    Reads `extract_skill_description` in the active checkout (or
    `~/.hermes/hermes-agent` if `checkout` is None and the env var
    `HERMES_HERMES_AGENT_TARGET` is unset). Returns "patched" if the
    literal `60` is replaced by `MAX_DESCRIPTION_LENGTH`, else
    "unpatched".

    Raises:
        FileNotFoundError: if the active checkout's
            `agent/skill_utils.py` is not present.
    """
    target = checkout or _LIVE_HERMES_AGENT
    src = target.joinpath(*_SKILL_UTILS_REL_PARTS)
    if not src.exists():
        message = f"agent/skill_utils.py not found in {target}"
        raise FileNotFoundError(message)
    text = src.read_text(encoding=_TEXT_ENCODING)
    is_patched = _PATCHED_MARKER in text and _UNPATCHED_MARKER not in text
    return _STATE_PATCHED if is_patched else _STATE_UNPATCHED


def _select_skill_md(skill_dir: Path, *, cap: str) -> Path:
    """Select SKILL.md.short (cap=unpatched) or SKILL.md (cap=patched)."""
    if cap == _STATE_UNPATCHED:
        short = skill_dir / _SHORT_SKILL_MD_NAME
        if not short.exists():
            message = (
                f"SKILL.md.short not found in {skill_dir}; "
                "cannot install under 60-char cap"
            )
            raise FileNotFoundError(message)
        return short
    return skill_dir / _FULL_SKILL_MD_NAME


def _format_t3_row(index: int, row: dict[str, str]) -> str:
    return (
        f"| {index} | {row[_KEY_LOCATION]} | "
        f"`{row[_KEY_CLAUDE]}` | `{row[_KEY_HERMES]}` | {row[_KEY_ID]} |"
    )


def _render_strength_rows() -> list[str]:
    return [
        "",
        "## Strength preservation",
        "",
        "| Strength | Artifact | Hermes equivalent | AC |",
        "| --- | --- | --- | --- |",
        (
            "| Subagent split | "
            "agents/{grader,analyzer,comparator}.md |"
            " delegate_task + agent_name | T3.012-T3.014 |"
        ),
        (
            "| Eval pipeline | "
            "scripts/{run_eval, aggregate_benchmark, "
            "generate_report, ...}.py |"
            " same scripts, Hermes CLI, event-shape adapter |"
            " T3.003, T3.011, T3.006 |"
        ),
        (
            "| Eval viewer | eval-viewer/{generate_review.py, viewer.html} |"
            " generate_review.py --static, file:// URL | T3.015 |"
        ),
        "",
    ]


def _render_migration_skill_port(
    *,
    generated_at: str,
    upstream_commit: str,
) -> str:
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
    for index, row in enumerate(T3_INVENTORY, start=1):
        lines.append(_format_t3_row(index, row))
    lines.extend(_render_strength_rows())
    return "\n".join(lines)


def _generated_at() -> str:
    frozen = os.environ.get(_FROZEN_TIME_ENV_KEY)
    if frozen:
        return frozen
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class InstallResult:
    target_dir: Path
    selected_skill_md: Path
    migration_note: Path


def _refuse_live_install(hermes_home: Path) -> None:
    message = (
        f"refusing to install to live Hermes install: {hermes_home}. "
        "Set HERMES_HOME to a tmp_path or pass --hermes-home explicitly."
    )
    raise ValueError(message)


def _copy_skill_tree(skill_source: Path, target_dir: Path) -> None:
    for child in skill_source.rglob("*"):
        rel = child.relative_to(skill_source)
        dst = target_dir / rel
        if child.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, dst)


def _write_migration_note(worktree_root: Path) -> Path:
    note = worktree_root / _MIGRATION_NOTE_NAME
    note.write_text(
        _render_migration_skill_port(
            generated_at=_generated_at(),
            upstream_commit=PINNED_UPSTREAM_COMMIT,
        ),
        encoding=_TEXT_ENCODING,
    )
    return note


def install(
    *,
    skill_source: Path,
    hermes_home: Path,
    worktree_root: Path,
    cap: str | None = None,
) -> InstallResult:
    """Install the migrated skill to `hermes_home/skills/skill-creator/`.

    Emits `MIGRATION.skill-port.md` to `worktree_root`. The destination
    is the flat path under HERMES_HOME so the skill appears in
    `<available_skills>`. NEVER writes to the live
    `~/.hermes/hermes-agent`.

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
        _refuse_live_install(hermes_home)
    if not skill_source.exists():
        message = f"skill source not found: {skill_source}"
        raise FileNotFoundError(message)

    target_dir = hermes_home.joinpath(*_SKILL_DEST_REL_PARTS)
    # Re-install: clear the prior copy so leftover files from a previous
    # install (e.g. a SKILL.md.short from a prior unpatched-cap install)
    # do not shadow the new SKILL.md.
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    _copy_skill_tree(skill_source, target_dir)

    if cap is None:
        cap = detect_active_cap()
    src_md = _select_skill_md(skill_source, cap=cap)
    target_md = target_dir / _FULL_SKILL_MD_NAME
    shutil.copy2(src_md, target_md)

    migration_note = _write_migration_note(worktree_root)
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
