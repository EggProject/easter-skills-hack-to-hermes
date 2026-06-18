"""_migration_inspect.py — per-file marker and sha finding logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from tools._migration_paths import (
    GENERATED_MARKER,
    SHA_PREVIEW_LEN,
    sha256_of,
)


class Finding(NamedTuple):
    """One violation: file, message."""

    path: Path
    message: str


@dataclass(frozen=True)
class CheckInputs:
    """Inputs for one migration-file check loop iteration."""

    path: Path
    rel: Path
    body: str
    manifest: dict[str, str]
    manifest_filename: str


def marker_finding_or_none(
    path: Path,
    rel: Path,
    body: str,
) -> Finding | None:
    """Return a marker-missing finding if the file lacks GENERATED_MARKER."""
    if GENERATED_MARKER in body:
        return None
    msg = f"{rel}: missing generated marker ({GENERATED_MARKER!r})"
    return Finding(path=path, message=msg)


def drift_finding_or_none(
    path: Path,
    rel: Path,
    sha: str,
    expected: str | None,
    manifest_filename: str,
) -> Finding | None:
    """Return a manifest-drift finding if sha != expected (or missing)."""
    if expected is None:
        head = f"{rel} is git-tracked but missing from "
        tail = f"{manifest_filename}; re-run the generator"
        msg = head + tail
        return Finding(path=path, message=msg)
    if sha != expected:
        preview_actual = sha[:SHA_PREVIEW_LEN]
        preview_expected = expected[:SHA_PREVIEW_LEN]
        msg = (
            f"{rel} sha256 {preview_actual} differs from "
            f"manifest entry {preview_expected}; "
            "hand-edit detected — regenerate via the script"
        )
        return Finding(path=path, message=msg)
    return None


def _live_is_git_tracked():
    """Return the live ``_is_git_tracked`` from the public module.

    Honored by tests that ``monkeypatch.setattr`` the public attribute.
    Falls back to the ``__main__`` entry when invoked via ``python3 -m``.
    """
    import sys

    public_module = sys.modules.get("tools.check_migration_note")
    if public_module is not None:
        return public_module._is_git_tracked
    main_module = sys.modules.get("__main__")
    if main_module is None:
        raise RuntimeError("check_migration_note module not in sys.modules")
    ends_with_tool = getattr(main_module, "__file__", "").endswith(
        "check_migration_note.py",
    )
    if ends_with_tool:
        return main_module._is_git_tracked
    raise RuntimeError("check_migration_note module not in sys.modules")


def inspect_one(inputs: CheckInputs) -> list[Finding]:
    """Inspect one migration file and return its findings."""
    findings: list[Finding] = []
    marker = marker_finding_or_none(inputs.path, inputs.rel, inputs.body)
    if marker is not None:
        findings.append(marker)
    if not _live_is_git_tracked()(inputs.path):
        return findings
    sha = sha256_of(inputs.path)
    sha_finding = drift_finding_or_none(
        inputs.path,
        inputs.rel,
        sha,
        inputs.manifest.get(str(inputs.rel)),
        inputs.manifest_filename,
    )
    if sha_finding is not None:
        findings.append(sha_finding)
    return findings
