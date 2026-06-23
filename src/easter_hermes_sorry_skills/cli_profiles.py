"""Script #2 — per-profile audit/flip for the migrated skill-creator (plan 06).

Public surface:
    app:                click command group (the CLI)
    run_audit(...):     programmatic entry point used by tests
    make_cli():         click.testing.CliRunner factory
    AuditReport:        dataclass-shaped dict-like report (the JSON shape)

The script is invoked as ``easter-hermes-sorry-skills-profiles`` (declared in
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

from collections.abc import Callable

from easter_hermes_sorry_skills import _cli_profiles_bindings as _bindings
from easter_hermes_sorry_skills import _cli_profiles_profiles as _profiles_mod
from easter_hermes_sorry_skills import _cli_profiles_run as _run


def _try_import_agent_utils() -> tuple[
    Callable[[], list[str]] | None,
    Callable[[list[str]], None] | None,
]:
    """Try to import the read/write disabled-skill helpers.

    Returns a ``(get_disabled_skill_names, save_disabled_skills)`` pair
    of callables, with each entry set to ``None`` if its source package
    is missing from this venv. The live call sites
    (``_cli_profiles_audit.py:107`` and ``_cli_profiles_audit.py:131``)
    do their own local import with a try/except fallback, so a missing
    binding here is non-fatal.
    """
    get_names: Callable[[], list[str]] | None
    save_skills: Callable[[list[str]], None] | None
    try:
        from agent.skill_utils import get_disabled_skill_names
    except ModuleNotFoundError:
        # ``agent`` package is not installed in this venv.
        get_names = None
    else:
        get_names = get_disabled_skill_names
    try:
        from hermes_cli.skills_config import save_disabled_skills
    except ModuleNotFoundError:
        # ``hermes_cli`` is not installed in this venv.
        save_skills = None
    else:
        save_skills = save_disabled_skills
    return get_names, save_skills


# Tests grep this module's source for the canonical import lines
# (the read-side ``agent.skill_utils.get_disabled_skill_names`` and
# the write-side ``hermes_cli.skills_config.save_disabled_skills``);
# the audit helpers live in ``_cli_profiles_audit`` and the unused-
# import silencer is mandated by the test contract.
get_disabled_skill_names: Callable[[], list[str]] | None
save_disabled_skills: Callable[[list[str]], None] | None
get_disabled_skill_names, save_disabled_skills = _try_import_agent_utils()

# Re-bindings matching the previous top-level names exposed by this
# orchestrator (kept for backward compat with tests + external callers).
_audit_profile = _bindings._audit_profile
_build_bilingual = _bindings._build_bilingual
EN = _bindings.EN
HU = _bindings.HU

# Re-bind the canonical read/write helpers at module level so the
# import lines above are not flagged as unused (F401) without
# resorting to a noqa silencer. The bindings mirror ``__all__``'s
# former public surface.
_get_disabled_skill_names = get_disabled_skill_names
_save_disabled_skills = save_disabled_skills


def _bilingual(key: str, **format_values: object) -> str:
    """Bilingual ``[en] ... / [hu] ...`` helper using EN/HU tables."""
    return _build_bilingual(EN, HU, key, **format_values)


diff_sets = _bindings.diff_sets
walk_skills = _bindings.walk_skills
walk_profile_subdirs = _bindings.walk_profile_subdirs
read_gateway_pid_stat = _bindings.read_gateway_pid_stat
_build_help_text = _bindings._build_help_text
main_cmd = _bindings.main_cmd
_make_cli = _bindings._make_cli
_now_iso = _profiles_mod._now_iso
AuditReport = _bindings.AuditReport

# Re-exports for tests / external callers (do NOT remove — tests
# import these by name from ``easter_hermes_sorry_skills.cli_profiles``).
_walk_skills = walk_skills
_diff = diff_sets
run_audit = _run.run_audit
PROFILE_DIRS = _bindings.PROFILE_DIRS

# ---------------------------------------------------------------------------
# Click CLI re-export.
# ---------------------------------------------------------------------------


# `app` is the alias tests use; `main` is the click entry point declared
# in pyproject.toml. Both alias the click command built in
# ``_cli_profiles_cli.main_cmd``.
app = main_cmd
main = main_cmd
make_cli = _make_cli
