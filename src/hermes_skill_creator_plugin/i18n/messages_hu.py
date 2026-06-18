"""Hungarian i18n messages for hermes-skill-creator-plugin.

TDD test cases:
    test_advisory_cap_hu_is_bilingual_line

Bilingual contract: every string here is the HU half of `[en] ... / [hu] ...`.
The full single-line is composed at log time; the HU half must be a plain
sentence (no [en] / [hu] markers), so the composed line matches the regex
`^\\[en\\] .+ / \\[hu\\] .+$`.

See also: plans/03-plugin-spec.md, plans/10-toolchain-and-conventions.md.
"""

# Cap-state advisory (HU half). Emitted when the 60-character skill-description
# cap is detected as still un-raised in the operator's Hermes checkout.
ADVISORY_CAP_HU = (
    "[hu] A 60 karakteres skill-leírás-korlát még nincs felemelve a Hermes "
    "checkoutban. Futtasd a `hermes-skill-creator-patch` parancsot a felemeléshez."
)
