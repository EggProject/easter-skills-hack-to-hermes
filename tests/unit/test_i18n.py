"""tests/unit/test_i18n.py — Regression tests for bilingual i18n messages.

These tests guard against the LOW-1 finding flagged by the security-auditor:
the ``[en] `` / ``[hu] `` halves of every bilingual single-string message in
``messages_en.py`` / ``messages_hu.py`` must each contain ONLY the language
they claim to (the ``[en]`` half may not contain Hungarian text, and vice
versa). A swap of the two halves — like the one in ``DRY_RUN_NOT_APPLIED``
prior to the fix — silently corrupts the audit trail of bilingual output
because the marker is in the wrong half.

Pattern reference: plans/10-toolchain-and-conventions.md:
  - ``messages_en.py`` uses ``"[en] <text> / [hu] <text>"`` format
  - ``messages_hu.py`` uses ``"[hu] <text> / [en] <text>"`` format
  - In both files, the half whose leading marker matches the file's leading
    marker MUST be written in that language.
"""

from __future__ import annotations

import re

import pytest

from easter_hermes_sorry_skills.i18n import messages_en, messages_hu

# Markers used to find the [en] / [hu] halves inside a single bilingual string.
_EN_HALF = re.compile(r"^\[en\]\s*(?P<body>.+?)\s*/\s*\[hu\]\s*(?P<rest>.+)$", re.DOTALL)
_HU_HALF = re.compile(r"^\[hu\]\s*(?P<body>.+?)\s*/\s*\[en\]\s*(?P<rest>.+)$", re.DOTALL)

# Strings that MUST NOT appear in the English half (Hungarian markers/words).
_HU_FORBIDDEN_SUBSTRINGS = (
    "FIGYELEM",
    "figyelmeztetés",
    "módban",
    "terv",
    "alkalmazva",
    "patchelné",
    "sor-eltérés",
    "megtagadva",
    "kötelező",
    "sikertelen",
    "körkörös",
    "engedélyezett",
    "figyelmen kívül",
)

# Hungarian diacritics that MUST NOT appear in the English half. If any of
# these show up in an "[en] " block, the half was written in Hungarian.
_HU_DIACRITICS = ("é", "á", "ő", "ű", "ö", "ü", "ó")

# Strings that MUST NOT appear in the Hungarian half (English markers/words).
_EN_FORBIDDEN_SUBSTRINGS = (
    "WARNING",
    "would patch",
    "would be applied",
    "were NOT applied",
    "patches were NOT",
    "patches applied",
    "already patched",
    "patched successfully",
    "permission denied",
    "I/O error",
    "different filesystems",
    "text drift",
    "line drift",
    "circular import",
    "refusing to patch",
    "is required",
    "missing",
)


def _en_half(text: str) -> str:
    """Return the substring that follows the leading ``[en] `` marker.

    Raises ``ValueError`` if ``text`` does not start with ``[en] ``.
    """
    match = _EN_HALF.match(text)
    if match is None:
        raise ValueError(f"text does not start with [en] / [hu] format: {text!r}")
    return match.group("body")


def _hu_half(text: str) -> str:
    """Return the substring that follows the leading ``[hu] `` marker."""
    match = _HU_HALF.match(text)
    if match is None:
        raise ValueError(f"text does not start with [hu] / [en] format: {text!r}")
    return match.group("body")


# ---------------------------------------------------------------------------
# Names of every bilingual single-string constant added/changed on the
# fix/dry-run-soft-safety-and-plan branch. The test parametrizes over this
# list so adding a new bilingual constant is a one-line update.
# ---------------------------------------------------------------------------
_BILINGUAL_CONSTANTS = (
    "DRY_RUN_PLAN_HEADER",
    "DRY_RUN_PREFLIGHT_WARNING",
    "DRY_RUN_PATCH_LINE",
    "DRY_RUN_DIFF_LINE_OLD",
    "DRY_RUN_DIFF_LINE_NEW",
    "DRY_RUN_PLAN_SUMMARY",
    "DRY_RUN_NOT_APPLIED",
    "DRY_RUN_APPLIED",
)


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_en_dry_run_constants_match_bilingual_shape(name: str) -> None:
    """Every DRY_RUN_* constant in messages_en.py must parse as
    ``[en] <english> / [hu] <hungarian>``."""
    value = getattr(messages_en, name)
    assert isinstance(value, str)
    # Round-trip through _en_half to confirm the shape is valid.
    body = _en_half(value)
    assert body, f"{name} has empty [en] half"


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_hu_dry_run_constants_match_bilingual_shape(name: str) -> None:
    """Every DRY_RUN_* constant in messages_hu.py must parse as
    ``[hu] <hungarian> / [en] <english>``."""
    value = getattr(messages_hu, name)
    assert isinstance(value, str)
    body = _hu_half(value)
    assert body, f"{name} has empty [hu] half"


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_en_dry_run_english_half_is_english(name: str) -> None:
    """The [en] half of every messages_en.DRY_RUN_* constant must not
    contain Hungarian diacritics or Hungarian markers/words."""
    value = getattr(messages_en, name)
    body = _en_half(value)
    for ch in _HU_DIACRITICS:
        assert ch not in body, f"{name}: [en] half contains Hungarian diacritic {ch!r}: {value!r}"
    for forbidden in _HU_FORBIDDEN_SUBSTRINGS:
        assert forbidden not in body, f"{name}: [en] half contains Hungarian substring {forbidden!r}: {value!r}"


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_en_dry_run_hungarian_half_is_hungarian(name: str) -> None:
    """The [hu] half of every messages_en.DRY_RUN_* constant must not
    contain English-only markers/words."""
    value = getattr(messages_en, name)
    match = _EN_HALF.match(value)
    assert match is not None
    hu_body = match.group("rest")
    for forbidden in _EN_FORBIDDEN_SUBSTRINGS:
        assert forbidden not in hu_body, f"{name}: [hu] half contains English substring {forbidden!r}: {value!r}"


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_hu_dry_run_hungarian_half_is_hungarian(name: str) -> None:
    """The [hu] half of every messages_hu.DRY_RUN_* constant must not
    contain English-only markers/words."""
    value = getattr(messages_hu, name)
    body = _hu_half(value)
    for forbidden in _EN_FORBIDDEN_SUBSTRINGS:
        assert forbidden not in body, f"{name}: [hu] half contains English substring {forbidden!r}: {value!r}"


@pytest.mark.parametrize("name", _BILINGUAL_CONSTANTS)
def test_messages_hu_dry_run_english_half_is_english(name: str) -> None:
    """The [en] half of every messages_hu.DRY_RUN_* constant must not
    contain Hungarian diacritics or Hungarian markers/words."""
    value = getattr(messages_hu, name)
    match = _HU_HALF.match(value)
    assert match is not None
    en_body = match.group("rest")
    for ch in _HU_DIACRITICS:
        assert ch not in en_body, f"{name}: [en] half contains Hungarian diacritic {ch!r}: {value!r}"
    for forbidden in _HU_FORBIDDEN_SUBSTRINGS:
        assert forbidden not in en_body, f"{name}: [en] half contains Hungarian substring {forbidden!r}: {value!r}"


# ---------------------------------------------------------------------------
# LOW-1 regression: the specific constant that was swapped.
# ---------------------------------------------------------------------------
def test_messages_en_dry_run_not_applied_has_english_first_half() -> None:
    """Regression for LOW-1: ``messages_en.DRY_RUN_NOT_APPLIED`` must
    start with an English ``[en] WARNING: ...`` half, NOT a Hungarian
    ``[en] FIGYELEM: ...`` half."""
    value = messages_en.DRY_RUN_NOT_APPLIED
    body = _en_half(value)
    assert "WARNING" in body, f"[en] half must contain English marker WARNING: {value!r}"
    assert "FIGYELEM" not in body, f"[en] half must NOT contain Hungarian marker FIGYELEM: {value!r}"
    assert "módban" not in body, f"[en] half must NOT contain Hungarian 'módban': {value!r}"


def test_messages_hu_dry_run_not_applied_has_hungarian_first_half() -> None:
    """Regression for LOW-1: ``messages_hu.DRY_RUN_NOT_APPLIED`` must
    start with a Hungarian ``[hu] FIGYELEM: ...`` half, NOT an English
    ``[hu] WARNING: ...`` half."""
    value = messages_hu.DRY_RUN_NOT_APPLIED
    body = _hu_half(value)
    assert "FIGYELEM" in body, f"[hu] half must contain Hungarian marker FIGYELEM: {value!r}"
    assert "WARNING" not in body, f"[hu] half must NOT contain English marker WARNING: {value!r}"
    assert "patches were NOT" not in body, f"[hu] half must NOT contain English 'patches were NOT': {value!r}"
