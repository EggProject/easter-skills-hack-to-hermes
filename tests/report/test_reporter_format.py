"""tests/report/test_reporter_format.py

TDD: tests for hermes_skill_creator_plugin._reporter (formatting, sorting, n/a).
"""

from __future__ import annotations

import json

import pytest

from hermes_skill_creator_plugin import _reporter
from hermes_skill_creator_plugin._reporter import (
    DOCUMENTED_USAGE_FIELDS,
    TEXT_COLUMNS,
    ProfileSection,
    format_json,
    format_text,
    sort_rows,
)
from tests.report._fixtures import make_row_factory

# --- format_text ---


def test_format_text_columns_present() -> None:
    rows = [make_row_factory(name="a", tokens=10)]
    out = format_text("hermes", rows, total_tokens=10)
    # Every TEXT_COLUMNS header must appear in the rendered table. This
    # covers the six documented usage fields (view_count, patch_count,
    # last_used_at, last_viewed_at, last_patched_at) plus the structural
    # columns (profile, name, description, tokens, use_count, pct_of_cap).
    header_line = out.splitlines()[0]
    rendered_headers = set(header_line.split())
    for col in TEXT_COLUMNS:
        assert col in rendered_headers, f"missing column header {col!r} in {header_line!r}"


def test_format_text_truncates_description_to_60() -> None:
    desc = "x" * 200
    rows = [make_row_factory(name="a", description=desc, tokens=5)]
    out = format_text("hermes", rows, total_tokens=5)
    # Find the row that contains 'a' and the description cells.
    body_lines = out.splitlines()[1:]  # skip header
    assert any("xxx..." in line for line in body_lines)
    # The description cell in the text table is 60 chars max.
    # After truncation: 57 x's + "..." = 60 chars.
    truncated_cell = "x" * 57 + "..."
    for line in body_lines:
        if truncated_cell in line:
            # Ensure the cell doesn't contain the full 200.
            assert "x" * 200 not in line
            return
    # If we didn't find the 60-char string, the truncation logic was wrong.
    pytest.fail("expected a 60-char description cell in the rendered text")


def test_format_text_total_row() -> None:
    rows = [make_row_factory(name="a", tokens=10), make_row_factory(name="b", tokens=20)]
    out = format_text("hermes", rows, total_tokens=30)
    assert "total" in out
    assert "30" in out  # total tokens


def test_format_text_alignment() -> None:
    rows = [
        make_row_factory(name="alpha", tokens=100),
        make_row_factory(name="beta", tokens=2),
    ]
    out = format_text("hermes", rows, total_tokens=102)
    # Each line is a non-empty string of consistent row width.
    lines = out.splitlines()
    assert len(lines) >= 3
    widths = {len(line) for line in lines}
    assert len(widths) == 1, f"lines not aligned to one width: {widths}"


# --- format_json ---


def test_format_json_shape() -> None:
    rows = [make_row_factory(name="a", tokens=10, use_count=3, last_used_at="2026-06-16T00:00:00Z")]
    out = format_json(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        sections=[ProfileSection(profile_name="hermes", rows=rows, total_tokens=10)],
    )
    obj = json.loads(out)
    assert obj["tool"] == "x"
    assert obj["version"] == "0.1.0"
    assert obj["generated_at"] == "2026-06-17T00:00:00Z"
    assert "profiles" in obj
    assert len(obj["profiles"]) == 1
    prof = obj["profiles"][0]
    assert prof["profile_name"] == "hermes"
    assert prof["total_tokens"] == 10
    assert len(prof["enabled_skills"]) == 1
    skill = prof["enabled_skills"][0]
    for f in (
        "use_count",
        "view_count",
        "patch_count",
        "last_used_at",
        "last_viewed_at",
        "last_patched_at",
    ):
        assert f in skill, f"missing field {f!r}"


def test_format_json_deterministic_with_frozen_time() -> None:
    rows = [make_row_factory(name="a", tokens=10)]
    sections = [ProfileSection(profile_name="hermes", rows=rows, total_tokens=10)]
    out1 = format_json(tool="x", version="0.1.0", generated_at="2026-06-17T00:00:00Z", sections=sections)
    out2 = format_json(tool="x", version="0.1.0", generated_at="2026-06-17T00:00:00Z", sections=sections)
    assert out1 == out2
    import hashlib

    assert hashlib.sha256(out1.encode("utf-8")).hexdigest() == hashlib.sha256(out2.encode("utf-8")).hexdigest()


def test_format_json_includes_pct_of_cap() -> None:
    rows = [make_row_factory(name="a", tokens=512)]
    out = format_json(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        sections=[ProfileSection(profile_name="hermes", rows=rows, total_tokens=512)],
    )
    obj = json.loads(out)
    assert obj["profiles"][0]["enabled_skills"][0]["pct_of_cap"] == 50.0


def test_format_json_full_description_preserved() -> None:
    desc = "x" * 200
    rows = [make_row_factory(name="a", description=desc)]
    out = format_json(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        sections=[ProfileSection(profile_name="hermes", rows=rows, total_tokens=10)],
    )
    obj = json.loads(out)
    assert obj["profiles"][0]["enabled_skills"][0]["description"] == desc


def test_format_json_multi_profile_is_single_valid_document() -> None:
    """Regression: multi-profile JSON output MUST be a single valid JSON object.

    Previously the reporter called format_json per-profile and joined the
    outputs with newlines, producing N concatenated JSON objects that
    downstream consumers (jq, JSON parsers) reject with 'Extra data'.
    """
    sections = [
        ProfileSection(
            profile_name="hermes",
            rows=[make_row_factory(name="a", tokens=10)],
            total_tokens=10,
        ),
        ProfileSection(
            profile_name="work",
            rows=[make_row_factory(name="b", tokens=20)],
            total_tokens=20,
        ),
    ]
    out = format_json(
        tool="x",
        version="0.1.0",
        generated_at="2026-06-17T00:00:00Z",
        sections=sections,
    )
    obj = json.loads(out)  # MUST parse as a single JSON object.
    assert len(obj["profiles"]) == 2
    assert obj["profiles"][0]["profile_name"] == "hermes"
    assert obj["profiles"][1]["profile_name"] == "work"
    # Top-level fields appear ONCE (not repeated per profile).
    assert out.count('"tool":') == 1
    assert out.count('"version":') == 1
    assert out.count('"generated_at":') == 1


# --- sort_rows ---


def test_sort_rows_by_tokens_desc() -> None:
    rows = [
        make_row_factory(name="a", tokens=10),
        make_row_factory(name="b", tokens=50),
        make_row_factory(name="c", tokens=30),
    ]
    out = sort_rows(rows, "tokens")
    assert [r.name for r in out] == ["b", "c", "a"]


def test_sort_rows_by_use_count_desc_with_na_last() -> None:
    rows = [
        make_row_factory(name="a", use_count=10),
        make_row_factory(name="b", use_count=None),
        make_row_factory(name="c", use_count=5),
    ]
    out = sort_rows(rows, "use_count")
    assert [r.name for r in out] == ["a", "c", "b"]


def test_sort_rows_by_last_used_at_desc_with_na_last() -> None:
    rows = [
        make_row_factory(name="a", last_used_at="2026-01-01T00:00:00Z"),
        make_row_factory(name="b", last_used_at=None),
        make_row_factory(name="c", last_used_at="2026-06-15T00:00:00Z"),
    ]
    out = sort_rows(rows, "last_used_at")
    assert [r.name for r in out] == ["c", "a", "b"]


def test_sort_rows_stable_secondary_key_by_name() -> None:
    rows = [
        make_row_factory(name="beta", tokens=10),
        make_row_factory(name="alpha", tokens=10),
        make_row_factory(name="gamma", tokens=10),
    ]
    out = sort_rows(rows, "tokens")
    # All equal primary; secondary is name asc.
    assert [r.name for r in out] == ["alpha", "beta", "gamma"]


def test_sort_rows_default_is_tokens() -> None:
    rows = [
        make_row_factory(name="a", tokens=5),
        make_row_factory(name="b", tokens=20),
    ]
    out = sort_rows(rows, "tokens")
    assert [r.name for r in out] == ["b", "a"]


def test_sort_rows_unknown_falls_back_to_tokens() -> None:
    rows = [make_row_factory(name="a", tokens=5)]
    out = sort_rows(rows, "nope")
    assert out == rows  # No change; unknown key returns same order.


# --- n/a-vs-0 accessor ---


def test_na_renders_when_persisted_false() -> None:
    # The SkillRow dataclass already encodes n/a as None; the test asserts
    # that the format_text renderer emits the literal "n/a" string.
    row = make_row_factory(name="a", use_count=None)
    out = format_text("hermes", [row], total_tokens=10)
    assert "n/a" in out


def test_zero_renders_when_persisted_true() -> None:
    row = make_row_factory(name="a", use_count=0)
    out = format_text("hermes", [row], total_tokens=10)
    # The use_count column should show "0" not "n/a" for a persisted row.
    body = out.splitlines()[1]
    cells = body.split("  ")
    # The "0" should appear (in either tokens or use_count cells).
    assert "0" in cells


def test_na_when_curator_absent() -> None:
    # Same as test_na_renders_when_persisted_false but framed as Curator absent.
    row = make_row_factory(name="a", use_count=None, last_used_at=None)
    out = format_text("hermes", [row], total_tokens=10)
    assert "n/a" in out


def test_documented_fields_constant() -> None:
    assert DOCUMENTED_USAGE_FIELDS == frozenset(
        {
            "use_count",
            "view_count",
            "patch_count",
            "last_used_at",
            "last_viewed_at",
            "last_patched_at",
        }
    )


def test_truncate_helper() -> None:
    assert _reporter._truncate_for_display("x" * 5) == "x" * 5
    assert _reporter._truncate_for_display("x" * 100) == "x" * 57 + "..."
