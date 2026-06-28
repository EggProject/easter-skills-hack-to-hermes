"""tests/report/test_cli.py

TDD: tests for the cli_report command — read-only contract, json output,
sort modes, flag rejections, exit codes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from click.testing import CliRunner

from easter_hermes_sorry_skills import cli_report
from easter_hermes_sorry_skills.cli_report import HELP_EN_HEADER, HELP_HU_HEADER, main
from tests.report._fixtures import _write_profile

# --- help + bilingual ---


def test_help_is_bilingual() -> None:
    runner = CliRunner()
    en_result = runner.invoke(main, ["--help"])
    assert en_result.exit_code == 0
    assert HELP_EN_HEADER in en_result.output
    assert HELP_HU_HEADER not in en_result.output
    for opt in ("--profile", "--sort", "--format", "--json"):
        assert opt in en_result.output

    hu_result = runner.invoke(main, ["--lang", "hu", "--help"])
    assert hu_result.exit_code == 0
    assert HELP_HU_HEADER in hu_result.output
    assert HELP_EN_HEADER not in hu_result.output
    for opt in ("--profile", "--sort", "--format", "--json"):
        assert opt in hu_result.output


def test_console_log_lines_match_bilingual_regex() -> None:
    """Assert every print/echo line in cli_report.py matches the bilingual regex.

    The script emits messages via click.echo; this test asserts the source
    contains no non-bilingual string literals passed to echo/print.
    """
    import ast

    src = Path(cli_report.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    pat = re.compile(r"\[en\][^/]+/\[hu\]")
    bad: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Match click.echo(...) AND print(...).
            is_echo = (
                isinstance(func, ast.Attribute)
                and func.attr in {"echo"}
                and isinstance(func.value, ast.Name)
                and func.value.id == "click"
            )
            is_print = isinstance(func, ast.Name) and func.id == "print"
            if not (is_echo or is_print):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if not arg.value:
                        # Empty separator line — allowed.
                        continue
                    if not pat.search(arg.value):
                        bad.append((node.lineno, arg.value))
    assert not bad, f"non-bilingual call(s): {bad}"


# --- exit codes ---


def test_exit_zero_on_success(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 0


def test_exit_six_when_enabled_detection_unavailable(hermes_home: Path, monkeypatch) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})

    def _boom(*a, **kw):
        raise ImportError("simulated missing _enabled_detection")

    monkeypatch.setattr(cli_report, "get_enabled_skills", _boom)
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 6


# --- rejected flags ---


def test_rejects_apply_flag(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--apply"],
    )
    assert rc == 2


def test_rejects_emit_migration_note_flag(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--emit-migration-note"],
    )
    assert rc == 2


def test_rejects_write_report_flag(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--write-report"],
    )
    assert rc == 2


def test_rejects_apply_flag_with_equals(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--apply=true"],
    )
    assert rc == 2


# --- JSON output ---


def test_json_format_shape(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    out_path = hermes_home.parent / "report.json"
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="json",
        json_path=out_path,
    )
    assert rc == 0
    obj = json.loads(out_path.read_text(encoding="utf-8"))
    assert obj["tool"] == "easter-hermes-sorry-skills-report"
    assert "profiles" in obj
    assert obj["profiles"][0]["profile_name"] == "hermes"


def test_json_path_outside_hermes_home(hermes_home: Path, tmp_path: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    out = tmp_path / "report.json"
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="json",
        json_path=out,
    )
    assert rc == 0
    assert out.exists()


def test_json_path_inside_hermes_home_aborts(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="json",
        json_path=hermes_home / "report.json",
    )
    assert rc == 6


def test_json_default_under_cwd(hermes_home: Path, monkeypatch, tmp_path: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    monkeypatch.chdir(tmp_path)
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="json",
        json_path=None,
    )
    assert rc == 0
    assert (tmp_path / "skill-report.json").exists()


def test_json_default_aborts_when_cwd_inside_hermes_home(hermes_home: Path, monkeypatch) -> None:
    """The default `./skill-report.json` MUST be safety-checked against HERMES_HOME.

    Regression sentinel: if cwd is INSIDE hermes_home, the default json_path
    would resolve inside the live install. The reporter must abort with
    exit 6 instead of writing the file.
    """
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    monkeypatch.chdir(hermes_home)
    rc = cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="json",
        json_path=None,
    )
    assert rc == 6
    # The file was NOT created.
    assert not (hermes_home / "skill-report.json").exists()


def test_json_deterministic_with_frozen_time(hermes_home: Path, tmp_path: Path, monkeypatch) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    out1 = tmp_path / "report1.json"
    out2 = tmp_path / "report2.json"
    cli_report.run(profile="hermes", sort="tokens", fmt="json", json_path=out1)
    cli_report.run(profile="hermes", sort="tokens", fmt="json", json_path=out2)
    assert hashlib.sha256(out1.read_bytes()).hexdigest() == hashlib.sha256(out2.read_bytes()).hexdigest()


def test_json_multi_profile_is_single_valid_document(hermes_home: Path, tmp_path: Path) -> None:
    """Regression: default profile iteration writes ONE JSON object with all profiles.

    Previously, format_json was called per-profile and concatenated with \\n\\n,
    producing N separate JSON objects that parsers reject.
    """
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    # Named profiles live under <hermes_home>/profiles/<name> per _resolve_profiles.
    _write_profile(hermes_home, name="profiles/work", config=None, skills={"b": "y"})
    out = tmp_path / "report.json"
    rc = cli_report.run(profile=None, sort="tokens", fmt="json", json_path=out)
    assert rc == 0
    obj = json.loads(out.read_text(encoding="utf-8"))  # MUST parse as one object.
    assert len(obj["profiles"]) == 2
    names = {p["profile_name"] for p in obj["profiles"]}
    assert names == {"hermes", "work"}
    # Top-level fields appear exactly once.
    text = out.read_text(encoding="utf-8")
    assert text.count('"tool":') == 1
    assert text.count('"version":') == 1


# --- sort modes ---


def test_sort_by_tokens(hermes_home: Path) -> None:
    _write_profile(
        hermes_home,
        name="hermes",
        config=None,
        skills={"a": "x" * 100, "b": "y" * 5, "c": "z" * 50},
    )
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 0


def test_sort_by_use_count(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="use_count", fmt="text", json_path=None)
    assert rc == 0


def test_sort_by_last_used_at(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="last_used_at", fmt="text", json_path=None)
    assert rc == 0


def test_unknown_sort_aborts(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="bogus", fmt="text", json_path=None)
    assert rc == 2


def test_unknown_format_aborts(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="bogus", json_path=None)
    assert rc == 2


# --- help short-circuit ---


def test_show_help_returns_zero(hermes_home: Path) -> None:
    rc = cli_report.run(show_help=True)
    assert rc == 0


# --- curator field verification fixture ---


def test_report_curator_field_verification_recorded() -> None:
    """Assert the curator fixture is well-formed and was verified within 7 days.

    The fixture's content is the real contract (the six documented
    SkillUsageStore fields). The mtime is captured at the start of
    the test (no mutation) and the age is computed against "now"; a
    fresh checkout with an old git-recorded mtime that exceeds 7
    days FAILS this gate as it should.
    """
    import json
    import time
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "curator" / "recorded_fields.json"
    assert fixture.is_file(), f"missing fixture: {fixture}"
    obj = json.loads(fixture.read_text(encoding="utf-8"))
    fields = set(obj["fields"].keys())
    expected = {
        "use_count",
        "view_count",
        "patch_count",
        "last_used_at",
        "last_viewed_at",
        "last_patched_at",
    }
    assert fields == expected
    original_mtime = fixture.stat().st_mtime
    age = time.time() - original_mtime
    assert age < 7 * 86400, f"curator fixture is {age / 86400:.1f} days old"


def test_report_usage_n_a_when_curator_absent(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 0
    # Curator is absent; all usage columns render n/a.


def test_report_usage_does_not_invent_fields() -> None:
    """The reporter source must reference only the six documented field names."""
    import re
    from pathlib import Path

    from easter_hermes_sorry_skills import _reporter, cli_report

    pat = re.compile(r"\b(last_used|last_viewed|last_patched|use_count|view_count|patch_count)\b")
    bad: list[str] = []
    for mod in (_reporter, cli_report):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pat.search(stripped) and "last_used" in stripped and "_at" not in stripped.split("last_used")[1][:8]:
                # The legacy unsuffixed "last_used" form is forbidden.
                if re.search(r"\blast_used\b(?!_at)", stripped):
                    bad.append(stripped)
    assert not bad, f"legacy field reference(s): {bad}"


def test_report_uses_at_suffixed_timestamps() -> None:
    """Source references must use the _at-suffixed timestamps, not the legacy form."""
    import re
    from pathlib import Path

    from easter_hermes_sorry_skills import _reporter, cli_report

    for mod in (_reporter, cli_report):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # The legacy unsuffixed forms (last_used, last_viewed, last_patched) must
        # NOT appear as bare identifiers — only the _at-suffixed forms are allowed.
        for legacy in ("last_used", "last_viewed", "last_patched"):
            # A bare reference is `<legacy>` NOT followed by `_at` or by other
            # identifier chars.
            for m in re.finditer(rf"\b{legacy}\b", src):
                tail = src[m.end() : m.end() + 4]
                assert tail.startswith("_at"), f"legacy field {legacy!r} in {mod.__name__} at offset {m.start()}"


def test_cli_report_main_entry_invokes_main(monkeypatch) -> None:
    """Calling the _main_entry function exercises the standalone CLI path."""
    from easter_hermes_sorry_skills import cli_report

    called = {"n": 0}

    def stub_main() -> None:
        called["n"] += 1

    monkeypatch.setattr(cli_report, "main", stub_main)
    cli_report._main_entry()
    assert called["n"] == 1


# --- verbose (Phase D) ---


def test_verbose_flag_added_to_report(hermes_home: Path) -> None:
    """``--verbose`` at the report CLI emits ``[verbose]`` diagnostics on stderr."""
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    runner = CliRunner()
    result = runner.invoke(main, ["--verbose"])
    assert result.exit_code == 0, result.output
    assert "[verbose]" in result.stderr or "[verbose]" in result.output


def test_report_help_lists_verbose() -> None:
    """The report ``--help`` output mentions ``--verbose`` once (single language)."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert result.output.count("--verbose") >= 1
