"""tests/test_i18n.py — TDD tests for the single-language i18n constants.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.2

Single-language contract (no bilingual in-line format):
  - ``messages_en.ADVISORY_CAP`` is a plain English string (no `[hu]` text,
    no Hungarian diacritics).
  - ``messages_hu.ADVISORY_CAP`` is a plain Hungarian string (no `[en]` text).
  - ``pick(lang)`` returns ``messages_en`` for ``"en"``/empty/unknown,
    ``messages_hu`` for ``"hu"``.
  - No module constant may contain ``"[en]"``, ``"[hu]"``, ``"/ [hu]"``,
    or ``"/ [en]"`` substrings.
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _i18n_pick
from easter_hermes_sorry_skills.i18n import messages_en, messages_hu

# Hungarian diacritics that MUST NOT appear in the English module.
_HU_DIACRITICS = ("é", "á", "ő", "ű", "ö", "ü", "ó")


def _all_string_constants(module: object) -> list[tuple[str, str]]:
    """Return every uppercase string constant defined on ``module``."""
    result: list[tuple[str, str]] = []
    for name in vars(module):
        if not name.isupper():
            continue
        value = getattr(module, name)
        if isinstance(value, str):
            result.append((name, value))
    return result


def test_messages_en_is_plain_english() -> None:
    """Every messages_en.* constant must be plain English text."""
    for name, value in _all_string_constants(messages_en):
        assert "[hu]" not in value, f"messages_en.{name} contains [hu] substring (should be plain English): {value!r}"
        assert "[en]" not in value, f"messages_en.{name} contains [en] marker (should be plain English): {value!r}"
        for ch in _HU_DIACRITICS:
            assert ch not in value, f"messages_en.{name} contains Hungarian diacritic {ch!r}: {value!r}"


def test_messages_hu_is_plain_hungarian() -> None:
    """Every messages_hu.* constant must be plain Hungarian text."""
    for name, value in _all_string_constants(messages_hu):
        assert "[en]" not in value, f"messages_hu.{name} contains [en] substring (should be plain Hungarian): {value!r}"
        assert "[hu]" not in value, f"messages_hu.{name} contains [hu] marker (should be plain Hungarian): {value!r}"


def test_advisory_cap_exists_in_both_modules() -> None:
    """Both modules must export ADVISORY_CAP."""
    assert hasattr(messages_en, "ADVISORY_CAP"), "messages_en.ADVISORY_CAP is missing"
    assert hasattr(messages_hu, "ADVISORY_CAP"), "messages_hu.ADVISORY_CAP is missing"
    assert isinstance(messages_en.ADVISORY_CAP, str)
    assert isinstance(messages_hu.ADVISORY_CAP, str)


def test_pick_returns_correct_module() -> None:
    """pick(lang) returns the right module for each input."""
    assert _i18n_pick.pick("en") is messages_en
    assert _i18n_pick.pick("hu") is messages_hu
    assert _i18n_pick.pick("") is messages_en
    assert _i18n_pick.pick("xx") is messages_en


def test_no_bilingual_format_in_modules() -> None:
    """No constant in either module may contain the bilingual-format separator."""
    for module in (messages_en, messages_hu):
        for name, value in _all_string_constants(module):
            assert "/ [hu]" not in value, f"{module.__name__}.{name} contains '/ [hu]' substring: {value!r}"
            assert "/ [en]" not in value, f"{module.__name__}.{name} contains '/ [en]' substring: {value!r}"


def test_no_brackets_in_modules() -> None:
    """No constant may contain a [en] or [hu] marker."""
    for module in (messages_en, messages_hu):
        for name, value in _all_string_constants(module):
            assert "[en]" not in value, f"{module.__name__}.{name} contains '[en]' marker: {value!r}"
            assert "[hu]" not in value, f"{module.__name__}.{name} contains '[hu]' marker: {value!r}"
