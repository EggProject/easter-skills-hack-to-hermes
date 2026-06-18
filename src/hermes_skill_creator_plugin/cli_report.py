"""src/hermes_skill_creator_plugin/cli_report.py

Hermes skill-creator reporter (READ-ONLY) — Script #3.

See also: plans/13-script-3-report.md

The reporter is the operator's "what is on right now, and what does it
cost?" view. It is purely informational: NO file writes (except the
operator-chosen --json PATH), NO config flips, NO install calls.

TDD test cases for this module:
  test_help_is_bilingual
  test_exit_zero_on_success
  test_exit_six_when_enabled_detection_unavailable
  test_default_profile_iteration
  test_named_profile_selects_one
  test_sort_by_tokens
  test_sort_by_use_count
  test_sort_by_last_used_at
  test_text_format_columns
  test_json_format_shape
  test_rejects_apply_flag
  test_rejects_emit_migration_note_flag
  test_rejects_write_report_flag
  test_json_path_outside_fixture
  test_json_path_inside_hermes_home_aborts
  test_no_write_to_hermes_home_under_any_flag_combination
  test_no_migration_report_file_emitted
  test_console_log_lines_match_bilingual_regex
  test_uses_at_suffixed_timestamps
  test_does_not_invent_fields
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from ._enabled_detection import get_enabled_skills
from ._reporter import (
    ProfileSection,
    SkillRow,
    format_json,
    format_text,
    make_row,
    sort_rows,
)
from ._tokenizer import estimate_tokens
from .i18n import messages_en as EN

REJECTED_FLAGS = {
    "--apply": "apply",
    "--emit-migration-note": "emit-migration-note",
    "--write-report": "write-report",
}

HELP_EN_HEADER = "Usage (English):"
HELP_HU_HEADER = "Hasznalat (magyar):"


def _emit_tokenizer_warning(_msg: str) -> None:
    """Bilingual `click.echo` callback for `_tokenizer.estimate_tokens(warning=...)`.

    The D6 spec mandates that the reporter wires a bilingual warning callback
    into every `estimate_tokens` call so the operator sees exactly one
    `chars/4 fallback` notice per process. The module-level guard in
    `_tokenizer` (`_WARNED_ONCE`) ensures this callback fires at most once
    even when many skills are tokenized in one run. The bilingual constant
    lives in `i18n/messages_en.py::report_tokenizer_unavailable`.
    """
    click.echo(EN.report_tokenizer_unavailable, err=True)


def _resolve_hermes_home() -> Path:
    """Resolve HERMES_HOME from env, default to ~/.hermes (the LIVE install).

    The fixture tests monkeypatch HERMES_HOME to a tmp path BEFORE calling
    main(), so this resolution happens in the worktree and never touches
    the live install under test conditions.
    """
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path("~/.hermes").expanduser()


def _load_curator(hermes_home: Path) -> Any | None:
    """Best-effort: load tools.skill_usage. Return None when unavailable.

    The reporter does NOT raise when the Curator is absent; it falls back
    to n/a for every usage column. This mirrors the documented V8/W4 fix
    (the reporter must not invent usage values).
    """
    try:
        import tools.skill_usage as usage_mod  # type: ignore[import-not-found]
    except Exception:
        return None
    if not hasattr(usage_mod, "usage_report"):
        return None
    return usage_mod


def _resolve_profiles(hermes_home: Path, profile_arg: str | None) -> list[Path]:
    """Return the list of profile roots to report on.

    If `profile_arg` is set, return only `<hermes_home>/<profile_arg>`.
    Otherwise, return the `hermes` (default) profile and every named
    profile directory under `<hermes_home>/profiles/`.
    """
    if profile_arg:
        return [hermes_home / profile_arg]
    out: list[Path] = [hermes_home / "hermes"]
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.is_dir():
        for child in sorted(profiles_dir.iterdir()):
            if child.is_dir():
                out.append(child)
    return out


def _load_skill_description(skills_dir: Path, skill_name: str) -> str:
    """Read the full description from `<skills_dir>/<skill_name>/SKILL.md`.

    Falls back to a short placeholder when the file is missing or the
    frontmatter is unparseable. The function checks the frontmatter
    block first (for `description:` key) and falls back to the body
    section if no frontmatter description is present.
    """
    skill_md = skills_dir / skill_name / "SKILL.md"
    if not skill_md.is_file():
        return f"<description unavailable for {skill_name}>"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return f"<description unavailable for {skill_name}>"
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            frontmatter = text[3:end]
            body = text[end + 4 :].strip()
            # Look for a `description:` key in the frontmatter block first.
            for line in frontmatter.splitlines():
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip().strip("'\"")
            # Fall back to the body content.
            return body.split("\n\n", 1)[0] if body else text.strip()
    return text.strip()


def _build_usage_rows(
    curator: Any | None,
    skills_dir: Path,
    enabled_names: frozenset[str],
) -> dict[str, dict[str, Any]]:
    """Build a `name -> {use_count, view_count, patch_count, last_*_at, _persisted}` map.

    n/a-vs-0 (binding, V8/W4): use `usage_report()` and read the
    `_persisted` flag. We do NOT call `get_record()` (the backfill
    accessor). When the Curator is absent, every row has None values and
    `_persisted=False`.
    """
    out: dict[str, dict[str, Any]] = {}
    if curator is None:
        for n in enabled_names:
            out[n] = {
                "use_count": None,
                "view_count": None,
                "patch_count": None,
                "last_used_at": None,
                "last_viewed_at": None,
                "last_patched_at": None,
                "_persisted": False,
            }
        return out
    try:
        report = curator.usage_report(skills_dir=skills_dir)
    except Exception:
        report = []
    for entry in report or []:
        # The Curator returns objects with the six documented fields plus
        # a `_persisted` flag. We tolerate duck-typed access.
        name = getattr(entry, "name", None)
        if name is None:
            continue
        if name not in enabled_names:
            continue
        persisted = bool(getattr(entry, "_persisted", False))
        out[name] = {
            "use_count": getattr(entry, "use_count", 0) if persisted else None,
            "view_count": getattr(entry, "view_count", 0) if persisted else None,
            "patch_count": getattr(entry, "patch_count", 0) if persisted else None,
            "last_used_at": getattr(entry, "last_used_at", None) if persisted else None,
            "last_viewed_at": getattr(entry, "last_viewed_at", None) if persisted else None,
            "last_patched_at": getattr(entry, "last_patched_at", None) if persisted else None,
            "_persisted": persisted,
        }
    # Backfill: skills that are enabled but absent from the Curator's view.
    for n in enabled_names:
        if n not in out:
            out[n] = {
                "use_count": None,
                "view_count": None,
                "patch_count": None,
                "last_used_at": None,
                "last_viewed_at": None,
                "last_patched_at": None,
                "_persisted": False,
            }
    return out


class _EnabledDetectionUnavailable(Exception):
    """Raised by _build_rows_for_profile when get_enabled_skills is unavailable."""


def _build_rows_for_profile(
    profile: Path,
    *,
    platform: str | None,
    curator: Any | None,
) -> tuple[list[SkillRow], int]:
    """Build the SkillRow list and total_tokens for `profile`.

    Raises:
        _EnabledDetectionUnavailable: when the shared enabled-detection
            module is unavailable (e.g., the import was monkey-patched to
            raise). The caller is responsible for printing the bilingual
            error and exiting with code 6.
    """
    try:
        enabled = get_enabled_skills(profile, platform=platform)
    except Exception as exc:
        raise _EnabledDetectionUnavailable(str(exc)) from exc
    skills_dir = profile / "skills"
    usage = _build_usage_rows(curator, skills_dir, enabled)
    rows: list[SkillRow] = []
    total = 0
    for name in sorted(enabled):
        description = _load_skill_description(skills_dir, name)
        tokens = estimate_tokens(name, description, warning=_emit_tokenizer_warning)
        total += tokens
        u = usage.get(
            name,
            {
                "use_count": None,
                "view_count": None,
                "patch_count": None,
                "last_used_at": None,
                "last_viewed_at": None,
                "last_patched_at": None,
            },
        )
        rows.append(
            make_row(
                profile=profile.name,
                name=name,
                description=description,
                tokens=tokens,
                use_count=u["use_count"],
                view_count=u["view_count"],
                patch_count=u["patch_count"],
                last_used_at=u["last_used_at"],
                last_viewed_at=u["last_viewed_at"],
                last_patched_at=u["last_patched_at"],
            )
        )
    return rows, total


def _now_iso() -> str:
    """Return an ISO 8601 UTC timestamp. Honors HERMES_SKILL_CREATOR_FROZEN_TIME."""
    frozen = os.environ.get("HERMES_SKILL_CREATOR_FROZEN_TIME", "").strip()
    if frozen:
        return frozen
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_json_path(json_path: Path, hermes_home: Path) -> bool:
    """Return True when `json_path` resolves inside `hermes_home`.

    The caller is responsible for printing the bilingual error and exiting
    with code 6 when this returns True.
    """
    try:
        resolved = json_path.resolve()
    except OSError:
        return False
    try:
        home_resolved = hermes_home.resolve()
    except OSError:
        return False
    if resolved == home_resolved or home_resolved in resolved.parents:
        return True
    return False


def _emit_bilingual_help() -> None:
    """Print a two-section bilingual help (English, then Hungarian)."""
    en_lines = [
        HELP_EN_HEADER,
        "",
        "  uv run hermes-skill-creator-report [--profile <name>] "
        "[--sort tokens|use_count|last_used_at]",
        "                                     [--format text|json] [--json PATH] [--help]",
        "",
        "Options:",
        "  --profile <name>    " + EN.report_opt_profile,
        "  --sort <key>        " + EN.report_opt_sort,
        "  --format <fmt>      " + EN.report_opt_format,
        "  --json PATH         " + EN.report_opt_json,
        "  --help              " + EN.report_opt_help,
    ]
    from .i18n import messages_hu as HU

    hu_lines = [
        HELP_HU_HEADER,
        "",
        "  uv run hermes-skill-creator-report [--profile <name>] "
        "[--sort tokens|use_count|last_used_at]",
        "                                     [--format text|json] [--json PATH] [--help]",
        "",
        "Opciok:",
        "  --profile <name>    " + HU.report_opt_profile,
        "  --sort <key>        " + HU.report_opt_sort,
        "  --format <fmt>      " + HU.report_opt_format,
        "  --json PATH         " + HU.report_opt_json,
        "  --help              " + HU.report_opt_help,
    ]
    click.echo("\n".join(en_lines))
    click.echo("")
    click.echo("\n".join(hu_lines))


def _reject_flag(flag_name: str) -> int:
    """Print a bilingual rejection message and return exit code 2."""
    msg = {
        "apply": EN.report_rejected_apply,
        "emit-migration-note": EN.report_rejected_emit_migration_note,
        "write-report": EN.report_rejected_write_report,
    }.get(flag_name, EN.report_rejected_apply)
    click.echo(msg, err=True)
    return 2


# Public, testable entry point.
def run(
    *,
    profile: str | None = None,
    sort: str = "tokens",
    fmt: str = "text",
    json_path: Path | None = None,
    platform: str | None = None,
    show_help: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Run the reporter. Returns the exit code (0 on success).

    Args:
        profile: a single profile name, or None for default + named profiles.
        sort: 'tokens' | 'use_count' | 'last_used_at'.
        fmt: 'text' | 'json'.
        json_path: optional path to write the JSON output to (default:
            ./skill-report.json when --format=json and no --json).
        platform: optional platform tag passed to the enabled-detection helper.
        show_help: when True, print the bilingual help and return 0.
        argv: when set, scan `argv` for rejected flags before running.
    """
    if argv is not None:
        for arg in argv:
            for prefix, key in REJECTED_FLAGS.items():
                if arg == prefix or arg.startswith(prefix + "="):
                    return _reject_flag(key)
    if show_help:
        _emit_bilingual_help()
        return 0
    if sort not in {"tokens", "use_count", "last_used_at"}:
        click.echo(EN.report_opt_sort, err=True)
        return 2
    if fmt not in {"text", "json"}:
        click.echo(EN.report_opt_format, err=True)
        return 2
    hermes_home = _resolve_hermes_home()
    # Resolve the json_path target BEFORE the safety check so the default
    # `./skill-report.json` is also guarded. (Previously the default bypassed
    # _check_json_path, allowing a write inside HERMES_HOME when cwd==hermes_home.)
    if json_path is None and fmt == "json":
        json_path = Path("./skill-report.json")
    if json_path is not None and _check_json_path(json_path, hermes_home):
        click.echo(EN.report_json_path_inside_hermes_home, err=True)
        return 6
    curator = _load_curator(hermes_home)
    profile_paths = _resolve_profiles(hermes_home, profile)
    if not profile_paths:
        click.echo(EN.report_no_profiles, err=True)
        return 0
    generated_at = _now_iso()
    text_sections: list[str] = []
    json_sections: list[ProfileSection] = []
    for p in profile_paths:
        try:
            rows, total = _build_rows_for_profile(p, platform=platform, curator=curator)
        except _EnabledDetectionUnavailable:
            click.echo(EN.report_enabled_detection_unavailable, err=True)
            return 6
        rows = sort_rows(rows, sort)
        if fmt == "text":
            text_sections.append(format_text(p.name, rows, total_tokens=total))
        else:
            json_sections.append(
                ProfileSection(profile_name=p.name, rows=rows, total_tokens=total)
            )
    if fmt == "text":
        output = "\n\n".join(text_sections)
    else:
        output = format_json(
            tool="hermes-skill-creator-report",
            version="0.1.0",
            generated_at=generated_at,
            sections=json_sections,
        )
    if fmt == "json":
        # JSON mode: write to json_path (resolved above; default
        # `./skill-report.json` is operator-chosen, OUTSIDE the fixture tree).
        assert json_path is not None  # set above when fmt == "json"
        json_path.write_text(output, encoding="utf-8")
        click.echo(EN.report_opt_json)
    else:
        click.echo(output)
    return 0


@click.command(
    help=EN.report_help_short + "\n\n" + EN.report_help_long,
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.option("--profile", default=None, help=EN.report_opt_profile)
@click.option(
    "--sort",
    type=click.Choice(["tokens", "use_count", "last_used_at"]),
    default="tokens",
    help=EN.report_opt_sort,
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help=EN.report_opt_format,
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(),
    default=None,
    help=EN.report_opt_json,
)
@click.option("--help", "show_help", is_flag=True, default=False, help=EN.report_opt_help)
def main(
    profile: str | None,
    sort: str,
    fmt: str,
    json_path: str | None,
    show_help: bool,
) -> None:
    """Bilingual EN+HU reporter. See `--help` for details."""
    import sys

    argv = sys.argv[1:]
    if show_help:
        _emit_bilingual_help()
        raise SystemExit(0)
    jp: Path | None = Path(json_path) if json_path else None
    raise SystemExit(
        run(
            profile=profile,
            sort=sort,
            fmt=fmt,
            json_path=jp,
            argv=argv,
        )
    )


if __name__ == "__main__":
    main()  # pragma: no cover
