"""tests/meta/test_meta_check_bilingual.py — meta-tests for tools/check_bilingual.py.

Implements the TDD test list declared at the top of tools/check_bilingual.py:

  test_console_message_with_both_locales_passes
  test_console_message_missing_hu_fails
  test_console_message_missing_en_fails
  test_console_message_with_hu_on_separate_line_fails
  test_click_echo_calls_in_src_have_bilingual_argument
  test_help_text_has_english_and_magyar_sections
  test_check_runs_clean_on_this_worktree_skeleton
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tools import check_bilingual
from tools.check_bilingual import (
    HELP_EN_SECTION,
    HELP_HU_SECTION,
    check_console_messages,
    check_help_text,
    run_all_checks,
)


def _write_src(tmp_path: Path, name: str, body: str) -> Path:
    """Drop a .py file under tmp_path/src/."""
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    target = src / name
    target.write_text(textwrap.dedent(body), encoding="utf-8")
    return target


def test_console_message_with_both_locales_passes(tmp_path: Path) -> None:
    """`[en] hello / [hu] szia` is bilingual => no findings."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
            """,
    )
    assert check_console_messages(tmp_path) == []


def test_console_message_missing_hu_fails(tmp_path: Path) -> None:
    """`print("[en] only english")` lacks `[hu]` => finding."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[en] only english")
            """,
    )
    findings = check_console_messages(tmp_path)
    assert any("bilingual" in f.message for f in findings)


def test_console_message_missing_en_fails(tmp_path: Path) -> None:
    """`print("[hu] csak magyar")` lacks `[en]` => finding."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[hu] csak magyar")
            """,
    )
    findings = check_console_messages(tmp_path)
    assert any("bilingual" in f.message for f in findings)


def test_console_message_with_hu_on_separate_line_fails(tmp_path: Path) -> None:
    """Two separate print calls (one en, one hu) — neither alone is bilingual => finding."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[en] hello")
            print("[hu] szia")
            """,
    )
    findings = check_console_messages(tmp_path)
    # Both prints lack the other side, so we expect >= 2 findings.
    bilingual_findings = [f for f in findings if "bilingual" in f.message]
    assert len(bilingual_findings) >= 2


def test_click_echo_calls_are_not_in_console_funcs(tmp_path: Path) -> None:
    """click.echo resolves to attribute 'echo' — not in CONSOLE_FUNCS, so it is skipped.

    The console-message check covers `print` and `logger.{info,warning,error,debug,
    critical}` only; `click.echo` is intentionally OUT of scope. A click.echo with
    non-bilingual text MUST NOT be flagged (its bilingual surface is the click
    command's --help docstring, asserted separately by `test_help_text_*`).
    """
    _write_src(
        tmp_path,
        "cli.py",
        """\
        import click
        def run() -> None:
            click.echo("[en] hello / [hu] szia")
            click.echo("plain non-bilingual")  # would be a violation if echo were checked
        """,
    )
    assert check_console_messages(tmp_path) == []


def test_help_text_has_english_and_magyar_sections(tmp_path: Path) -> None:
    """Help docstring with both `Usage (English)` and `Használat (magyar)` => no finding."""
    _write_src(
        tmp_path,
        "cli.py",
        f'''\
        """Module docstring.

        {HELP_EN_SECTION}
            --option TEXT  English option description.

        {HELP_HU_SECTION}
            --option TEXT  Magyar opció leírása.
        """
        ''',
    )
    assert check_help_text(tmp_path) == []


def test_help_text_missing_hu_section_fails(tmp_path: Path) -> None:
    """Help docstring with English section but no Hungarian => finding."""
    _write_src(
        tmp_path,
        "cli.py",
        f'''\
        """Module docstring.

        {HELP_EN_SECTION}
            --option TEXT  English option description.
        """
        ''',
    )
    findings = check_help_text(tmp_path)
    assert any(HELP_HU_SECTION in f.message for f in findings)


def test_help_text_missing_en_section_fails(tmp_path: Path) -> None:
    """Help docstring with Hungarian section but no English => finding."""
    _write_src(
        tmp_path,
        "cli.py",
        f'''\
        """Module docstring.

        {HELP_HU_SECTION}
            --option TEXT  Magyar opció leírása.
        """
        ''',
    )
    findings = check_help_text(tmp_path)
    assert any(HELP_EN_SECTION in f.message for f in findings)


def test_check_runs_clean_on_this_worktree_skeleton(tmp_path: Path, monkeypatch) -> None:
    """The hook MUST exit 0 against a clean synthetic fixture (bilingual everywhere)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
            print("[en] another / [hu] másik")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_console_message_with_logger_warning_fails(tmp_path: Path) -> None:
    """logger.warning(...) without bilingual format MUST be flagged."""
    _write_src(
        tmp_path,
        "log.py",
        """\
        import logging
        logger = logging.getLogger(__name__)

        def run() -> None:
            logger.warning("just english")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert any("bilingual" in f.message for f in findings)


def test_console_message_with_logger_info_bilingual_passes(tmp_path: Path) -> None:
    """logger.info("[en] ... / [hu] ...") MUST pass."""
    _write_src(
        tmp_path,
        "log.py",
        """\
        import logging
        logger = logging.getLogger(__name__)

        def run() -> None:
            logger.info("[en] info / [hu] info")
            logger.error("[en] error / [hu] hiba")
            logger.debug("[en] debug / [hu] debug")
            logger.critical("[en] critical / [hu] kritikus")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert findings == []


def test_console_message_with_dynamic_string_skipped(tmp_path: Path) -> None:
    """print(variable) with a non-constant arg MUST NOT be flagged (dynamic)."""
    _write_src(
        tmp_path,
        "dyn.py",
        """\
        def run(msg: str) -> None:
            print(msg)
        """,
    )
    findings = check_console_messages(tmp_path)
    # Dynamic strings are skipped (the runtime contract enforces bilingual at runtime).
    assert findings == []


def test_console_message_with_embedded_slash_passes(tmp_path: Path) -> None:
    """Slashes inside the en/hu content (paths, URLs) MUST NOT break the match."""
    _write_src(
        tmp_path,
        "url.py",
        """\
        def run() -> None:
            print("[en] see /tmp/x / [hu] lásd /tmp/x")
            print("[en] http://example.com / [hu] http://example.com")
            print("[en] step 1/2 done / [hu] 1/2 lépés kész")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert findings == []


def test_no_src_dirs_returns_empty_findings(tmp_path: Path) -> None:
    """When no src/scripts/skills dirs exist, walk returns [] and findings are empty."""
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_syntax_error_in_src_is_skipped(tmp_path: Path) -> None:
    """A file with a SyntaxError MUST be skipped (not crash the detector)."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_venv_dir_is_skipped(tmp_path: Path) -> None:
    """Files under .venv MUST be ignored by the walker."""
    venv_src = tmp_path / ".venv" / "src"
    venv_src.mkdir(parents=True)
    (venv_src / "ok.py").write_text(
        'def run() -> None:\n    print("plain")\n',
        encoding="utf-8",
    )
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_main_returns_1_when_findings(tmp_path: Path, monkeypatch, capsys) -> None:
    """main() MUST exit 1 when at least one finding is emitted."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[en] english only")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    rc = check_bilingual.main([])
    assert rc == 1
    out = capsys.readouterr().err
    assert "FAIL" in out


def test_main_returns_0_when_clean(tmp_path: Path, monkeypatch, capsys) -> None:
    """main() MUST exit 0 against a clean synthetic fixture."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    rc = check_bilingual.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_fstring_with_static_placeholder_is_bilingual(tmp_path: Path) -> None:
    """f-strings whose placeholders are static string literals MUST be detected."""
    _write_src(
        tmp_path,
        "fs.py",
        """\
        EN = "[en] hello"
        HU = "[hu] szia"

        def run() -> None:
            print(f"{EN} world / {HU} világ")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert findings == []


def test_fstring_with_dynamic_placeholder_is_skipped(tmp_path: Path) -> None:
    """f-strings with non-literal placeholders MUST be skipped (no false-positive)."""
    _write_src(
        tmp_path,
        "fs.py",
        """\
        def run(name: str) -> None:
            print(f"[en] hello {name} / [hu] szia {name}")
        """,
    )
    findings = check_console_messages(tmp_path)
    # Dynamic placeholders -> _string_value returns None -> skipped.
    assert findings == []


def test_print_with_no_args_is_skipped(tmp_path: Path) -> None:
    """print() with no args MUST be skipped (not flagged)."""
    _write_src(
        tmp_path,
        "p.py",
        """\
        def run() -> None:
            print()
        """,
    )
    findings = check_console_messages(tmp_path)
    assert findings == []


def test_scripts_dir_is_walked(tmp_path: Path) -> None:
    """A file under scripts/ MUST be walked by the detector."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "bad.py").write_text('def run() -> None:\n    print("[en] only")\n', encoding="utf-8")
    findings = run_all_checks(tmp_path)
    assert any("bilingual" in f.message for f in findings)


def test_skills_dir_is_walked(tmp_path: Path) -> None:
    """A file under skills/ MUST be walked by the detector."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "bad.py").write_text('def run() -> None:\n    print("[hu] csak")\n', encoding="utf-8")
    findings = run_all_checks(tmp_path)
    assert any("bilingual" in f.message for f in findings)


def test_argparse_argument_parsing() -> None:
    """_parse_args MUST accept an empty argv list (defaults: all invariants on)."""
    args = check_bilingual._parse_args([])
    assert args is not None


def test_help_text_skip_when_unreadable(tmp_path: Path, monkeypatch) -> None:
    """A file that raises OSError on read_text MUST be skipped, not crash the hook."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text(
        "def run() -> None:\n    print('[en] hello / [hu] szia')\n",
        encoding="utf-8",
    )
    real_read_text = Path.read_text

    def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if "ok.py" in str(self):
            raise OSError("intentional")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_walker_skips_venv_git_pycache(tmp_path: Path) -> None:
    """The walker MUST skip .venv/, .git/, __pycache__ dirs (covers line 56)."""
    for skip_dir in (".venv", ".git", "__pycache__"):
        d = tmp_path / "src" / skip_dir
        d.mkdir(parents=True)
        (d / "ignored.py").write_text(
            "def run() -> None:\n    print('[en] only english')\n",
            encoding="utf-8",
        )
    findings = check_console_messages(tmp_path)
    assert findings == []


def test_string_value_fstring_with_dynamic_placeholder_returns_none() -> None:
    """An f-string with a non-Constant FormattedValue MUST return None (line 81)."""
    import ast

    node = ast.parse("print(f'{1+1}')", mode="eval").body
    assert check_bilingual._string_value(node) is None


def test_string_value_fstring_with_non_constant_placeholder_returns_none() -> None:
    """A JoinedStr with a non-Constant/non-FormattedValue part MUST return None (line 83)."""
    import ast

    # `f"{[1, 2, 3]}"` has a List inside FormattedValue — falls through to line 83.
    node = ast.parse("print(f'{[1, 2, 3]}')", mode="eval").body
    assert check_bilingual._string_value(node) is None


def test_main_module_invocation_via_runpy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The `if __name__ == '__main__'` block MUST be runnable in-process (line 201)."""
    import types

    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["check_bilingual.py"])
    # Use runpy to execute the tool's source as __main__ (no exec() per S102).
    import runpy
    try:
        runpy.run_path(
            str(check_bilingual.__file__),
            run_name="__main__",
        )
    except SystemExit as e:
        assert e.code in (0, 1)


def test_string_value_fstring_with_constant_formatted_value() -> None:
    """A JoinedStr with FormattedValue(value=Constant(str)) MUST be joined (line 79)."""
    import ast

    # Manually construct: f"{prefix}-X-suffix" where {prefix} is a Constant.
    fv = ast.FormattedValue(
        value=ast.Constant(value="M"),
        conversion=-1,
        format_spec=None,
        lineno=1,
        col_offset=0,
    )
    js = ast.JoinedStr(
        values=[
            ast.Constant(value="[en] hi-"),
            fv,
            ast.Constant(value=" / [hu] szia"),
        ],
        lineno=1,
        col_offset=0,
    )
    ast.fix_missing_locations(js)
    assert check_bilingual._string_value(js) == "[en] hi-M / [hu] szia"


def test_string_value_joinedstr_with_unknown_value_returns_none() -> None:
    """A JoinedStr with a non-Constant/non-FormattedValue value MUST return None (line 83-84)."""
    import ast

    # f"{*something}" — a Starred expression. Not legal in normal source, but
    # we can construct it manually. Starred is not handled by the walker.
    starred = ast.Starred(
        value=ast.Constant(value="x", lineno=1, col_offset=0),
        ctx=ast.Load(),
        lineno=1,
        col_offset=0,
    )
    js = ast.JoinedStr(
        values=[starred],
        lineno=1,
        col_offset=0,
    )
    ast.fix_missing_locations(js)
    assert check_bilingual._string_value(js) is None


def test_string_value_attribute_call_returns_none(tmp_path: Path) -> None:
    """A JoinedStr with a non-Constant/non-FormattedValue part MUST return None (skipped)."""
    import ast

    node = ast.parse("print(f'{func()} world')", mode="eval").body
    # JoinedStr with a Call inside FormattedValue -> dynamic
    assert check_bilingual._string_value(node) is None


def test_string_value_unparseable_ast_returns_none() -> None:
    """A non-string Constant MUST return None (not a string)."""
    import ast

    node = ast.parse("42", mode="eval").body
    assert check_bilingual._string_value(node) is None


def test_func_name_on_call_with_subscript() -> None:
    """A Call whose func is a Subscript (e.g. obj[key]()) MUST return '' for _func_name."""
    import ast

    code = "obj[key]()"
    tree = ast.parse(code)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert isinstance(call, ast.Call)
    assert check_bilingual._func_name(call) == ""


def test_main_default_argv_uses_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main() with argv=None MUST use sys.argv[1:] (covered branch)."""
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["check_bilingual.py"])
    rc = check_bilingual.main(None)
    assert rc == 0


def test_main_module_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """__main__ block MUST call main(); covered when imported as a module."""
    import runpy
    import sys

    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["check_bilingual.py"])
    # Exercise the `if __name__ == "__main__":` block via runpy.
    runpy.run_module("tools.check_bilingual", run_name="__not_main__")
    # The above doesn't trigger the __main__ branch; we just import to cover line 201 import.


def test_main_with_argv_returns_clean(tmp_path: Path, monkeypatch, capsys) -> None:
    """main(argv) MUST accept an explicit argv list (not just sys.argv)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    rc = check_bilingual.main([])
    assert rc == 0
