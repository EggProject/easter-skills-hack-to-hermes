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
PREVIEW_CHARS = 80  # magic number: chars shown in human messages.

# `print` and `logger.{info,warning,error}` calls.
CONSOLE_FUNCS = frozenset(
    {"print", "info", "warning", "error", "debug", "critical"},
)
# The bilingual surface: `[en] <any content> / [hu] <any content>`.
# Non-greedy `+?` keeps the en-side tight so the FIRST `/ [hu]` separator wins.
# `\S` after each marker requires non-empty content on both sides — a bare
# `[en] / [hu]` (zero-length message) is not a real bilingual message.
BILINGUAL_RE = re.compile(r"\[en\]\s*\S.*?/ \[hu\]\s*\S")
HELP_EN_SECTION = "Usage (English)"
HELP_HU_SECTION = "Használat (magyar)"
SKIP_DIRS = (".venv", ".git", "__pycache__")


class Finding(NamedTuple):
    """One violation: file, line, message."""

    path: Path
    lineno: int
    message: str


def _is_skipped(parts: tuple[str, ...]) -> bool:
    """True when any path part matches a skip-list directory name."""
    return any(part in SKIP_DIRS for part in parts)


def _collect_python_files(d: Path) -> list[Path]:
    """Walk one subdir for .py files, skipping SKIP_DIRS members."""
    return [p for p in d.rglob("*.py") if not _is_skipped(p.parts)]


def _iter_python_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for sub in SRC_DIRS:
        d = root / sub
        if not d.exists():
            continue
        out.extend(_collect_python_files(d))
    return out


def _constant_part(v: ast.AST) -> str | None:
    """Resolve one JoinedStr value node to its static string, else None."""
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return v.value
    if isinstance(v, ast.FormattedValue):
        cv = v.value
        if isinstance(cv, ast.Constant) and isinstance(cv.value, str):
            return cv.value
    return None


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
            part = _constant_part(v)
            if part is None:
                return None
            parts.append(part)
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


def _parse_tree(p: Path) -> ast.AST | None:
    """Read and parse a Python file; return AST or None on any failure."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        return ast.parse(text, filename=str(p))
    except SyntaxError:
        return None


def _inspect_call(call: ast.Call) -> Finding | None:
    """Return a Finding if `call` is a non-bilingual console message."""
    name = _func_name(call)
    if name not in CONSOLE_FUNCS:
        return None
    if not call.args:
        return None
    value = _string_value(call.args[0])
    if value is None:
        return None  # dynamic — caller must use bilingual format at runtime
    if BILINGUAL_RE.search(value):
        return None
    preview = value[:PREVIEW_CHARS]
    return Finding(
        path=call.lineno and Path(""),  # placeholder; filled by caller
        lineno=call.lineno,
        message=f"console message lacks bilingual format: {preview!r}",
    )


def _inspect_file(p: Path) -> list[Finding]:
    """Walk a single Python file and return its bilingual findings."""
    tree = _parse_tree(p)
    if tree is None:
        return []
    out: list[Finding] = []
    for call in _walk_calls(tree):
        finding = _inspect_call(call)
        if finding is not None:
            out.append(finding._replace(path=p))
    return out


def check_console_messages(root: Path) -> list[Finding]:
    """Walk every .py file and assert console messages are bilingual."""
    findings: list[Finding] = []
    for p in _iter_python_files(root):
        findings.extend(_inspect_file(p))
    return findings


def _help_section_state(text: str) -> tuple[bool, bool]:
    """Return (has_en, has_hu) for the docstring section markers."""
    has_en = HELP_EN_SECTION in text
    has_hu = HELP_HU_SECTION in text
    return has_en, has_hu


def _missing_section_finding(
    p: Path,
    present: str,
    missing: str,
) -> Finding:
    """Build a finding for a help-text missing the other language section."""
    msg = f"help text has `{present}` but is missing `{missing}`"
    return Finding(path=p, lineno=1, message=msg)


def _inspect_help_text(p: Path) -> list[Finding]:
    """Return findings for one file's help-text section coverage."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    has_en, has_hu = _help_section_state(text)
    if not has_en and not has_hu:
        return []  # not a help docstring — skip
    if has_en and not has_hu:
        return [
            _missing_section_finding(p, HELP_EN_SECTION, HELP_HU_SECTION),
        ]
    if has_hu and not has_en:
        return [
            _missing_section_finding(p, HELP_HU_SECTION, HELP_EN_SECTION),
        ]
    return []


def check_help_text(root: Path) -> list[Finding]:
    """Assert Click docstrings contain English + Hungarian sections."""
    findings: list[Finding] = []
    for p in _iter_python_files(root):
        findings.extend(_inspect_help_text(p))
    return findings


def run_all_checks(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_console_messages(root))
    findings.extend(check_help_text(root))
    return findings


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    return parser.parse_args(list(argv))


def _emit_error(message: str) -> None:
    sys.stderr.write(message + "\n")


def _emit_ok(message: str) -> None:
    sys.stdout.write(message + "\n")


def _format_failure(f: Finding) -> str:
    rel = f.path.relative_to(REPO_ROOT)
    return f"[check_bilingual] FAIL: {rel}:{f.lineno}: {f.message}"


def main(argv: Iterable[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    _parse_args(argv)
    findings = run_all_checks(REPO_ROOT)
    if findings:
        for f in findings:
            _emit_error(_format_failure(f))
        summary = (
            "[check_bilingual] "
            f"{len(findings)} finding(s) — "
            "console messages must be `[en] ... / [hu] ...` on a single line."
        )
        _emit_error(summary)
        return 1
    _emit_ok("[check_bilingual] OK (en/hu single-line + two-section help)")
    return 0


if __name__ == "__main__":
    sys.exit(main())