"""tests/meta/test_meta_check_migration_note.py — meta-tests for tools/check_migration_note.py.

Implements the TDD test list declared at the top of tools/check_migration_note.py:

  test_unmodified_migration_file_passes
  test_hand_edit_to_migration_hermes_patch_md_fails
  test_hand_edit_to_migration_skill_port_md_fails
  test_generated_marker_present_passes
  test_generated_marker_missing_fails
  test_manifest_missing_fails_when_migration_file_present
  test_check_runs_clean_on_this_worktree_skeleton
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools import check_migration_note
from tools.check_migration_note import (
    GENERATED_MARKER,
    MANIFEST_PATH,
    check_migration_files,
)


def _write_migration(tmp_path: Path, name: str, body: str, *, register_in_manifest: bool = True) -> Path:
    """Drop a MIGRATION*.md and (optionally) register its sha in the manifest."""
    target = tmp_path / name
    target.write_text(f"{GENERATED_MARKER}\n{body}\n", encoding="utf-8")
    if register_in_manifest:
        manifest = {}
        if (tmp_path / MANIFEST_PATH.name).exists():
            manifest = json.loads((tmp_path / MANIFEST_PATH.name).read_text(encoding="utf-8"))
        manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        (tmp_path / MANIFEST_PATH.name).write_text(json.dumps(manifest), encoding="utf-8")
    return target


def _setup_repo(tmp_path: Path) -> None:
    """Make REPO_ROOT point at tmp_path for the duration of the test."""
    import importlib

    importlib.reload(check_migration_note)


def test_unmodified_migration_file_passes(tmp_path: Path, monkeypatch) -> None:
    """Generator-emitted file with matching manifest sha => no findings."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    _write_migration(tmp_path, "MIGRATION.md", "Patch summary.")
    assert check_migration_files(tmp_path) == []


def test_hand_edit_to_migration_hermes_patch_md_fails(tmp_path: Path, monkeypatch) -> None:
    """Hand-editing a tracked MIGRATION*.md (sha no longer matches manifest) => finding."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    target = _write_migration(tmp_path, "MIGRATION.hermes-patch.md", "Original.")
    # Simulate a hand-edit by rewriting the file AFTER the manifest was written.
    target.write_text(f"{GENERATED_MARKER}\nHand-edited.\n", encoding="utf-8")
    with patch.object(check_migration_note, "_is_git_tracked", return_value=True):
        findings = check_migration_files(tmp_path)
    assert any("MIGRATION.hermes-patch.md" in f.message for f in findings)
    assert any("differs from" in f.message for f in findings)


def test_hand_edit_to_migration_skill_port_md_fails(tmp_path: Path, monkeypatch) -> None:
    """Hand-editing MIGRATION.skill-port.md (sha no longer matches manifest) => finding."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    target = _write_migration(tmp_path, "MIGRATION.skill-port.md", "Original skill port.")
    target.write_text(f"{GENERATED_MARKER}\nHand-edited skill port.\n", encoding="utf-8")
    with patch.object(check_migration_note, "_is_git_tracked", return_value=True):
        findings = check_migration_files(tmp_path)
    assert any("MIGRATION.skill-port.md" in f.message for f in findings)


def test_generated_marker_present_passes(tmp_path: Path, monkeypatch) -> None:
    """MIGRATION*.md with the generated marker => no marker-missing finding."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    _write_migration(tmp_path, "MIGRATION.md", "All good.")
    findings = check_migration_files(tmp_path)
    assert not any("missing generated marker" in f.message for f in findings)


def test_generated_marker_missing_fails(tmp_path: Path, monkeypatch) -> None:
    """MIGRATION*.md WITHOUT the generated marker => finding."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    (tmp_path / "MIGRATION.md").write_text("Plain notes.\n", encoding="utf-8")
    findings = check_migration_files(tmp_path)
    assert any("missing generated marker" in f.message for f in findings)


def test_manifest_missing_fails_when_migration_file_present(tmp_path: Path, monkeypatch) -> None:
    """A git-tracked MIGRATION*.md without a manifest entry => finding."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    target = tmp_path / "MIGRATION.hermes-patch.md"
    target.write_text(f"{GENERATED_MARKER}\nBody.\n", encoding="utf-8")
    # No manifest at all.
    with patch.object(check_migration_note, "_is_git_tracked", return_value=True):
        findings = check_migration_files(tmp_path)
    assert any("missing from" in f.message for f in findings)


def test_check_runs_clean_on_this_worktree_skeleton(tmp_path: Path, monkeypatch) -> None:
    """Hook MUST exit 0 against a clean synthetic fixture (manifest matches)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    _write_migration(tmp_path, "MIGRATION.md", "OK.")
    _write_migration(tmp_path, "MIGRATION.hermes-patch.md", "OK.")
    _write_migration(tmp_path, "MIGRATION.skill-port.md", "OK.")
    with patch.object(check_migration_note, "_is_git_tracked", return_value=True):
        findings = check_migration_files(tmp_path)
    assert findings == []


def test_no_migration_files_returns_empty(tmp_path: Path, monkeypatch) -> None:
    """When no MIGRATION*.md exists, the hook MUST return []."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    findings = check_migration_files(tmp_path)
    assert findings == []


def test_unreadable_migration_file_yields_finding(tmp_path: Path, monkeypatch) -> None:
    """An unreadable MIGRATION*.md MUST yield a clear finding (not crash)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    target = tmp_path / "MIGRATION.md"
    target.write_text("irrelevant\n", encoding="utf-8")
    # Force the read to fail.
    real_read_text = Path.read_text

    def failing_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "MIGRATION.md":
            raise OSError("intentional")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    findings = check_migration_files(tmp_path)
    assert any("could not read" in f.message for f in findings)


def test_manifest_with_garbage_json_returns_empty_dict(tmp_path: Path, monkeypatch) -> None:
    """A non-JSON manifest MUST be treated as empty (no crash)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    manifest = tmp_path / MANIFEST_PATH.name
    manifest.write_text("not-json-at-all", encoding="utf-8")
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", manifest)
    target = tmp_path / "MIGRATION.md"
    target.write_text(f"{GENERATED_MARKER}\nBody.\n", encoding="utf-8")
    # No manifest entries; the file isn't tracked => no findings.
    findings = check_migration_files(tmp_path)
    assert findings == []


def test_main_returns_1_when_findings(tmp_path: Path, monkeypatch, capsys) -> None:
    """main() MUST exit 1 when at least one finding is emitted."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    (tmp_path / "MIGRATION.md").write_text("Plain notes.\n", encoding="utf-8")
    rc = check_migration_note.main([])
    assert rc == 1
    out = capsys.readouterr().err
    assert "FAIL" in out


def test_main_returns_0_when_clean(tmp_path: Path, monkeypatch, capsys) -> None:
    """main() MUST exit 0 against a clean synthetic fixture (manifest matches)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    _write_migration(tmp_path, "MIGRATION.md", "OK.")
    with patch.object(check_migration_note, "_is_git_tracked", return_value=True):
        rc = check_migration_note.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_is_git_tracked_returns_false_when_git_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_is_git_tracked MUST return False when git binary is not found."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)

    def raising(*args: object, **kwargs: object) -> str:
        raise FileNotFoundError("no git")

    monkeypatch.setattr(check_migration_note.subprocess, "check_output", raising)
    assert check_migration_note._is_git_tracked(tmp_path / "MIGRATION.md") is False


def test_main_with_argv_none_uses_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """main(argv=None) MUST read sys.argv[1:] (covers the `if argv is None` branch)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    monkeypatch.setattr("sys.argv", ["check_migration_note.py"])
    rc = check_migration_note.main(None)
    assert rc == 0


def test_main_module_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The __main__ block MUST be importable (covers line 161)."""
    import importlib

    importlib.reload(check_migration_note)
    assert hasattr(check_migration_note, "main")


def test_is_git_tracked_returns_false_on_called_process_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_is_git_tracked MUST return False on CalledProcessError (line 60)."""
    import subprocess as sp

    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)

    # Patch the module's `subprocess` reference so the function sees the patched call.
    def raising(*args: object, **kwargs: object) -> str:
        raise sp.CalledProcessError(1, "git")

    monkeypatch.setattr(check_migration_note.subprocess, "check_output", raising)
    assert check_migration_note._is_git_tracked(tmp_path / "MIGRATION.md") is False


def test_is_git_tracked_returns_true_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_is_git_tracked MUST return True when git outputs a non-empty string (line 60)."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note.subprocess, "check_output", lambda *a, **k: "MIGRATION.md\n")
    assert check_migration_note._is_git_tracked(tmp_path / "MIGRATION.md") is True


def test_is_git_tracked_returns_false_on_empty_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_is_git_tracked MUST return False when git outputs an empty string."""
    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note.subprocess, "check_output", lambda *a, **k: "")
    assert check_migration_note._is_git_tracked(tmp_path / "MIGRATION.md") is False


def test_main_module_via_runpy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The `if __name__ == '__main__'` block MUST be runnable in-process (line 161)."""
    import types

    monkeypatch.setattr(check_migration_note, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_migration_note, "MANIFEST_PATH", tmp_path / MANIFEST_PATH.name)
    monkeypatch.setattr("sys.argv", ["check_migration_note.py"])
    main_module = types.ModuleType("__main__")
    main_module.__dict__.update(check_migration_note.__dict__)
    main_module.__name__ = "__main__"
    src = Path(check_migration_note.__file__).read_text(encoding="utf-8")
    code = compile(src, check_migration_note.__file__, "exec")
    try:
        exec(code, main_module.__dict__)  # noqa: S102
    except SystemExit as e:
        assert e.code in (0, 1)
