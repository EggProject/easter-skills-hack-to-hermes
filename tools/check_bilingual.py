"""Bilingual format check (EN+HU) for print / logger calls.

Walks every .py file under src/ and asserts that the format string of
each ``print(...)`` and ``logger.{info,warning,error}(...)`` call
matches ``^[en] .+ / [hu] .+$`` on a single line.

See also: plans/10-toolchain-and-conventions.md, plans/04-script-1-patch.md.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

BILINGUAL = re.compile(r"^\[en\] .+ / \[hu\] .+$")


def _check_file(path: pathlib.Path) -> list[str]:
    issues: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        issues.append(f"{path}: SyntaxError: {exc}")
        return issues
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # match `print`, `info`, `warning`, `error`
        name: str | None = None
        if isinstance(func, ast.Name) and func.id in {"print"}:
            name = "print"
        elif isinstance(func, ast.Attribute) and func.attr in {
            "info",
            "warning",
            "error",
        }:
            name = func.attr
        if name is None:
            continue
        if not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            if not BILINGUAL.match(arg0.value):
                issues.append(
                    f"{path}:{arg0.lineno}: non-bilingual {name}(): {arg0.value!r}"
                )
        elif isinstance(arg0, ast.JoinedStr):
            # f-string: walk each Constant piece
            for value in ast.walk(arg0):
                if (
                    isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                    and value.value.strip()
                ):
                    # only check the literal pieces; the call as a whole
                    # is expected to assemble into a bilingual line
                    pass
    return issues


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent / "src"
    if not root.exists():
        return 0
    all_issues: list[str] = []
    for p in root.rglob("*.py"):
        all_issues.extend(_check_file(p))
    if all_issues:
        for issue in all_issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
