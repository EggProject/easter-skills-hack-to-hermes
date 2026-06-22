"""tests/test_i18n_bilingual.py — TDD tests for the bilingual advisory strings.

Plan file: docs/plans/03-plugin-spec.md
ACs covered: AC-1.2

TDD list (from plan):
  test_advisory_log_contains_en_and_hu
"""

from __future__ import annotations

import re

# Pattern required by plans/10-toolchain-and-conventions.md:
#   ^\[en\] .+ / \[hu\] .+$
BILINGUAL_LINE = re.compile(r"^\[en\] .+ / \[hu\] .+$")


def test_advisory_composed_line_matches_bilingual_pattern() -> None:
    """The composed EN/HU line (built in register) must match the bilingual
    pattern `^[en] ... / [hu] ...$` on a single line."""
    from easter_hermes_sorry_skills.i18n.messages_en import ADVISORY_CAP_EN
    from easter_hermes_sorry_skills.i18n.messages_hu import ADVISORY_CAP_HU

    composed = f"{ADVISORY_CAP_EN} / {ADVISORY_CAP_HU}"
    assert BILINGUAL_LINE.match(composed), f"composed bilingual line does not match pattern: {composed!r}"


def test_advisory_cap_en_has_en_marker() -> None:
    from easter_hermes_sorry_skills.i18n.messages_en import ADVISORY_CAP_EN

    assert ADVISORY_CAP_EN.startswith("[en] ")


def test_advisory_cap_hu_has_hu_marker() -> None:
    from easter_hermes_sorry_skills.i18n.messages_hu import ADVISORY_CAP_HU

    assert ADVISORY_CAP_HU.startswith("[hu] ")


def test_advisory_log_contains_en_and_hu(tmp_path) -> None:
    """The cap-state advisory contains both [en] and [hu] markers (single line)."""
    from easter_hermes_sorry_skills.i18n.messages_en import ADVISORY_CAP_EN
    from easter_hermes_sorry_skills.i18n.messages_hu import ADVISORY_CAP_HU

    en = ADVISORY_CAP_EN
    hu = ADVISORY_CAP_HU
    assert "[en]" in en and "[hu]" in hu
