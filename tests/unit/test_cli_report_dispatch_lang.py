"""tests/unit/test_cli_report_dispatch_lang.py

Regression tests for the ``lang`` parameter on
:func:`cli_report_dispatch.check_hermes_home` and
:func:`cli_report_dispatch.load_context`.

The reporter CLI exposes a ``--lang`` flag (default ``en``) that selects
the language of the error message emitted when ``--json`` resolves under
``HERMES_HOME``. ``check_hermes_home`` must accept a ``lang`` keyword and
route the message through :func:`_i18n_pick.pick` so that ``hu`` emits
the Hungarian single-language text and ``en`` (or anything else) emits
the English single-language text (no ``[en]`` / ``[hu]`` prefixes).

These tests predate the implementation change (TDD red-then-green).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from easter_hermes_sorry_skills import cli_report_dispatch as _dispatch


def test_check_hermes_home_default_lang_emits_en_half() -> None:
    """Without ``lang`` arg, default ``"en"`` prints the EN single-language message."""
    captured: dict[str, str] = {}

    def _fake_echo(msg: str, err: bool = False) -> None:
        captured["msg"] = msg

    hermes_home = Path("/tmp/hermes-home")
    inside = hermes_home / "report.json"
    with patch.object(_dispatch, "_imps"), patch.object(_dispatch.click, "echo", _fake_echo):
        _dispatch._imps._check_json_path.return_value = True  # type: ignore[attr-defined]
        rc = _dispatch.check_hermes_home(inside, hermes_home)
    assert rc == _dispatch._JSON_INSIDE_HERMES_HOME_RC
    assert captured["msg"] == "--json path resolves under HERMES_HOME, refusing", captured["msg"]


def test_check_hermes_home_hu_lang_emits_hu_half() -> None:
    """With ``lang="hu"``, prints the HU single-language message."""
    captured: dict[str, str] = {}

    def _fake_echo(msg: str, err: bool = False) -> None:
        captured["msg"] = msg

    hermes_home = Path("/tmp/hermes-home")
    inside = hermes_home / "report.json"
    with patch.object(_dispatch, "_imps"), patch.object(_dispatch.click, "echo", _fake_echo):
        _dispatch._imps._check_json_path.return_value = True  # type: ignore[attr-defined]
        rc = _dispatch.check_hermes_home(inside, hermes_home, lang="hu")
    assert rc == _dispatch._JSON_INSIDE_HERMES_HOME_RC
    assert captured["msg"] == "a --json útvonala a HERMES_HOME alá esik, megtagadva", captured["msg"]


def test_load_context_forwards_lang_to_check_hermes_home() -> None:
    """``load_context`` must thread the ``lang`` argument into check_hermes_home."""
    hermes_home = Path("/tmp/hermes-home")
    with patch.object(_dispatch, "_imps"), patch.object(_dispatch, "check_hermes_home") as fake_check:
        fake_check.return_value = None
        _dispatch._imps._paths.resolve_hermes_home.return_value = hermes_home  # type: ignore[attr-defined]
        _dispatch._imps._helpers.resolve_json_path.return_value = None  # type: ignore[attr-defined]
        _dispatch._imps._paths.load_curator.return_value = None  # type: ignore[attr-defined]
        _dispatch._imps._paths.resolve_profiles.return_value = []  # type: ignore[attr-defined]
        _dispatch.load_context("text", None, None, lang="hu")
    assert fake_check.call_args.kwargs.get("lang") == "hu" or (
        len(fake_check.call_args.args) >= 3 and fake_check.call_args.args[2] == "hu"
    )
