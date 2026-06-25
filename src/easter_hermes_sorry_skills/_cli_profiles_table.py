"""Rich-table renderer for the ``profiles`` CLI (Phase B).

TDD test cases for this module (see tests/unit/test_cli_profiles_table.py):
  test_build_profile_table_with_5_enabled_skills
  test_build_profile_table_empty_profile
  test_build_profile_table_with_fallback_badge
  test_render_all_profiles_json_structure
  test_render_all_profiles_table_output_uses_console

Two public functions:
- ``build_profile_table`` returns a ``rich.table.Table`` for one profile
  (columns: ``#``, ``Skill``, ``Description``, ``Tokens``). The last row
  is a section-ending summary footer carrying the
  ``"{n} skills · {tokens} tokens"`` text — suffixed with ``(est.)`` when
  any row was produced via the chars/4 fallback.
- ``render_all_profiles`` emits the tables (or a JSON dump) to a
  ``rich.console.Console``. The ``--json`` flag in the parent CLI gates
  the format.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from rich.console import Console
from rich.table import Table

from easter_hermes_sorry_skills._cli_profiles_skill import EnabledSkillRow

_TOOL_NAME = "easter-hermes-sorry-skills-profiles"
_TOOL_VERSION = "0.1.0"

# Column specs: (header, width, justify).
_COLUMNS: tuple[tuple[str, int, str], ...] = (
    ("#", 4, "left"),
    ("Skill", 24, "left"),
    ("Description", 80, "left"),
    ("Tokens", 8, "right"),
)

_DESCRIPTION_TRUNCATE_LIMIT = 79
_DESCRIPTION_TRUNCATE_SUFFIX = "…"

# JSON key literals — extracted to constants to keep WPS226 happy
# (any one literal must not appear more than 3 times in a scope).
_KEY_NAME = "name"
_KEY_DESCRIPTION = "description"
_KEY_TOKEN_COUNT = "token_count"
_KEY_SKILL_COUNT = "skill_count"
_KEY_TOKEN_TOTAL = "token_total"
_KEY_TOKEN_SOURCE = "token_source"
_KEY_ENABLED_SKILLS = "enabled_skills"
_KEY_WARNINGS = "warnings"
# Internal dict keys for the collector helper return payload — kept
# separate from the public JSON keys above so the literal "warnings"
# stays out of multiple scopes.
KEY_PROFILES = "profiles"
KEY_GLOBAL_WARNINGS = "warnings"


def build_profile_table(
    profile_name: str,
    rows: list[EnabledSkillRow],
    summary: dict[str, Any],
) -> Table:
    """Return a rich.Table for a single profile with a summary footer row."""
    table = Table(title=profile_name, show_lines=False)
    for header, width, justify in _COLUMNS:
        table.add_column(header, width=width, justify=justify)
    _add_data_rows(table, rows)
    _add_summary_footer(table, summary)
    return table


def render_all_profiles(
    _profile_entries: list[_ProfileTuple],
    *,
    as_json: bool,
    console: Console,
) -> None:
    """Render ``_profile_entries`` either as text tables or as a JSON dump."""
    if as_json:
        payload = _json_payload(_profile_entries)
        console.print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for _name, table, _summary in _profile_entries:
        console.print(table)


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _add_data_rows(table: Table, rows: list[EnabledSkillRow]) -> None:
    """Append one row per skill with a truncated description."""
    for index, row in enumerate(rows, start=1):
        description = row.description
        if len(description) > _DESCRIPTION_TRUNCATE_LIMIT:
            description = description[:_DESCRIPTION_TRUNCATE_LIMIT] + _DESCRIPTION_TRUNCATE_SUFFIX
        table.add_row(str(index), row.name, description, str(row.token_count))


def _add_summary_footer(table: Table, summary: dict[str, Any]) -> None:
    """Append the section-ending summary footer (text in the wide column)."""
    skill_count = int(summary.get(_KEY_SKILL_COUNT, 0))
    token_total = int(summary.get(_KEY_TOKEN_TOTAL, 0))
    source = summary.get(_KEY_TOKEN_SOURCE, "tokenizer")
    badge = " (est.)" if source == "chars_div_4" else ""
    footer = f"{skill_count} skills · {token_total} tokens{badge}"
    table.add_row("", "", footer, "", end_section=True)


def _json_payload(_profile_entries: list[_ProfileTuple]) -> dict[str, Any]:
    """Build the JSON-serialisable top-level payload from the per-profile entries."""
    collected = _collect_profiles_and_warnings(_profile_entries)
    return {
        "tool": _TOOL_NAME,
        "version": _TOOL_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "profile_count": len(collected[KEY_PROFILES]),
        KEY_PROFILES: collected[KEY_PROFILES],
        _KEY_WARNINGS: collected[KEY_GLOBAL_WARNINGS],
    }


def _collect_profiles_and_warnings(
    _profile_entries: list[_ProfileTuple],
) -> dict[str, Any]:
    """Walk the entries once, returning per-profile blocks and aggregated warnings."""
    profiles: list[dict[str, Any]] = []
    warnings: list[str] = []
    for name, _table, summary in _profile_entries:
        profiles.append(_profile_entry(name, summary))
        warnings.extend(map(str, summary.get(_KEY_WARNINGS, []) or []))
    return {KEY_PROFILES: profiles, KEY_GLOBAL_WARNINGS: warnings}


def _profile_entry(name: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Project the per-profile summary into the JSON-friendly profile entry."""
    enabled: list[dict[str, Any]] = []
    for entry in summary.get(_KEY_ENABLED_SKILLS, []) or []:
        if isinstance(entry, EnabledSkillRow):
            enabled.append(
                {
                    _KEY_NAME: entry.name,
                    _KEY_DESCRIPTION: entry.description,
                    _KEY_TOKEN_COUNT: entry.token_count,
                }
            )
        elif isinstance(entry, dict):
            enabled.append(
                {
                    _KEY_NAME: entry.get(_KEY_NAME, ""),
                    _KEY_DESCRIPTION: entry.get(_KEY_DESCRIPTION, ""),
                    _KEY_TOKEN_COUNT: int(entry.get(_KEY_TOKEN_COUNT, 0)),
                }
            )
    return {
        _KEY_NAME: summary.get(_KEY_NAME, name),
        _KEY_SKILL_COUNT: int(summary.get(_KEY_SKILL_COUNT, 0)),
        _KEY_TOKEN_TOTAL: int(summary.get(_KEY_TOKEN_TOTAL, 0)),
        _KEY_TOKEN_SOURCE: summary.get(_KEY_TOKEN_SOURCE, "tokenizer"),
        _KEY_ENABLED_SKILLS: enabled,
    }


# Type alias for the (name, table, summary) tuple used by ``render_all_profiles``.
# Extracted to keep WPS234 happy: a single-parameter alias beats a
# nested four-parameter annotation at every call site.
_ProfileTuple = tuple[str, "Table", dict[str, Any]]
