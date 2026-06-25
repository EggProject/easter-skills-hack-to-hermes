"""tests/report/test_readonly.py

TDD: read-only contract for the reporter. The fixture tree MUST be
byte-identical before and after every flag combination.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from easter_hermes_sorry_skills import cli_report
from tests.report._fixtures import _write_profile


def _snapshot(root: Path) -> dict[str, tuple[int, float, str]]:
    """Return a sorted map of (size, mtime, sha256) for every file under root."""
    out: dict[str, tuple[int, float, str]] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            out[str(p.relative_to(root))] = (
                len(data),
                p.stat().st_mtime,
                hashlib.sha256(data).hexdigest(),
            )
    return out


def test_report_read_only_zero_writes_default(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    before = _snapshot(hermes_home)
    cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    after = _snapshot(hermes_home)
    assert before == after


def test_report_read_only_zero_writes_json(hermes_home: Path, tmp_path: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    before = _snapshot(hermes_home)
    out = tmp_path / "report.json"
    cli_report.run(profile="hermes", sort="tokens", fmt="json", json_path=out)
    after = _snapshot(hermes_home)
    assert before == after
    assert out.exists()  # --json PATH writes outside hermes_home.


def test_report_read_only_zero_writes_all_sort_modes(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    before = _snapshot(hermes_home)
    for sort_key in ("tokens", "use_count", "last_used_at"):
        cli_report.run(profile="hermes", sort=sort_key, fmt="text", json_path=None)
    after = _snapshot(hermes_home)
    assert before == after


def test_report_read_only_zero_writes_rejected_flags(hermes_home: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    before = _snapshot(hermes_home)
    cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None, argv=["--apply"])
    cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--emit-migration-note"],
    )
    cli_report.run(
        profile="hermes",
        sort="tokens",
        fmt="text",
        json_path=None,
        argv=["--write-report"],
    )
    after = _snapshot(hermes_home)
    assert before == after


def test_report_no_write_calls_in_source() -> None:
    """AST-grep: the reporter's source MUST NOT contain write primitives.

    The reporter is strictly READ-ONLY (it may write to the operator-chosen
    --json PATH, but that path is constructed dynamically, not as a literal
    in the source). This test catches any literal write call to a path
    INSIDE the fixture tree. The documented exception is the single
    `json_path.write_text(output, ...)` call for --format=json.
    """
    import ast
    from pathlib import Path

    from easter_hermes_sorry_skills import cli_report

    src = Path(cli_report.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    bad: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # The ONLY permitted write is `json_path.write_text(...)` for the
        # --json output. Any other write primitive is a contract violation.
        if isinstance(func, ast.Attribute) and func.attr == "write_text":
            # Allow only the `json_path.write_text` call.
            if not (isinstance(func.value, ast.Name) and func.value.id == "json_path"):
                bad.append((node.lineno, f"Path.{func.attr}"))
        if isinstance(func, ast.Attribute) and func.attr in {"write_bytes", "unlink"}:
            bad.append((node.lineno, f"Path.{func.attr}"))
        if isinstance(func, ast.Name) and func.id in {"remove", "rmtree"}:
            bad.append((node.lineno, func.id))
        if (
            isinstance(func, ast.Attribute)
            and func.attr
            in {
                "remove",
                "rmtree",
                "copy",
                "copytree",
                "replace",
            }
            and isinstance(func.value, ast.Name)
            and func.value.id in {"os", "shutil"}
        ):
            bad.append((node.lineno, f"{func.value.id}.{func.attr}"))
    assert not bad, f"write calls found: {bad}"


def test_report_no_migration_report_file_emitted(hermes_home: Path, tmp_path: Path) -> None:
    _write_profile(hermes_home, name="hermes", config=None, skills={"a": "x"})
    cli_report.run(profile="hermes", sort="tokens", fmt="text", json_path=None)
    out = tmp_path / "report.json"
    cli_report.run(profile="hermes", sort="tokens", fmt="json", json_path=out)
    assert not (hermes_home / "MIGRATION.report.md").exists()
    assert not (tmp_path / "MIGRATION.report.md").exists()


def test_report_no_subprocess_for_writes() -> None:
    """The reporter MUST NOT call subprocess.run (which could have side effects)."""
    import ast
    from pathlib import Path

    from easter_hermes_sorry_skills import cli_report

    src = Path(cli_report.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "run" and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                pytest.fail("subprocess.run found in cli_report")
