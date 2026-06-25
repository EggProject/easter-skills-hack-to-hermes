"""Audit pipeline helpers for the ``cli_profiles`` CLI (READ-ONLY).

Phase 8: the orchestrator no longer drives the apply pipeline. It only
forwards the per-profile scan result into the table renderer's payload
shape. The read-only row collector builds the per-profile summary dict
(``enabled_skills`` + token rollups) consumed by
``_cli_profiles_table.render_all_profiles``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_cli.profiles import ProfileInfo

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings

_build_bilingual = _bindings._build_bilingual


def _bilingual(key: str, **format_kwargs: object) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key."""
    return _build_bilingual(_bindings.EN, _bindings.HU, key, **format_kwargs)


def _audit_and_collect_row_readonly(
    profile_info: ProfileInfo,
    *,
    verbose: bool = False,
    as_json: bool = False,
) -> dict[str, object]:
    """Build the per-profile summary dict for the table renderer.

    Phase 8 is READ-ONLY: the dict is the payload that
    ``_cli_profiles_table._profile_entry`` consumes to populate the
    per-profile JSON block. The ``verbose`` and ``as_json`` kwargs are
    accepted for API symmetry with the previous (WRITE) implementation;
    neither has any effect on the returned payload.
    """
    return {
        "profile_name": profile_info.name,
    }
