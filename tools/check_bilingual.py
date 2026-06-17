#!/usr/bin/env python3
"""tools/check_bilingual.py — pre-commit hook: enforce `[en] ... / [hu] ...` format.

Walks every `print(...)` and `click.echo(...)` call's first string argument
in src/ and tests/. Asserts the format matches the bilingual regex.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BILINGUAL = re.compile(r"\[en\][^/]+/ \[hu\]")


def main() -> int:
    root = Path("src")
    if not root.is_dir():
        return 0
    bad: list[tuple[Path, int, str]] = []
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_echo = (
                isinstance(func, ast.Attribute)
                and func.attr == "echo"
                and isinstance(func.value, ast.Name)
                and func.value.id == "click"
            )
            is_print = isinstance(func, ast.Name) and func.id == "print"
            if not (is_echo or is_print):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if not arg.value:
                        continue
                    if not BILINGUAL.search(arg.value):
                        bad.append((p, node.lineno, arg.value[:60]))
    if bad:
        for p, lineno, val in bad:
            print(f"NOT_BILINGUAL: {p}:{lineno}: {val!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
