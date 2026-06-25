"""Unit tests for ``_cli_profiles_table`` (Phase B).

TDD list:
- test_build_profile_table_with_5_enabled_skills
- test_build_profile_table_empty_profile
- test_build_profile_table_with_fallback_badge
- test_render_all_profiles_json_structure
- test_render_all_profiles_table_output_uses_console

The module wraps ``rich.table.Table`` to produce a per-profile report and
``rich.console.Console`` to render either text tables or a structured JSON
dump (gated by the ``--json`` CLI flag).
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock

from rich.console import Console
from rich.table import Table

from easter_hermes_sorry_skills._cli_profiles_skill import EnabledSkillRow
from easter_hermes_sorry_skills._cli_profiles_table import (
    build_profile_table,
    render_all_profiles,
)


def _row(name: str, desc: str, tokens: int, source: str = "tokenizer") -> EnabledSkillRow:
    return EnabledSkillRow(
        name=name,
        description=desc,
        token_count=tokens,
        token_source=source,  # type: ignore[arg-type]
    )


def test_build_profile_table_with_5_enabled_skills() -> None:
    """5 rows → table has 5 data rows + 1 summary footer row.

    The footer text reads ``"5 skills · 50 tokens"`` (no ``(est.)`` badge
    when every row's ``token_source == "tokenizer"``).
    """
    rows = [_row(f"skill-{i}", f"description {i}", 10) for i in range(5)]
    summary = {"skill_count": 5, "token_total": 50, "token_source": "tokenizer", "warnings": []}
    table = build_profile_table("hermes", rows, summary)

    # 5 data rows + 1 footer row (end_section=True).
    assert table.row_count == 6

    rendered = _render_to_text(table)
    assert "5 skills · 50 tokens" in rendered
    # No fallback badge.
    assert "(est.)" not in rendered


def test_build_profile_table_empty_profile() -> None:
    """0 rows → only the summary footer row exists."""
    summary = {"skill_count": 0, "token_total": 0, "token_source": "tokenizer", "warnings": []}
    table = build_profile_table("hermes", [], summary)

    # Only the summary footer.
    assert table.row_count == 1
    rendered = _render_to_text(table)
    assert "0 skills · 0 tokens" in rendered


def test_build_profile_table_with_fallback_badge() -> None:
    """When ``token_source == "chars_div_4"``, the footer carries ``(est.)``."""
    rows = [_row("alpha", "x", 10, source="chars_div_4")]
    summary = {
        "skill_count": 1,
        "token_total": 10,
        "token_source": "chars_div_4",
        "warnings": [],
    }
    table = build_profile_table("hermes", rows, summary)
    rendered = _render_to_text(table)
    assert "(est.)" in rendered
    assert "1 skills · 10 tokens (est.)" in rendered


def test_render_all_profiles_json_structure() -> None:
    """``as_json=True`` emits parseable JSON with the documented top-level keys."""
    rows = [_row("alpha", "first skill", 12)]
    summary = {
        "name": "hermes",
        "skill_count": 1,
        "token_total": 12,
        "token_source": "tokenizer",
        "warnings": ["warn-1"],
        "enabled_skills": rows,
    }
    table = build_profile_table("hermes", rows, summary)

    console = Console(file=StringIO(), record=True)
    render_all_profiles([("hermes", table, summary)], as_json=True, console=console)

    output = console.export_text()
    # The Console captures the JSON dump via stdout file.
    assert output  # non-empty

    parsed = json.loads(output)
    assert parsed["tool"] == "easter-hermes-sorry-skills-profiles"
    assert parsed["version"] == "0.1.0"
    assert "generated_at" in parsed
    assert parsed["profile_count"] == 1
    assert parsed["profiles"][0]["name"] == "hermes"
    assert parsed["profiles"][0]["enabled_skills"][0]["name"] == "alpha"
    assert parsed["warnings"] == ["warn-1"]


def test_render_all_profiles_table_output_uses_console() -> None:
    """``as_json=False`` uses ``Console.print`` to emit the tables."""
    rows = [_row("alpha", "x", 5)]
    summary = {
        "skill_count": 1,
        "token_total": 5,
        "token_source": "tokenizer",
        "warnings": [],
        "enabled_skills": rows,
    }
    table = build_profile_table("hermes", rows, summary)

    fake_console = MagicMock(spec=Console)
    render_all_profiles([("hermes", table, summary)], as_json=False, console=fake_console)

    # The Console.print(Table) call was issued at least once.
    printed_objects = [call.args[0] for call in fake_console.print.call_args_list]
    assert any(isinstance(obj, Table) for obj in printed_objects)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _render_to_text(table: Table) -> str:
    """Render a rich.Table to text via a temporary Console."""
    console = Console(file=StringIO(), record=True, width=200)
    console.print(table)
    return console.export_text()
