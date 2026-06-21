"""Script #2 — per-profile audit/flip for the migrated skill-creator (plan 06).

Public surface:
    app:                click command group (the CLI)
    run_audit(...):     programmatic entry point used by tests
    make_cli():         click.testing.CliRunner factory
    AuditReport:        dataclass-shaped dict-like report (the JSON shape)

The script is invoked as ``hermes-skill-creator-profiles`` (declared in
``pyproject.toml``). It walks every Hermes profile (the default
``hermes`` profile and every named profile returned by
``hermes_cli.profiles.list_profiles()``), audits the per-profile
skills tree, and (with ``--apply``) installs/replaces the migrated
``skill-creator`` at the flat path ``<HERMES_HOME>/skills/skill-creator/``.

The replace is in-place: the factory skill-creator (installed from
``openai/skills/skill-creator`` per ``hermes_cli/skills_hub.py``) and
the migrated skill share the same dir/name; ``do_install(force=True,
...)`` overwrites the factory at the flat path. We do NOT disable the
factory by NAME (the disable check is keyed by skill NAME per
``tools/skills_tool.py:597``: ``return name in global_disabled``);
adding ``"openai"`` or ``"skills"`` to the disabled list is a no-op
(no skill has those names) and would mislead operators — S5 BLOCKER
fix.

Safety:
- Runs under ``hermes_home_scope(path)`` which mirrors HERMES_HOME in
  BOTH the ``hermes_constants`` override token AND ``os.environ``.
- Refuses ``--apply`` against the live ``~/.hermes`` unless ``--yes``
  is passed AND the output is a TTY.
- All console messages are bilingual (en/hu single line).
- ``--help`` has two mirrored sections (English / magyar).

See also: plans/06-script-2-profiles.md, plans/09-test-strategy.md.
"""

from __future__ import annotations

# Tests grep this module's source for the canonical import lines
# (the read-side ``agent.skill_utils.get_disabled_skill_names`` and
# the write-side ``hermes_cli.skills_config.save_disabled_skills``);
# the audit helpers live in ``_cli_profiles_audit`` and the unused-
# import silencer is mandated by the test contract.
from agent.skill_utils import get_disabled_skill_names  # noqa: F401
from hermes_cli.skills_config import save_disabled_skills  # noqa: F401

from hermes_skill_creator_plugin import _cli_profiles_bindings as _bindings
from hermes_skill_creator_plugin import _cli_profiles_profiles as _profiles_mod
from hermes_skill_creator_plugin import _cli_profiles_run as _run

# Re-bindings matching the previous top-level names exposed by this
# orchestrator (kept for backward compat with tests + external callers).
_audit_profile = _bindings._audit_profile
_build_bilingual = _bindings._build_bilingual
EN = _bindings.EN
HU = _bindings.HU


def _bilingual(key: str, **format_values: object) -> str:
    """Bilingual ``[en] ... / [hu] ...`` helper using EN/HU tables."""
    return _build_bilingual(EN, HU, key, **format_values)


diff_sets = _bindings.diff_sets
walk_skills = _bindings.walk_skills
_build_help_text = _bindings._build_help_text
main_cmd = _bindings.main_cmd
_make_cli = _bindings._make_cli
_now_iso = _profiles_mod._now_iso
AuditReport = _bindings.AuditReport

# Re-exports for tests / external callers (do NOT remove — tests
# import these by name from ``hermes_skill_creator_plugin.cli_profiles``).
_walk_skills = walk_skills
_diff = diff_sets
run_audit = _run.run_audit
PROFILE_DIRS = (
    "memories",
    "sessions",
    "skills",
    "skins",
    "logs",
    "plans",
    "workspace",
    "cron",
    "home",
)

# ---------------------------------------------------------------------------
# Click CLI re-export.
# ---------------------------------------------------------------------------


# `app` is the alias tests use; `main` is the click entry point declared
# in pyproject.toml. Both alias the click command built in
# ``_cli_profiles_cli.main_cmd``.
app = main_cmd
main = main_cmd
make_cli = _make_cli
_build_help_text = _build_help_text  # noqa: F841 - re-export for tests
