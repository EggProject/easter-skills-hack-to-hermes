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

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from ._scope import hermes_home_scope
from .i18n.messages_en import M as EN
from .i18n.messages_hu import M as HU

# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

TOOL_NAME = "hermes-skill-creator-profiles"
TOOL_VERSION = "0.1.0"
DESIRED_SKILL = "skill-creator"
# Canonical per-profile subdir set (mirrors hermes_cli/profiles.py).
PROFILE_DIRS: tuple[str, ...] = (
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
# Live install refusal (per the safety contract).
LIVE_HERMES_HOME = Path.home() / ".hermes"
# S5 regression sentinels: these strings are NEVER added to the disabled list.
NEVER_DISABLE = frozenset({"openai", "skills"})


# ---------------------------------------------------------------------------
# Report dataclass.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditReport:
    """A deterministic per-profile audit/flip report.

    The dataclass serializes to JSON via ``to_json_bytes()``; the
    serialized form is byte-identical across runs given the same
    inputs and a stable ``generated_at``.

    The class is dict-like (``report["profiles"]``) for ergonomic
    tests; ``to_dict()`` returns the canonical shape.
    """

    tool: str
    version: str
    generated_at: str
    profiles: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        # Sort keys for deterministic serialization (D7).
        return {
            "tool": self.tool,
            "version": self.version,
            "generated_at": self.generated_at,
            "profiles": sorted(self.profiles, key=lambda r: r["profile_name"]),
        }

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.to_dict())

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def __hash__(self) -> int:  # type: ignore[no-untyped-def]
        # Hash on a frozen view of to_dict(); lists are not hashable so
        # we freeze the profiles list into a tuple of tuples.
        d = self.to_dict()
        return hash(
            (
                d["tool"],
                d["version"],
                d["generated_at"],
                tuple(tuple(sorted(p.items())) for p in d["profiles"]),
            )
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AuditReport):
            return self.to_dict() == other.to_dict()
        if isinstance(other, dict):
            return self.to_dict() == other
        return NotImplemented


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _bilingual(key: str, **values: Any) -> str:
    """Build a ``[en] ... / [hu] ...`` line for the given message key.

    The English half uses the ``EN`` table; the Hungarian half uses
    ``HU``. ``values`` are substituted via ``str.format`` into both
    halves.
    """
    en_template = EN[key]
    hu_template = HU[key]
    # Prepend the ``[en]`` / ``[hu]`` markers; the Hungarian half gets
    # the ``/ [hu]`` separator.
    en_part = "[en] " + en_template.format(**values)
    hu_part = "[hu] " + hu_template.format(**values)
    return f"{en_part} / {hu_part}"


def _now_iso(frozen_time: str | None) -> str:
    """Return the report timestamp (stable when ``frozen_time`` is set)."""
    if frozen_time is not None:
        return frozen_time
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _walk_skills(skills_dir: Path) -> set[str]:
    """Return the set of installed skill NAMES under ``skills_dir``.

    NAME comes from the SKILL.md frontmatter ``name:`` field; the
    directory name is the fallback. Directories without SKILL.md are
    ignored. The walk is robust to read errors (the skill is dropped).
    """
    from agent.skill_utils import parse_frontmatter

    if not skills_dir.is_dir():
        return set()
    out: set[str] = set()
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            fm, _body = parse_frontmatter(text)
        except Exception:
            continue
        name = fm.get("name")
        if isinstance(name, str) and name:
            out.add(name)
        else:
            out.add(child.name)
    return out


def _diff(current: set[str], desired: set[str]) -> dict[str, list[str]]:
    """Compute the symmetric diff between current and desired as sorted lists."""
    return {
        "added": sorted(desired - current),
        "removed": sorted(current - desired),
    }


# ---------------------------------------------------------------------------
# Core audit + apply logic.
# ---------------------------------------------------------------------------


def _audit_profile(
    profile_path: Path,
    *,
    apply: bool,
    skip_install: bool,
    frozen_time: str | None,
) -> dict[str, Any]:
    """Audit (and optionally apply) a single profile.

    Returns the per-profile row of the report. The call runs inside
    ``hermes_home_scope(profile_path)`` so all ``load_config`` /
    ``do_install`` / ``save_config`` calls resolve against the
    scoped HERMES_HOME (per plan 06 D4 + AC-3.4 / AC-3.6).
    """
    from agent.prompt_builder import clear_skills_system_prompt_cache
    from agent.skill_utils import get_disabled_skill_names
    from hermes_cli.config import load_config, save_config
    from hermes_cli.skills_config import save_disabled_skills
    from hermes_cli.skills_hub import do_install

    row: dict[str, Any] = {
        "profile_name": profile_path.name or "hermes",
        "current_disabled": [],
        "current_installed": [],
        "desired_disabled": [],
        "desired_installed": [],
        "diff": {
            "added_disabled": [],
            "removed_disabled": [],
            "added_installed": [],
            "removed_installed": [],
        },
        "actions_taken": [],
        "errors": [],
    }
    actions = row["actions_taken"]
    errors = row["errors"]

    with hermes_home_scope(profile_path):
        # Look up the mutator at call time so monkeypatch.setattr on
        # the module works. The top-of-function import caches a
        # reference; the test infrastructure may rebind it.
        import hermes_cli.skills_config as _skills_config_mod

        save_disabled_skills = _skills_config_mod.save_disabled_skills

        # 1. config snapshot.
        try:
            config = load_config()
        except Exception as exc:  # noqa: BLE001 — surface as a row error.
            errors.append(f"load_config failed: {exc}")
            return row

        # 2. disabled_now (read from agent.skill_utils, NOT hermes_cli.skills_config).
        try:
            disabled_now: set[str] = set(get_disabled_skill_names(platform=None))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"get_disabled_skill_names failed: {exc}")
            disabled_now = set()

        # 3. installed_now (walk the skills dir).
        installed_now: set[str] = _walk_skills(profile_path / "skills")

        # 4. desired_disabled = disabled_now. NEVER add NEVER_DISABLE entries.
        desired_disabled: set[str] = set(disabled_now) - NEVER_DISABLE

        # 5. desired_installed = installed_now ∪ {DESIRED_SKILL}.
        desired_installed: set[str] = set(installed_now) | {DESIRED_SKILL}

        row["current_disabled"] = sorted(disabled_now)
        row["current_installed"] = sorted(installed_now)
        row["desired_disabled"] = sorted(desired_disabled)
        row["desired_installed"] = sorted(desired_installed)

        diff_disabled = _diff(disabled_now, desired_disabled)
        diff_installed = _diff(installed_now, desired_installed)
        row["diff"] = {
            "added_disabled": diff_disabled["added"],
            "removed_disabled": diff_disabled["removed"],
            "added_installed": diff_installed["added"],
            "removed_installed": diff_installed["removed"],
        }

        # 6. apply writes.
        if apply:
            # 6a. save_disabled_skills (only if it would change).
            if desired_disabled != disabled_now:
                try:
                    save_disabled_skills(config, sorted(desired_disabled), platform=None)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"save_disabled_skills failed: {exc}")
                else:
                    actions.append("save_disabled_skills")
                    try:
                        save_config(config)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"save_config failed: {exc}")
                    else:
                        actions.append("save_config")

            # 6b. do_install (always — even when installed_now already
            # contains DESIRED_SKILL, the apply is idempotent and the
            # migrated copy is authoritative).
            if not skip_install:
                try:
                    do_install(
                        DESIRED_SKILL,
                        category="",
                        force=True,
                        console=None,
                        skip_confirm=True,
                        invalidate_cache=True,
                        name_override="",
                    )
                    actions.append("do_install")
                except Exception as exc:  # noqa: BLE001
                    msg = _bilingual("profiles_msg_hub_error", name=row["profile_name"], err=exc)
                    click.echo(msg)
                    errors.append(f"hub install failed: {exc}")

            # 6c. clear_skills_system_prompt_cache (warn-and-continue).
            try:
                clear_skills_system_prompt_cache(clear_snapshot=True)
                actions.append("clear_skills_system_prompt_cache")
            except Exception as exc:  # noqa: BLE001
                msg = _bilingual("profiles_msg_cache_warn", name=row["profile_name"], err=exc)
                click.echo(msg)
                errors.append(f"cache clear failed: {exc}")

    return row


# ---------------------------------------------------------------------------
# Programmatic entry point.
# ---------------------------------------------------------------------------


def run_audit(
    *,
    apply: bool = False,
    json_path: Path | None = None,
    frozen_time: str | None = None,
    skip_install: bool = False,
    yes: bool = False,
    profile: str | None = None,
) -> AuditReport:
    """Run the per-profile audit/flip.

    Args:
        apply: When True, perform the writes (--apply).
        json_path: Optional path to write the JSON report to.
        frozen_time: Optional ISO 8601 UTC string to pin the report
            timestamp (D7: determinism).
        skip_install: When True, audit only (do not call do_install).
        yes: When True, suppress the live-install refusal.
        profile: Optional single profile NAME to restrict the run to.

    Returns:
        The ``AuditReport`` (also written to ``json_path`` if given).
    """
    from hermes_cli.profiles import list_profiles

    # 0. Live-install refusal (safety contract). The refusal fires
    #    whenever HERMES_HOME resolves to the LIVE install AND --yes is
    #    absent — TTY or not, CI or interactive. Operators who really
    #    want to write to the live install must pass --yes.
    if apply and not yes:
        env = os.environ.get("HERMES_HOME")
        if env is not None and Path(env).resolve() == LIVE_HERMES_HOME.resolve():
            click.echo(_bilingual("profiles_msg_refuse_no_yes"))
            sys.exit(5)

    click.echo(_bilingual("profiles_msg_scanning"))
    all_profiles = list_profiles()
    selected = [p for p in all_profiles if p.name == profile] if profile is not None else list(all_profiles)
    click.echo(_bilingual("profiles_msg_profile_count", n=len(selected)))
    if not selected:
        click.echo(_bilingual("profiles_msg_no_profiles"))
        return AuditReport(
            tool=TOOL_NAME,
            version=TOOL_VERSION,
            generated_at=_now_iso(frozen_time),
            profiles=[],
        )

    if apply:
        click.echo(_bilingual("profiles_msg_applying"))
    else:
        click.echo(_bilingual("profiles_msg_audit_default"))

    report = AuditReport(
        tool=TOOL_NAME,
        version=TOOL_VERSION,
        generated_at=_now_iso(frozen_time),
        profiles=[],
    )
    for p in selected:
        row = _audit_profile(
            p.path,
            apply=apply,
            skip_install=skip_install,
            frozen_time=frozen_time,
        )
        # Backfill the profile_name from the ProfileInfo (in case
        # the path-based name was "hermes" by default).
        row["profile_name"] = p.name
        click.echo(
            _bilingual(
                "profiles_msg_profile_audit",
                name=row["profile_name"],
                disabled=",".join(row["current_disabled"]) or "-",
                installed=",".join(row["current_installed"]) or "-",
            )
        )
        click.echo(
            _bilingual(
                "profiles_msg_diff",
                ad=",".join(row["diff"]["added_disabled"]) or "-",
                rd=",".join(row["diff"]["removed_disabled"]) or "-",
                ai=",".join(row["diff"]["added_installed"]) or "-",
                ri=",".join(row["diff"]["removed_installed"]) or "-",
            )
        )
        report.profiles.append(row)

    click.echo(_bilingual("profiles_msg_done", n=len(selected)))

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_bytes(report.to_json_bytes())
        click.echo(_bilingual("profiles_msg_json_written", path=str(json_path)))

    return report


# ---------------------------------------------------------------------------
# Click CLI.
# ---------------------------------------------------------------------------


def _build_help_text() -> str:
    """Build the bilingual --help text (two mirrored sections)."""
    en = (
        f"{EN['profiles_help_short']}\n\n"
        f"Usage (English):\n"
        f"  hermes-skill-creator-profiles [--apply] [--audit] [--profile NAME]\n"
        f"                                  [--json PATH] [--yes] [--skip-install]\n"
        f"                                  [--frozen-time ISO] [--help]\n\n"
        f"{EN['profiles_help_long']}\n\n"
        f"Options:\n"
        f"  --apply            {EN['profiles_opt_apply']}\n"
        f"  --audit            {EN['profiles_opt_audit']}\n"
        f"  --profile NAME     {EN['profiles_opt_profile']}\n"
        f"  --json PATH        {EN['profiles_opt_json']}\n"
        f"  --yes              {EN['profiles_opt_yes']}\n"
        f"  --skip-install     {EN['profiles_opt_skip_install']}\n"
        f"  --frozen-time ISO  {EN['profiles_opt_frozen_time']}\n"
        f"  --help             {EN['profiles_opt_help']}\n"
    )
    hu = (
        f"{HU['profiles_help_short']}\n\n"
        f"Használat (magyar):\n"
        f"  hermes-skill-creator-profiles [--apply] [--audit] [--profile NÉV]\n"
        f"                                  [--json ÚTVONAL] [--yes] [--skip-install]\n"
        f"                                  [--frozen-time ISO] [--help]\n\n"
        f"{HU['profiles_help_long']}\n\n"
        f"Kapcsolók:\n"
        f"  --apply            {HU['profiles_opt_apply']}\n"
        f"  --audit            {HU['profiles_opt_audit']}\n"
        f"  --profile NÉV      {HU['profiles_opt_profile']}\n"
        f"  --json ÚTVONAL     {HU['profiles_opt_json']}\n"
        f"  --yes              {HU['profiles_opt_yes']}\n"
        f"  --skip-install     {HU['profiles_opt_skip_install']}\n"
        f"  --frozen-time ISO  {HU['profiles_opt_frozen_time']}\n"
        f"  --help             {HU['profiles_opt_help']}\n"
    )
    return en + "\n" + hu


@click.command(
    help=_build_help_text(),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--apply", "apply", is_flag=True, default=False, help=EN["profiles_opt_apply"])
@click.option("--audit", "audit_only", is_flag=True, default=False, help=EN["profiles_opt_audit"])
@click.option("--profile", "profile", default=None, help=EN["profiles_opt_profile"])
@click.option("--json", "json_path", default=None, type=click.Path(), help=EN["profiles_opt_json"])
@click.option("--yes", "yes", is_flag=True, default=False, help=EN["profiles_opt_yes"])
@click.option(
    "--skip-install",
    "skip_install",
    is_flag=True,
    default=False,
    help=EN["profiles_opt_skip_install"],
)
@click.option(
    "--frozen-time",
    "frozen_time",
    default=None,
    envvar="HERMES_SKILL_CREATOR_FROZEN_TIME",
    help=EN["profiles_opt_frozen_time"],
)
def main(
    apply: bool,
    audit_only: bool,
    profile: str | None,
    json_path: str | None,
    yes: bool,
    skip_install: bool,
    frozen_time: str | None,
) -> None:
    """Per-profile audit/flip for the migrated skill-creator skill (Script #2)."""
    effective_apply = apply and not audit_only
    resolved_json: Path | None = Path(json_path) if json_path else None
    run_audit(
        apply=effective_apply,
        json_path=resolved_json,
        frozen_time=frozen_time,
        skip_install=skip_install,
        yes=yes,
        profile=profile,
    )


# `app` is the alias tests use; `main` is the click entry point declared
# in pyproject.toml.
app = main


def make_cli() -> Any:
    """Return a ``click.testing.CliRunner`` for tests."""
    from click.testing import CliRunner

    return CliRunner()
