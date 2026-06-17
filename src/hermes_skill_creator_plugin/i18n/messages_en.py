"""English i18n messages for hermes-skill-creator-plugin.

TDD test cases:
    test_advisory_cap_en_is_bilingual_line

Bilingual contract: every string here is the EN half of `[en] ... / [hu] ...`.
The full single-line is composed at log time; the EN half must be a plain
sentence (no [en] / [hu] markers), so the composed line matches the regex
`^\\[en\\] .+ / \\[hu\\] .+$`.
"""

# Cap-state advisory (EN half). Emitted when the 60-char skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_EN = (
    "[en] The 60-character skill-description cap is un-raised in your Hermes "
    "checkout. Run `hermes-skill-creator-patch` to raise it."
)
