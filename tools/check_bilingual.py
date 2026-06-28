r"""check_bilingual.py — enforce single-language console messages.

The code uses single-language console messages; the bilingual ``[en] / [hu]``
strings live exclusively in ``src/.../i18n/`` helpers (``messages_en.py``,
``messages_hu.py``). This meta-tool walks ``src/``, ``scripts/`` and
``skills/`` and asserts NO console message or help text contains a literal
``[en]`` or ``[hu]`` prefix — unless the file is under an ``i18n`` path
part (the i18n helpers own those tokens by design).

Walked console-output calls: ``print``, ``click.echo``, and
``logger.{info,warning,error,debug,critical}``.

TDD test cases (mirror of tests/meta/test_meta_check_bilingual.py):

  test_console_message_single_language_passes
  test_console_message_with_en_prefix_fails
  test_console_message_with_hu_prefix_fails
  test_console_message_with_both_prefixes_fails
  test_i18n_helper_with_prefix_passes
  test_click_echo_with_en_prefix_fails
  test_help_text_with_en_prefix_fails
  test_help_text_with_hu_prefix_fails
  test_help_text_in_i18n_helper_passes
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

# Console-output functions whose static-string literal must be free of
# `[en]` / `[hu]` prefixes. click.echo is included: single-language
# enforcement applies to every console channel.
CONSOLE_FUNCS = frozenset(
    {"print", "echo", "info", "warning", "error", "debug", "critical"},
)
# Forbidden prefix tokens. The pattern matches `[en]` / `[hu]` as whole
# bracketed tokens — not partial matches inside a word.
PREFIX_RE = re.compile(r"\[(en|hu)\]")
# i18n helpers (`src/.../i18n/messages_en.py`, `messages_hu.py`) own the
# bilingual literals by design and are exempt from both checks.
I18N_DIR = "i18n"
SKIP_DIRS = (".venv", ".git", "__pycache__")


class Finding(NamedTuple):
    """One violation: file, line, message."""

    path: Path
    lineno: int
    message: str


def _is_skipped(parts: tuple[str, ...]) -> bool:
    """True when any path part matches a skip-list directory name."""
    return any(part in SKIP_DIRS for part in parts)


def _is_i18n(parts: tuple[str, ...]) -> bool:
    """True when any path part is the i18n helper directory."""
    return I18N_DIR in parts


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
    """Return a Finding if `call` is a console message containing a `[en]`/`[hu]` prefix."""
    name = _func_name(call)
    if name not in CONSOLE_FUNCS:
        return None
    if not call.args:
        return None
    value = _string_value(call.args[0])
    if value is None:
        return None  # dynamic — caller must enforce single-language at runtime
    match = PREFIX_RE.search(value)
    if match is None:
        return None
    preview = value[:PREVIEW_CHARS]
    return Finding(
        path=Path(""),  # placeholder; filled by caller
        lineno=call.lineno,
        message=f"console message contains forbidden `{match.group(0)}` prefix: {preview!r}",
    )


def _inspect_file(p: Path) -> list[Finding]:
    """Walk a single Python file and return its single-language findings."""
    if _is_i18n(p.parts):
        return []  # i18n helpers own the bilingual literals
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
    """Walk every .py file and assert console messages are single-language."""
    findings: list[Finding] = []
    for p in _iter_python_files(root):
        findings.extend(_inspect_file(p))
    return findings


def _inspect_help_text(p: Path) -> list[Finding]:
    """Return findings for a file's help-text / module-docstring prefix tokens."""
    if _is_i18n(p.parts):
        return []  # i18n helpers own the bilingual literals
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    match = PREFIX_RE.search(text)
    if match is None:
        return []
    return [
        Finding(
            path=p,
            lineno=1,
            message=f"help text contains forbidden `{match.group(0)}` prefix",
        ),
    ]


def check_help_text(root: Path) -> list[Finding]:
    """Assert no source file's help text contains a `[en]`/`[hu]` prefix."""
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
            "console messages must not contain `[en]` / `[hu]` prefixes "
            "(use the i18n helpers)."
        )
        _emit_error(summary)
        return 1
    _emit_ok("[check_bilingual] OK (single-language console messages, no i18n prefixes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
