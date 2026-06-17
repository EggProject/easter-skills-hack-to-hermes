"""Plan file line-count check.

Enforces the per-file cap, footer drift, and budget-table guards
described in plans/10-toolchain-and-conventions.md.

For Phase 5 / workstream C this stub is intentionally minimal: it
enforces per-file ``<= 500`` lines for the plans/ directory. The
extended footer / per-cell / budget-table guards land in workstream
F (the meta workstream) when the 00-index budget table is settled.
"""

from __future__ import annotations

import pathlib
import re
import sys

MAX_LINES = 500
FOOTER = re.compile(r"<!-- end of file: (\d+) lines \(budget \d+\) -->")


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    plans = root / "docs" / "plans"
    if not plans.exists():
        return 0
    issues: list[str] = []
    for p in sorted(plans.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        n = text.count("\n") + (0 if text.endswith("\n") else 1)
        if n > MAX_LINES:
            issues.append(f"{p}: {n} lines > {MAX_LINES}")
        footer_match = FOOTER.search(text)
        if footer_match:
            claimed = int(footer_match.group(1))
            if claimed != n:
                issues.append(
                    f"{p}: footer says {claimed} lines but file has {n}"
                )
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
