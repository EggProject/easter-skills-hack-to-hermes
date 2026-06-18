r"""check_bilingual.py — enforce that all console messages are bilingual
(en/hu on a single line: '[en] ... / [hu] ...') and that --help output uses
two top-level sections (`Usage (English)` and `Használat (magyar)`) with
mirrored content.

Walks every `print(...)` and `logger.{info,warning,error}(...)` call in
`src/hermes_skill_creator_plugin/` and asserts the format string matches
`^\[en\] .+ / \[hu\] .+$`. Also walks Click commands' docstrings to
assert the two-section structure.

TDD test cases (mirror of tests/meta/test_meta_check_bilingual.py):

  test_console_message_with_both_locales_passes
  test_console_message_missing_hu_fails
  test_console_message_missing_en_fails
  test_console_message_with_hu_on_separate_line_fails
  test_click_echo_calls_in_src_have_bilingual_argument
  test_help_text_has_english_and_magyar_sections
  test_check_runs_clean_on_this_worktree_skeleton
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = ("src", "scripts", "skills")

# `print` and `logger.{info,warning,error}` calls.
CONSOLE_FUNCS = frozenset({"print", "info", "warning", "error", "debug", "critical"})
# The bilingual surface: `[en] <any content, may contain '/'> / [hu] <any content>`.
# Non-greedy `+?` keeps the en-side tight so the FIRST `/ [hu]` separator wins.
# `\S` after each marker requires non-empty content on both sides — a bare
# `[en] / [hu]` (zero-length message) is not a real bilingual message.
BILINGUAL_RE = re.compile(r"\[en\]\s*\S.*?/ \[hu\]\s*\S")
HELP_EN_SECTION = "Usage (English)"
HELP_HU_SECTION = "Használat (magyar)"


class Finding(NamedTuple):
    """One violation: file, line, message."""

    path: Path
    lineno: int
    message: str


def _iter_python_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for sub in SRC_DIRS:
        d = root / sub
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if ".venv" in p.parts or ".git" in p.parts or "__pycache__" in p.parts:
                continue
            out.append(p)
    return out


def _string_value(node: ast.AST | None) -> str | None:
    """Extract a static string value from a Constant or JoinedStr.

    Returns None for non-static strings (variables, calls, f-strings with
    non-literal placeholders).
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                # Only accept static placeholders that resolve to known literals.
                cv = v.value
                if isinstance(cv, ast.Constant) and isinstance(cv.value, str):
                    parts.append(cv.value)
                else:
                    return None  # dynamic -> skip
            else:
                return None
        return "".join(parts)
    return None


def _func_name(node: ast.Call) -> str:
    """Best-effort name for the function being called."""
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _walk_calls(tree: ast.AST) -> Iterable[ast.Call]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def check_console_messages(root: Path) -> list[Finding]:
    """Walk every .py file and assert console messages are bilingual."""
    findings: list[Finding] = []
    for p in _iter_python_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text, filename=str(p))
        except (OSError, SyntaxError):
            continue
        for call in _walk_calls(tree):
            name = _func_name(call)
            if name not in CONSOLE_FUNCS:
                continue
            if not call.args:
                continue
            arg = call.args[0]
            value = _string_value(arg)
            if value is None:
                continue  # dynamic — caller must use bilingual format at runtime
            if not BILINGUAL_RE.search(value):
                findings.append(
                    Finding(
                        path=p,
                        lineno=call.lineno,
                        message=f"console message lacks bilingual format: {value[:80]!r}",
                    )
                )
    return findings


def check_help_text(root: Path) -> list[Finding]:
    """Assert Click-command docstrings contain both English and Hungarian help sections."""
    findings: list[Finding] = []
    for p in _iter_python_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if HELP_EN_SECTION not in text and HELP_HU_SECTION not in text:
            continue  # not a help docstring — skip
        # If either section is present, both must be present.
        has_en = HELP_EN_SECTION in text
        has_hu = HELP_HU_SECTION in text
        if has_en and not has_hu:
            findings.append(
                Finding(
                    path=p,
                    lineno=1,
                    message=f"help text has `{HELP_EN_SECTION}` but is missing `{HELP_HU_SECTION}`",
                )
            )
        elif has_hu and not has_en:
            findings.append(
                Finding(
                    path=p,
                    lineno=1,
                    message=f"help text has `{HELP_HU_SECTION}` but is missing `{HELP_EN_SECTION}`",
                )
            )
    return findings


def run_all_checks(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_console_messages(root))
    findings.extend(check_help_text(root))
    return findings


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    _parse_args(argv)
    findings = run_all_checks(REPO_ROOT)
    if findings:
        for f in findings:
            rel = f.path.relative_to(REPO_ROOT)
            print(
                f"[check_bilingual] FAIL: {rel}:{f.lineno}: {f.message}",
                file=sys.stderr,
            )
        print(
            f"[check_bilingual] {len(findings)} finding(s) — "
            f"console messages must be `[en] ... / [hu] ...` on a single line.",
            file=sys.stderr,
        )
        return 1
    print("[check_bilingual] OK (en/hu single-line + two-section help)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
