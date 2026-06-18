"""_migration_checks.py — top-level orchestrator for migration checks."""

from __future__ import annotations

import sys
from pathlib import Path

from tools._migration_inspect import CheckInputs, Finding, inspect_one
from tools._migration_manifest import load_manifest
from tools._migration_paths import GLOB_PATTERNS, REPO_ROOT


def iter_migration_files(root: Path) -> list[Path]:
    """List existing MIGRATION*.md files in ``root`` matching known names."""
    out: list[Path] = []
    for pattern in GLOB_PATTERNS:
        candidate = root / pattern
        if candidate.exists():
            out.append(candidate)
    return out


def read_or_record_failure(
    path: Path,
    rel: Path,
    findings: list[Finding],
) -> str | None:
    """Return file body, appending a read-failure finding if needed."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        findings.append(Finding(path=path, message=f"could not read {rel}"))
        return None


def _collect_findings(
    root: Path,
    manifest: dict[str, str],
    manifest_filename: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for candidate in iter_migration_files(root):
        rel = candidate.relative_to(root)
        body = read_or_record_failure(candidate, rel, findings)
        if body is None:
            continue
        findings.extend(
            inspect_one(
                CheckInputs(
                    candidate,
                    rel,
                    body,
                    manifest,
                    manifest_filename,
                ),
            ),
        )
    return findings


def _live_manifest_path() -> Path:
    """Return the live MANIFEST_PATH from the public script module.

    Looks up either the ``tools.check_migration_note`` entry (when
    imported as a normal package module) or the ``__main__`` entry
    (when invoked via ``python3 -m tools.check_migration_note``).
    """
    public_module = sys.modules.get("tools.check_migration_note")
    if public_module is not None:
        return public_module.MANIFEST_PATH
    main_module = sys.modules.get("__main__")
    if main_module is None:
        return REPO_ROOT / ".migration_manifest.json"
    ends_with_tool = getattr(main_module, "__file__", "").endswith(
        "check_migration_note.py",
    )
    if ends_with_tool:
        return main_module.MANIFEST_PATH
    return REPO_ROOT / ".migration_manifest.json"


def check_migration_files(root: Path) -> list[Finding]:
    """Run all checks against every MIGRATION*.md in the worktree root."""
    manifest_path = _live_manifest_path()
    manifest = load_manifest(manifest_path)
    return _collect_findings(root, manifest, manifest_path.name)


def run_all_checks(root: Path) -> list[Finding]:
    """Convenience alias delegating to :func:`check_migration_files`."""
    return check_migration_files(root)
