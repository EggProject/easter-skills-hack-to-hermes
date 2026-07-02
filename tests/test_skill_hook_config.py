"""Tests for WOW skill hook config normalization."""

from __future__ import annotations

import os
import sys
import types

import pytest

from easter_hermes_sorry_skills._skill_hook_config import (
    SkillHookConfig,
    _call_load_config,
    load_skill_hook_config,
)
from easter_hermes_sorry_skills._skill_hook_config_consts import (
    ENV_LOG_LEVEL,
    MODE_ADAPTIVE,
    MODE_FIRST,
    OUTPUT_NAMES,
    OUTPUT_SHORTLIST,
)


def _config(section: object) -> dict[str, object]:
    """Build a Hermes config fragment for the plugin section."""
    return {
        "plugins": {
            "entries": {
                "easter-hermes-sorry-skills-plugin": {
                    "skill_hook": section,
                },
            },
        },
    }


def test_load_skill_hook_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing config returns documented defaults."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)

    assert load_skill_hook_config({}) == SkillHookConfig()


def test_load_skill_hook_config_reads_nested_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested plugins.entries config is normalized."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)

    result = load_skill_hook_config(
        _config(
            {
                "enabled": "false",
                "mode": "FIRST",
                "output": "NAMES",
                "top_k": "5",
                "min_score": "0",
                "log_level": "debug",
            },
        ),
    )

    assert result == SkillHookConfig(
        enabled=False,
        mode=MODE_FIRST,
        output=OUTPUT_NAMES,
        top_k=5,
        min_score=0,
        log_level="DEBUG",
    )


def test_load_skill_hook_config_invalid_values_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed values fall back per-field."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)

    result = load_skill_hook_config(
        _config(
            {
                "enabled": "maybe",
                "mode": "always",
                "output": "full",
                "top_k": 0,
                "min_score": -1,
                "log_level": "trace",
            },
        ),
    )

    assert result == SkillHookConfig(
        enabled=True,
        mode=MODE_ADAPTIVE,
        output=OUTPUT_SHORTLIST,
        top_k=3,
        min_score=2,
        log_level="INFO",
    )


def test_load_skill_hook_config_env_log_level_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment loglevel overrides config loglevel."""
    monkeypatch.setenv(ENV_LOG_LEVEL, "warning")

    result = load_skill_hook_config(_config({"log_level": "debug"}))

    assert result.log_level == "WARNING"


def test_load_skill_hook_config_accepts_bool_and_true_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bool and true-like string values are normalized."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)

    result = load_skill_hook_config(_config({"enabled": True, "min_score": True}))

    assert result.enabled is True
    assert result.min_score == 2


@pytest.mark.parametrize(
    "raw",
    [
        {"plugins": []},
        {"plugins": {"entries": []}},
        {"plugins": {"entries": {"easter-hermes-sorry-skills-plugin": []}}},
        {"plugins": {"entries": {"easter-hermes-sorry-skills-plugin": {"skill_hook": []}}}},
    ],
)
def test_load_skill_hook_config_malformed_tree_uses_defaults(
    monkeypatch: pytest.MonkeyPatch,
    raw: dict[str, object],
) -> None:
    """Malformed config tree is treated like missing config."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)

    assert load_skill_hook_config(raw) == SkillHookConfig()


def test_load_skill_hook_config_without_explicit_config_uses_import_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No explicit config stays safe when Hermes config is unavailable."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    monkeypatch.setattr(os, "environ", {})

    assert load_skill_hook_config() == SkillHookConfig()


def test_load_skill_hook_config_imports_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default path reads Hermes config when it is importable."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    hermes_module = types.ModuleType("hermes_cli")
    config_module = types.ModuleType("hermes_cli.config")
    config_module.load_config = lambda: _config({"enabled": "yes"})
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_module)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_module)

    assert load_skill_hook_config().enabled is True


def test_load_skill_hook_config_ignores_non_dict_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-dict Hermes config payloads are ignored."""
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    hermes_module = types.ModuleType("hermes_cli")
    config_module = types.ModuleType("hermes_cli.config")
    config_module.load_config = lambda: []
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_module)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_module)

    assert load_skill_hook_config() == SkillHookConfig()


def test_call_load_config_fails_open_on_loader_error() -> None:
    """Hermes config loader errors become empty config."""

    def _boom() -> object:
        raise OSError("boom")

    assert _call_load_config(_boom) == {}
