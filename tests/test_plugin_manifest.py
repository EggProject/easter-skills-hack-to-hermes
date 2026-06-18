"""tests/test_plugin_manifest.py — TDD tests for the plugin.yaml manifest.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.1, AC-1.5

TDD list (from plan):
  test_plugin_manifest_is_yaml_not_json
  test_plugin_manifest_passes_hermes_parser
  test_plugin_manifest_has_no_kind_field
  test_plugin_manifest_has_no_entry_points
  test_register_callable_in_package_init
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "src" / "hermes_skill_creator_plugin"
MANIFEST_PATH = PLUGIN_ROOT / "plugin.yaml"


def test_plugin_manifest_is_yaml_not_json() -> None:
    """The bundled manifest is plugin.yaml (NOT plugin.json)."""
    assert MANIFEST_PATH.exists(), f"missing manifest at {MANIFEST_PATH}"
    bad = PLUGIN_ROOT / "plugin.json"
    assert not bad.exists(), "plugin.json must NOT exist at the plugin root (B3 fix)"


def test_plugin_manifest_parses_as_yaml() -> None:
    """Parses as YAML, not JSON."""
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_plugin_manifest_passes_hermes_parser() -> None:
    """Acceptance gate: name matches [a-z0-9][a-z0-9._-]*$, description len <= 1024,
    provides_hooks is a list containing 'on_session_start'."""
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    name = data["name"]
    assert isinstance(name, str)
    assert re.match(r"^[a-z0-9][a-z0-9._-]*$", name), f"invalid plugin name: {name!r}"
    description = data.get("description", "")
    assert isinstance(description, str)
    assert len(description) <= 1024, f"description too long: {len(description)}"
    hooks = data.get("provides_hooks", [])
    assert isinstance(hooks, list)
    assert "on_session_start" in hooks


def test_plugin_manifest_has_no_kind_field() -> None:
    """Asserts the bundled plugin.yaml does NOT carry a `kind` field.

    kind defaults to 'standalone' when omitted (hermes_cli/plugins.py:263,
    .get idiom at :1415)."""
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "kind" not in data, "kind field must be omitted (defaults to standalone)"


def test_plugin_manifest_has_no_entry_points() -> None:
    """Asserts the bundled plugin.yaml does NOT carry an `entry_points` map
    (the load model is one `register(ctx)` in `__init__.py`, not an entry-point map)."""
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "entry_points" not in data, "entry_points map is forbidden (B3 fix)"


def test_register_callable_in_package_init() -> None:
    """`from hermes_skill_creator_plugin import register` resolves to a callable."""
    from hermes_skill_creator_plugin import register

    assert callable(register)
