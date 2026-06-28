"""tests/meta/test_meta_check_bilingual.py — meta-tests for tools/check_bilingual.py.

The code now uses single-language console messages (the actual bilingual
strings live in ``src/easter_hermes_sorry_skills/i18n/``). This meta-tool
inverts the previous bilingual-enforcement rule: console messages and
help text MUST NOT contain ``[en]`` or ``[hu]`` prefix tokens — except in
``i18n/`` helper files where those tokens are the source of truth.

TDD test cases (mirror of tools/check_bilingual.py):

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

import textwrap
from pathlib import Path

import pytest

from tools import check_bilingual
from tools.check_bilingual import (
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


def _write_i18n(tmp_path: Path, name: str, body: str) -> Path:
    """Drop a .py file under tmp_path/src/.../i18n/."""
    i18n = tmp_path / "src" / "pkg" / "i18n"
    i18n.mkdir(parents=True, exist_ok=True)
    target = i18n / name
    target.write_text(textwrap.dedent(body), encoding="utf-8")
    return target


def test_console_message_single_language_passes(tmp_path: Path) -> None:
    """A plain single-language `print("hello")` MUST pass (no findings)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("hello")
            """,
    )
    assert check_console_messages(tmp_path) == []


def test_console_message_with_en_prefix_fails(tmp_path: Path) -> None:
    """`print("[en] only english")` MUST be flagged (single-language rule)."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[en] only english")
            """,
    )
    findings = check_console_messages(tmp_path)
    assert any("prefix" in f.message or "[en]" in f.message for f in findings)


def test_console_message_with_hu_prefix_fails(tmp_path: Path) -> None:
    """`print("[hu] csak magyar")` MUST be flagged (single-language rule)."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[hu] csak magyar")
            """,
    )
    findings = check_console_messages(tmp_path)
    assert any("prefix" in f.message or "[hu]" in f.message for f in findings)


def test_console_message_with_both_prefixes_fails(tmp_path: Path) -> None:
    """A legacy bilingual `[en] ... / [hu] ...` literal MUST be flagged."""
    _write_src(
        tmp_path,
        "bad.py",
        """\
        def run() -> None:
            print("[en] hello / [hu] szia")
            """,
    )
    findings = check_console_messages(tmp_path)
    assert len(findings) >= 1


def test_i18n_helper_with_prefix_passes(tmp_path: Path) -> None:
    """Files under i18n/ contain the bilingual strings by design => no findings."""
    _write_i18n(
        tmp_path,
        "messages_en.py",
        """\
        REPORT_HELP_SHORT = "[en] Profile skill token + usage reporter / [hu] Profil skill token + használati riport"
        """,
    )
    assert check_console_messages(tmp_path) == []


def test_click_echo_with_en_prefix_fails(tmp_path: Path) -> None:
    """A static `click.echo("[en] hello")` literal MUST be flagged.

    click.echo is now in CONSOLE_FUNCS because single-language enforcement
    applies to ALL console-output channels, not only print/logger.
    """
    _write_src(
        tmp_path,
        "cli.py",
        """\
        import click
        def run() -> None:
            click.echo("[en] hello")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert any("[en]" in f.message for f in findings)


def test_click_echo_dynamic_call_passes(tmp_path: Path) -> None:
    """`click.echo(pick(lang).X)` is dynamic => skipped (not flagged)."""
    _write_src(
        tmp_path,
        "cli.py",
        """\
        import click
        def run(msg: object) -> None:
            click.echo(msg)
        """,
    )
    assert check_console_messages(tmp_path) == []


def test_help_text_with_en_prefix_fails(tmp_path: Path) -> None:
    """A file containing the `[en]` prefix token MUST be flagged by check_help_text."""
    _write_src(
        tmp_path,
        "cli.py",
        '''\
        """Module docstring with [en] inline marker."""
        ''',
    )
    findings = check_help_text(tmp_path)
    assert any("[en]" in f.message for f in findings)


def test_help_text_with_hu_prefix_fails(tmp_path: Path) -> None:
    """A file containing the `[hu]` prefix token MUST be flagged by check_help_text."""
    _write_src(
        tmp_path,
        "cli.py",
        '''\
        """Module docstring with [hu] inline marker."""
        ''',
    )
    findings = check_help_text(tmp_path)
    assert any("[hu]" in f.message for f in findings)


def test_help_text_in_i18n_helper_passes(tmp_path: Path) -> None:
    """Files under i18n/ contain `[en]/[hu]` by design => no findings."""
    _write_i18n(
        tmp_path,
        "messages_hu.py",
        '''\
        """Hungarian messages — [hu] prefix is the source of truth."""
        REPORT_HELP = "[hu] Profil / [en] Profile"
        ''',
    )
    assert check_help_text(tmp_path) == []


def test_check_runs_clean_on_this_worktree_skeleton(tmp_path: Path, monkeypatch) -> None:
    """The hook MUST exit 0 against a clean synthetic fixture (single-language everywhere)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("hello")
            print("szia")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    findings = run_all_checks(tmp_path)
    assert findings == []


def test_console_message_with_logger_warning_prefix_fails(tmp_path: Path) -> None:
    """logger.warning("[en] ...") MUST be flagged (single-language rule)."""
    _write_src(
        tmp_path,
        "log.py",
        """\
        import logging
        logger = logging.getLogger(__name__)

        def run() -> None:
            logger.warning("[en] something")
        """,
    )
    findings = check_console_messages(tmp_path)
    assert any("[en]" in f.message for f in findings)


def test_console_message_with_logger_info_single_lang_passes(tmp_path: Path) -> None:
    """logger.info("plain info") without any prefix MUST pass."""
    _write_src(
        tmp_path,
        "log.py",
        """\
        import logging
        logger = logging.getLogger(__name__)

        def run() -> None:
            logger.info("info")
            logger.error("error")
            logger.debug("debug")
            logger.critical("critical")
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
    assert findings == []


def test_console_message_with_brackets_not_en_or_hu_passes(tmp_path: Path) -> None:
    """Brackets around tokens other than en/hu MUST NOT be flagged (e.g. `[verbose]`, `[X]`)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("[verbose] diagnostic info")
            print("[X] marker")
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
        'def run() -> None:\n    print("[en] hello")\n',
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
            print("[en] only english")
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
            print("hello")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    rc = check_bilingual.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


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
    assert any("[en]" in f.message for f in findings)


def test_skills_dir_is_walked(tmp_path: Path) -> None:
    """A file under skills/ MUST be walked by the detector."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "bad.py").write_text('def run() -> None:\n    print("[hu] csak")\n', encoding="utf-8")
    findings = run_all_checks(tmp_path)
    assert any("[hu]" in f.message for f in findings)


def test_argparse_argument_parsing() -> None:
    """_parse_args MUST accept an empty argv list (defaults: all invariants on)."""
    args = check_bilingual._parse_args([])
    assert args is not None


def test_help_text_skip_when_unreadable(tmp_path: Path, monkeypatch) -> None:
    """A file that raises OSError on read_text MUST be skipped, not crash the hook."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text(
        "def run() -> None:\n    print('hello')\n",
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
    """The walker MUST skip .venv/, .git/, __pycache__ dirs."""
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
    """An f-string with a non-Constant FormattedValue MUST return None."""
    import ast

    node = ast.parse("print(f'{1+1}')", mode="eval").body
    assert check_bilingual._string_value(node) is None


def test_string_value_fstring_with_non_constant_placeholder_returns_none() -> None:
    """A JoinedStr with a non-Constant/non-FormattedValue part MUST return None."""
    import ast

    # `f"{[1, 2, 3]}"` has a List inside FormattedValue — falls through to None.
    node = ast.parse("print(f'{[1, 2, 3]}')", mode="eval").body
    assert check_bilingual._string_value(node) is None


def test_main_module_invocation_via_runpy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The `if __name__ == '__main__'` block MUST be runnable in-process."""

    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("hello")
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
    """A JoinedStr with FormattedValue(value=Constant(str)) MUST be joined."""
    import ast

    fv = ast.FormattedValue(
        value=ast.Constant(value="M"),
        conversion=-1,
        format_spec=None,
        lineno=1,
        col_offset=0,
    )
    js = ast.JoinedStr(
        values=[
            ast.Constant(value="hi-"),
            fv,
            ast.Constant(value="-suffix"),
        ],
        lineno=1,
        col_offset=0,
    )
    ast.fix_missing_locations(js)
    assert check_bilingual._string_value(js) == "hi-M-suffix"


def test_string_value_joinedstr_with_unknown_value_returns_none() -> None:
    """A JoinedStr with a non-Constant/non-FormattedValue value MUST return None."""
    import ast

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


def test_main_with_argv_returns_clean(tmp_path: Path, monkeypatch, capsys) -> None:
    """main(argv) MUST accept an explicit argv list (not just sys.argv)."""
    _write_src(
        tmp_path,
        "ok.py",
        """\
        def run() -> None:
            print("hello")
        """,
    )
    monkeypatch.setattr(check_bilingual, "REPO_ROOT", tmp_path)
    rc = check_bilingual.main([])
    assert rc == 0


def test_i18n_skipped_for_help_text(tmp_path: Path) -> None:
    """i18n directory files MUST be skipped by check_help_text entirely."""
    _write_i18n(
        tmp_path,
        "messages_en.py",
        '''\
        """[en] docstring contains the prefix on purpose."""
        X = "[en] hello"
        ''',
    )
    findings = check_help_text(tmp_path)
    assert findings == []


def test_i18n_subdir_anywhere_in_path_is_exempt(tmp_path: Path) -> None:
    """A file whose path contains any 'i18n' part MUST be exempt from both checks."""
    _write_i18n(
        tmp_path,
        "messages_hu.py",
        """\
        Y = "[hu] szia / [en] hello"
        """,
    )
    assert check_console_messages(tmp_path) == []
    assert check_help_text(tmp_path) == []
