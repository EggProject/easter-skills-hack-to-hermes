"""Bilingual message helper for cli_profiles audit/apply.

Split from ``_cli_profiles_audit`` (WPS202 / WPS210).
"""

from __future__ import annotations

from typing import Any


def build_bilingual(
    en_table: Any,
    hu_table: Any,
    key: str,
    **format_values: Any,
) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key.

    The English half uses ``en_table``; the Hungarian half uses
    ``hu_table``. ``format_values`` are substituted via ``str.format``
    into both halves.
    """
    en_part = "[en] " + en_table[key].format(**format_values)
    hu_part = "[hu] " + hu_table[key].format(**format_values)
    return f"{en_part} / {hu_part}"
