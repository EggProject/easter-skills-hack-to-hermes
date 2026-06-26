"""Short description body for the profiles CLI surface.

Extracted from ``_cli_profiles_cli.py`` to keep that module under wemake
WPS202 (≤7 module members). Click's auto-generated ``Usage:`` and
``Options:`` blocks (which now include ``--lang`` itself) render
alongside this body via ``_LangAwareCommand.format_help_text``, so
this helper only returns the short description per language — it must
NOT include its own ``Usage:`` / ``Options:`` sections.
"""

from __future__ import annotations


def build_help_text(lang: str = "en") -> str:
    r"""Build the short description body for the profiles ``--help``.

    Pass ``lang="en"`` (default) for the English description or
    ``lang="hu"`` for the Hungarian description. The ``--lang`` Click
    option drives which single-language body is rendered by
    ``_LangAwareCommand.format_help_text``.
    """
    if lang == "hu":
        return (
            "Profilonkénti CSAK OLVASÁS audit a migrált skill-creator skillhez "
            "(Script #2). A script soha nem ír — a ~/.hermes/skills/skill-creator/ "
            "útvonalat vizsgálja minden profil alatt, és kétnyelvű EN/HU riportot ír."
        )
    return (
        "Per-profile READ-ONLY audit for the migrated skill-creator skill (Script "
        "#2). The script never writes — it inspects the skills tree at "
        "~/.hermes/skills/skill-creator/ under each profile and prints a bilingual "
        "EN/HU report."
    )
