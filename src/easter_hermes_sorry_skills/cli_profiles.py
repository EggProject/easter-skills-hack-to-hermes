"""Script #2 — per-profile audit/flip for the migrated skill-creator (plan 06).

Phase 8: the CLI is READ-ONLY. There is no apply/dry-run split; the
``--json`` flag is the only output-format switch.

Public surface:
    app:                click command group (the CLI)
    run_audit(...):     programmatic entry point used by tests
    make_cli():         click.testing.CliRunner factory
    AuditReport:        dataclass-shaped dict-like report (the JSON shape)

The script is invoked as ``easter-hermes-sorry-skills-profiles`` (declared in
``pyproject.toml``). It walks every Hermes profile (the default
``hermes`` profile and every named profile returned by
``hermes_cli.profiles.list_profiles()``), audits the per-profile
skills tree via ``get_enabled_skills``, and emits a read-only report
— tables by default, JSON when ``--json`` is set.

The script NEVER writes to the live ``~/.hermes`` install. The
original ``openai/skills/skill-creator`` factory replacement was
already merged into ``main`` in plan 06; the live apply helper
``do_install(force=True, ...)`` is no longer called from here.

Safety:
- All console messages are bilingual (en/hu single line).
- ``--help`` has two mirrored sections (English / magyar).

See also: plans/06-script-2-profiles.md, plans/09-test-strategy.md.
"""

from __future__ import annotations

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings
from easter_hermes_sorry_skills import _cli_profiles_profiles as _profiles_mod
from easter_hermes_sorry_skills import _cli_profiles_run as _run

# Re-bindings matching the previous top-level names exposed by this
# orchestrator (kept for backward compat with tests + external callers).
_build_bilingual = _bindings._build_bilingual
EN = _bindings.EN
HU = _bindings.HU


def _bilingual(key: str, **format_values: object) -> str:
    """Bilingual ``[en] ... / [hu] ...`` helper using EN/HU tables."""
    return _build_bilingual(EN, HU, key, **format_values)


_build_help_text = _bindings._build_help_text
main_cmd = _bindings.main_cmd
_make_cli = _bindings._make_cli
_now_iso = _profiles_mod._now_iso
AuditReport = _bindings.AuditReport

# Re-exports for tests / external callers (do NOT remove — tests
# import these by name from ``easter_hermes_sorry_skills.cli_profiles``).
run_audit = _run.run_audit

# ---------------------------------------------------------------------------
# Click CLI re-export.
# ---------------------------------------------------------------------------


# `app` is the alias tests use; `main` is the click entry point declared
# in pyproject.toml. Both alias the click command built in
# ``_cli_profiles_cli.main_cmd``.
app = main_cmd
main = main_cmd
make_cli = _make_cli
