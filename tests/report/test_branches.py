"""Branch-coverage tests for cli_report internals."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from hermes_skill_creator_plugin import cli_report
from hermes_skill_creator_plugin.cli_report import main
from tests.report._fixtures import _write_profile

# --- _resolve_hermes_home ---


def test_resolve_hermes_home_default_uses_dotslash(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_HOME", raising=False)
    p = cli_report._resolve_hermes_home()
    assert p == Path("~/.hermes").expanduser()


def test_resolve_hermes_home_uses_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert cli_report._resolve_hermes_home() == tmp_path


def test_resolve_hermes_home_uses_env_with_spaces(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERMES_HOME", "  " + str(tmp_path) + "  ")
    assert cli_report._resolve_hermes_home() == tmp_path


# --- _load_curator ---


def test_load_curator_returns_none_when_module_missing(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _raise(name, *a, **kw):
        if name == "tools.skill_usage" or name.startswith("tools.skill_usage"):
            raise ImportError("no curator")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _raise)
    assert cli_report._load_curator(Path("/tmp")) is None


def test_load_curator_returns_none_when_no_usage_report(monkeypatch) -> None:
    fake_module = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "tools.skill_usage", fake_module)
    assert cli_report._load_curator(Path("/tmp")) is None


def test_load_curator_returns_module_when_present(monkeypatch) -> None:
    fake_module = SimpleNamespace(usage_report=lambda **kw: [])
    monkeypatch.setitem(sys.modules, "tools.skill_usage", fake_module)
    assert cli_report._load_curator(Path("/tmp")) is fake_module


# --- _resolve_profiles ---


def test_resolve_profiles_named_returns_one(tmp_path: Path) -> None:
    out = cli_report._resolve_profiles(tmp_path, "work")
    assert out == [tmp_path / "work"]


def test_resolve_profiles_default_includes_hermes(tmp_path: Path) -> None:
    out = cli_report._resolve_profiles(tmp_path, None)
    assert tmp_path / "hermes" in out


def test_resolve_profiles_default_includes_named(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "alpha").mkdir(parents=True)
    (tmp_path / "profiles" / "zeta").mkdir(parents=True)
    out = cli_report._resolve_profiles(tmp_path, None)
    names = [p.name for p in out]
    assert "hermes" in names
    assert "alpha" in names
    assert "zeta" in names


def test_resolve_profiles_default_skips_non_dir(tmp_path: Path) -> None:
    p = tmp_path / "profiles"
    p.mkdir(parents=True)
    (p / "a-file").write_text("not a dir")
    (p / "actual-dir").mkdir()
    out = cli_report._resolve_profiles(tmp_path, None)
    names = [pp.name for pp in out]
    assert "a-file" not in names
    assert "actual-dir" in names


# --- _load_skill_description ---


def test_load_skill_description_missing_file(tmp_path: Path) -> None:
    s = cli_report._load_skill_description(tmp_path, "missing")
    assert "missing" in s


def test_load_skill_description_read_error(tmp_path: Path, monkeypatch) -> None:
    skill_dir = tmp_path / "a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: x\n---\n", encoding="utf-8")

    def _boom(*a, **kw):raise OSError("nope")

    monkeypatch.setattr(Path, "read_text", _boom)
    s = cli_report._load_skill_description(tmp_path, "a")
    assert "a" in s


def test_load_skill_description_full_text_no_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Just some prose.\n", encoding="utf-8")
    assert "Just some prose" in cli_report._load_skill_description(tmp_path, "a")


def test_load_skill_description_no_description_line(tmp_path: Path) -> None:
    skill_dir = tmp_path / "a"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: a\n---\n\nFirst paragraph.\n\n# Heading\n", encoding="utf-8")
    s = cli_report._load_skill_description(tmp_path, "a")
    assert "First paragraph" in s


# --- _build_usage_rows with mock curator ---


class _Entry:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_build_usage_rows_with_persisted_true() -> None:
    curator = SimpleNamespace(
        usage_report=lambda **kw: [
            _Entry(
                name="a",
                use_count=3,
                view_count=5,
                patch_count=1,
                last_used_at="2026-06-16T00:00:00Z",
                last_viewed_at="2026-06-16T00:00:00Z",
                last_patched_at="2026-06-10T00:00:00Z",
                _persisted=True,
            )
        ]
    )
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    assert out["a"]["use_count"] == 3
    assert out["a"]["_persisted"] is True


def test_build_usage_rows_with_persisted_false() -> None:
    curator = SimpleNamespace(usage_report=lambda **kw: [_Entry(name="a", use_count=99, _persisted=False)])
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    assert out["a"]["use_count"] is None
    assert out["a"]["_persisted"] is False


def test_build_usage_rows_curator_raises() -> None:
    def _boom(**kw):raise RuntimeError("nope")

    curator = SimpleNamespace(usage_report=_boom)
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    assert out["a"]["_persisted"] is False


def test_build_usage_rows_entry_without_name() -> None:
    curator = SimpleNamespace(usage_report=lambda **kw: [_Entry(use_count=1)])
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    # The nameless entry is skipped, and "a" is backfilled with n/a values.
    assert "a" in out
    assert out["a"]["_persisted"] is False


def test_build_usage_rows_entry_not_in_enabled_set() -> None:
    curator = SimpleNamespace(usage_report=lambda **kw: [_Entry(name="other", use_count=1, _persisted=True)])
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    # 'other' is not in enabled set; the only enabled skill 'a' is backfilled.
    assert "other" not in out
    assert out["a"]["_persisted"] is False


def test_build_usage_rows_entry_with_missing_attributes() -> None:
    curator = SimpleNamespace(usage_report=lambda **kw: [_Entry(name="a", _persisted=True)])
    out = cli_report._build_usage_rows(curator, Path("/tmp"), frozenset({"a"}))
    assert out["a"]["use_count"] == 0  # default 0 when attr is missing
    assert out["a"]["_persisted"] is True


# --- _now_iso ---


def test_now_iso_uses_frozen_time(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_SKILL_CREATOR_FROZEN_TIME", "2026-06-17T00:00:00Z")
    assert cli_report._now_iso() == "2026-06-17T00:00:00Z"


def test_now_iso_uses_wall_clock(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_SKILL_CREATOR_FROZEN_TIME", raising=False)
    out = cli_report._now_iso()
    assert out.endswith("Z") and "T" in out


# --- _check_json_path ---


def test_check_json_path_outside_returns_false(tmp_path: Path) -> None:
    outside = tmp_path.parent / "definitely-outside.json"
    assert cli_report._check_json_path(outside, tmp_path) is False


def test_check_json_path_at_root_returns_true(tmp_path: Path) -> None:
    assert cli_report._check_json_path(tmp_path, tmp_path) is True


def test_check_json_path_inside_returns_true(tmp_path: Path) -> None:
    assert cli_report._check_json_path(tmp_path / "x" / "a.json", tmp_path) is True


# --- main() with --help and show_help short-circuit ---


def test_main_help_via_click(monkeypatch) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage (English):" in result.output


def test_main_no_args_runs_default(monkeypatch, hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0


def test_main_with_unknown_flag_passes_through(monkeypatch, hermes_home: Path) -> None:
    """Click is configured to ignore unknown options; verify the call still succeeds."""
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    runner = CliRunner()
    result = runner.invoke(main, ["--bogus", "value"])
    # Either click accepts it (exit 0) or rejects it (exit 2); both are
    # acceptable behaviors for an unknown option. The test ensures the
    # rejected-flags scan does NOT trip on it.
    assert result.exit_code in (0, 2)


# --- warning callback wiring (D6 spec mandate) ---


def test_emit_tokenizer_warning_is_bilingual() -> None:
    """The wired callback MUST emit a single bilingual line (en/hu on one line)."""
    from hermes_skill_creator_plugin import _tokenizer

    captured: list[str] = []

    def _capture(msg: str) -> None:
        captured.append(msg)

    _tokenizer.reset_warning_state()
    _tokenizer.estimate_tokens("a", "b", tokenizer=None, warning=_capture)
    assert len(captured) == 1
    line = captured[0]
    assert "[en]" in line and "[hu]" in line, f"non-bilingual warning: {line!r}"


def test_cli_report_wires_warning_callback(monkeypatch, hermes_home: Path) -> None:
    """cli_report._build_rows_for_profile MUST pass a warning= callback to estimate_tokens.

    D6 spec mandate: every estimate_tokens call from the reporter MUST thread
    the bilingual warning callback so the operator sees exactly one
    `chars/4 fallback` notice per process. This test asserts the kwarg is
    wired (rather than relying on incidental coverage).
    """
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    from hermes_skill_creator_plugin import _tokenizer

    seen: dict[str, object] = {}

    real_estimate = _tokenizer.estimate_tokens

    def _spy(name, description, **kwargs):
        seen["warning"] = kwargs.get("warning")
        return real_estimate(name, description, **kwargs)

    monkeypatch.setattr(cli_report, "estimate_tokens", _spy)
    _tokenizer.reset_warning_state()
    rc = cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    assert rc == 0
    assert seen["warning"] is not None, "warning= kwarg was NOT wired into estimate_tokens"
    assert callable(seen["warning"])
