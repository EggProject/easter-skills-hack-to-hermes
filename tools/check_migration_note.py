"""Migration-note generation check.

Rejects hand-edits to the generated MIGRATION*.md files at the worktree
root. The files may be present (the workstream-C patcher emits them via
``--emit-migration-note``) but the only allowed modification path is via
the patcher's emit. Hand-edits are a hard pre-commit failure.

For Phase 5 / workstream C this is a no-op: the migration notes are
emitted into a worktree-local test dir (never the worktree root), so
the hook has nothing to police yet. The full hook (which checks the
frontmatter ``<!-- generated; do not edit by hand -->`` markers and
diff-against-last-emit) lands in workstream F.
"""

from __future__ import annotations

import sys


def main() -> int:
    # No-op stub: the migration note for workstream C is generated into
    # a tmp worktree in tests, never into the live worktree root.
    return 0


if __name__ == "__main__":
    sys.exit(main())
