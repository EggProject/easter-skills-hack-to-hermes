"""Unit tests for ``cli_patch_flow.resolve_target``."""

from __future__ import annotations

from pathlib import Path

from easter_hermes_sorry_skills.cli_patch_flow import resolve_target


def test_resolve_target_none_returns_none() -> None:
    assert resolve_target(None) is None


def test_resolve_target_str_returns_resolved_path() -> None:
    assert resolve_target("/tmp/x") == Path("/tmp/x").resolve()


def test_resolve_target_empty_string_returns_none() -> None:
    assert resolve_target("") is None
