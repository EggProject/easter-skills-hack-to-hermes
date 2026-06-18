"""tests/meta/test_meta_migration_helpers.py — migration helper coverage."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tools import _migration_checks, _migration_inspect, _migration_manifest

PUBLIC_TOOL = "tools.check_migration_note"
MAIN = "__main__"
DEFAULT_NAME = ".migration_manifest.json"


def _drop_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, MAIN, raising=False)


def _swap_main(monkeypatch: pytest.MonkeyPatch) -> ModuleType | None:
    previous = sys.modules.get(MAIN)
    stub = ModuleType("__not_the_tool__")
    stub.__file__ = "/some/other/script.py"
    monkeypatch.setitem(sys.modules, MAIN, stub)
    return previous


def _restore_main(monkeypatch: pytest.MonkeyPatch, previous: ModuleType | None) -> None:
    if previous is None:
        monkeypatch.delitem(sys.modules, MAIN, raising=False)
    else:
        monkeypatch.setitem(sys.modules, MAIN, previous)
    importlib.import_module(PUBLIC_TOOL)


def _fake_main(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    fake = importlib.import_module(PUBLIC_TOOL)
    monkeypatch.delitem(sys.modules, PUBLIC_TOOL, raising=False)
    fake.__name__ = MAIN
    monkeypatch.setitem(sys.modules, MAIN, fake)
    return fake


def test_manifest_path_via_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``_live_manifest_path`` reads from a ``__main__``-mounted tool."""
    target = tmp_path / "manifest.json"
    fake = _fake_main(monkeypatch)
    fake.MANIFEST_PATH = target
    observed = _migration_checks._live_manifest_path()
    importlib.import_module(PUBLIC_TOOL)
    assert observed == target


def test_manifest_path_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falls back to REPO_ROOT when no entry resolves."""
    monkeypatch.delitem(sys.modules, PUBLIC_TOOL, raising=False)
    previous = _swap_main(monkeypatch)
    observed = _migration_checks._live_manifest_path()
    _restore_main(monkeypatch, previous)
    assert observed == _migration_checks.REPO_ROOT / DEFAULT_NAME


def test_manifest_path_no_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falls back to REPO_ROOT when ``__main__`` is missing."""
    monkeypatch.delitem(sys.modules, PUBLIC_TOOL, raising=False)
    _drop_main(monkeypatch)
    observed = _migration_checks._live_manifest_path()
    importlib.import_module(PUBLIC_TOOL)
    assert observed == _migration_checks.REPO_ROOT / DEFAULT_NAME


def test_is_git_tracked_via_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_live_is_git_tracked`` reads from a ``__main__``-mounted tool."""
    fake = _fake_main(monkeypatch)

    def fake_tracked(target: Path) -> bool:
        return True

    fake._is_git_tracked = fake_tracked
    observed = _migration_inspect._live_is_git_tracked()
    importlib.import_module(PUBLIC_TOOL)
    assert observed is fake_tracked


def test_is_git_tracked_no_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises when neither public tool nor ``__main__`` resolves."""
    monkeypatch.delitem(sys.modules, PUBLIC_TOOL, raising=False)
    previous = _swap_main(monkeypatch)
    if previous is None:
        _drop_main(monkeypatch)
    else:
        monkeypatch.setitem(sys.modules, MAIN, previous)
    with pytest.raises(RuntimeError, match="check_migration_note"):
        _migration_inspect._live_is_git_tracked()
    importlib.import_module(PUBLIC_TOOL)


def test_is_git_tracked_no_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises when ``__main__`` is also missing."""
    monkeypatch.delitem(sys.modules, PUBLIC_TOOL, raising=False)
    _drop_main(monkeypatch)
    with pytest.raises(RuntimeError, match="check_migration_note"):
        _migration_inspect._live_is_git_tracked()
    importlib.import_module(PUBLIC_TOOL)


def test_load_manifest_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``load_manifest`` returns ``{}`` on OSError reading the file."""
    target = tmp_path / "manifest.json"
    target.write_text("{}", encoding="utf-8")

    def raising_read(this: Path, *_args: object, **_kwargs: object) -> str:
        raise OSError("intentional")

    monkeypatch.setattr(Path, "read_text", raising_read)
    assert _migration_manifest.load_manifest(target) == {}


def test_load_manifest_filters_bad(tmp_path: Path) -> None:
    """``load_manifest`` drops non-dict JSON and non-string entries."""
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert _migration_manifest.load_manifest(target) == {}
    payload = json.dumps({"good": "ok", "bad_int": 7, "bad_list": [1, 2]})
    target.write_text(payload, encoding="utf-8")
    assert _migration_manifest.load_manifest(target) == {"good": "ok"}
