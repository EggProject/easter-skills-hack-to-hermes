"""check_migration_note.py — MIGRATION*.md is generated, not hand-edited.

Pre-commit refuses any MIGRATION*.md whose sha256 differs from the
generator's last-emitted checksum recorded in `.migration_manifest.json`
at the worktree root. The generator (Script #1 --emit-migration-note and
the migrated-skill installer) writes BOTH the MIGRATION*.md file AND the
manifest entry on every regeneration. If a developer hand-edits the
migration note, the checksum drift is caught at commit time.

TDD test cases (mirror of tests/meta/test_meta_check_migration_note.py):

  test_unmodified_migration_file_passes
  test_hand_edit_to_migration_hermes_patch_md_fails
  test_hand_edit_to_migration_skill_port_md_fails
  test_generated_marker_present_passes
  test_generated_marker_missing_fails
  test_manifest_missing_fails_when_migration_file_present
  test_check_runs_clean_on_this_worktree_skeleton
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

from tools._migration_checks import check_migration_files, run_all_checks
from tools._migration_manifest import is_git_tracked
from tools._migration_manifest import subprocess as _migration_subprocess
from tools._migration_paths import GENERATED_MARKER

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / ".migration_manifest.json"
GENERATED_MARKER = GENERATED_MARKER
_is_git_tracked = is_git_tracked
subprocess = _migration_subprocess
check_migration_files = check_migration_files


def _emit(message: str, stream: object) -> None:
    stream.write(f"{message}\n")


def main(argv: Iterable[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(
        list(argv),
    )
    findings = run_all_checks(REPO_ROOT)
    if findings:
        for finding in findings:
            _emit(
                f"[check_migration_note] FAIL: {finding.message}",
                sys.stderr,
            )
        summary = (
            f"[check_migration_note] {len(findings)} finding(s) — MIGRATION*.md must be regenerated, not hand-edited."
        )
        _emit(summary, sys.stderr)
        return 1
    _emit(
        "[check_migration_note] OK (all MIGRATION*.md match manifest)",
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
