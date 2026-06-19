"""Script #1 click CLI: hermes-skill-creator-patch.

Bilingual --help (two-section EN/HU) and a small wrapper around
:func:`hermes_skill_creator_plugin._patcher.run_patch`.

The CLI is intentionally thin: every flag flows through to
``run_patch`` which returns a ``PatcherResult``. We then translate the
``exit_code`` into a ``SystemExit`` and emit any bilingual diagnostics
on the way out.

See also: plans/04-script-1-patch.md, plans/08-migration-note-format.md,
plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

from pathlib import Path

import click

from hermes_skill_creator_plugin._patcher import (
    EXIT_OK,
    PatcherResult,
    generate_migration_note,
    is_hermes_agent,
    run_patch,
)
from hermes_skill_creator_plugin.i18n.messages_en import (
    MIGRATION_REGENERATED,
    TARGET_IS_HERMES_AGENT,
    TARGET_REQUIRED,
)

_GIT_REV_PARSE_TIMEOUT_SEC = 5

HELP_EN = """\
Usage (English):
  uv run hermes-skill-creator-patch --check      --target <dir>
  uv run hermes-skill-creator-patch --apply      --target <dir> \\
      [--task-e-redirect] [--no-schema-redirect] [--i-accept-line-drift]
  uv run hermes-skill-creator-patch --emit-migration-note --target <dir> \\
      [--task-e-redirect] [--no-schema-redirect]
  uv run hermes-skill-creator-patch --help

Options:
  --target DIR                 REQUIRED. User-owned Hermes checkout.
                               Refuses ~/.hermes/hermes-agent (resolve()).
  --check                      Audit only; no writes. Default.
  --apply                      Write the patch atomically.
  --task-e-redirect            Opt-in: also patch the 7 Task E sites.
  --no-schema-redirect         Skip the OPTIONAL E6 schema description
                               site (under --task-e-redirect).
  --i-accept-line-drift        Required iff --force is set; explicit
                               second confirmation. Without it, --force
                               exits 5.
  --force                      Line-only override. Requires
                               --i-accept-line-drift. Retries ONLY
                               sites with LINE_DRIFT diagnostic.
  --emit-migration-note        Regenerates MIGRATION.hermes-patch.md
                               and MIGRATION.md index in the WORKTREE
                               (not the target). See 08-migration.
  --yes                        Suppresses interactive TTY confirmation
                               for --force. --yes alone does not bypass
                               --target refusal.
  --verbose                    Print bilingual per-site diagnostics.
  --help                       Show this help.

Exit codes: 0 OK / 1 validation / 2 drift / 3 permission / 4 I/O /
            5 user-abort.
"""

HELP_HU = """\
Használat (magyar):
  uv run hermes-skill-creator-patch --check      --target <mappa>
  uv run hermes-skill-creator-patch --apply      --target <mappa> \\
      [--task-e-redirect] [--no-schema-redirect] [--i-accept-line-drift]
  uv run hermes-skill-creator-patch --emit-migration-note --target <mappa> \\
      [--task-e-redirect] [--no-schema-redirect]
  uv run hermes-skill-creator-patch --help

Opciok:
  --target DIR                 KOTELEZO. Felhasznai tulajdonu Hermes
                               checkout. Megtagadja a
                               ~/.hermes/hermes-agent celt
                               (resolve() osszehasonlitas).
  --check                      Csak audit; nem ir. Alapertelmezett.
  --apply                      Atomikusan vegzi a patch-et.
  --task-e-redirect            Opt-in: a 7 Task E helyet is javitja.
  --no-schema-redirect         Kihagyja az OPCIONALIS E6 schema
                               description helyet (a --task-e-redirect
                               alatt).
  --i-accept-line-drift        Kotelezo, ha a --force be van allitva;
                               masodik megerosites. Nelkule a --force
                               5-re kilep.
  --force                      Sor-alapu feluliras.
                               --i-accept-line-drift kell hozza. Csak
                               a LINE_DRIFT diagnosztikaju helyeket
                               probalja ujra.
  --emit-migration-note        Ujrageneralja a MIGRATION.hermes-patch.md-t
                               es a MIGRATION.md indexet a WORKTREE
                               gyokerben (NEM a celban). Ld. 08-migration.
  --yes                        Elnyomja a --force interaktiv TTY
                               megerositeset. A --yes onmagaban nem
                               keruli meg a --target megtagadast.
  --verbose                    Bilingual per-hely diagnosztikat nyomtat.
  --help                       Ezt a sugot mutatja.

Kilepesi kodok: 0 OK / 1 validacio / 2 drift / 3 jogosultsag / 4 I/O /
                5 user-abort.
"""


# --- the click command ----------------------------------------------------


def _resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None


def _refuse_hermes_agent(target_path: Path) -> None:
    click.echo(
        TARGET_IS_HERMES_AGENT.format(resolved=str(target_path)),
        err=True,
    )
    raise SystemExit(4)


def _emit_migration_note_flow(
    target_path: Path,
    *,
    task_e_redirect: bool,
    no_schema_redirect: bool,
) -> None:
    if is_hermes_agent(target_path):
        _refuse_hermes_agent(target_path)
    worktree = Path.cwd()
    try:
        git_head = _git_head(target_path)
    except Exception:
        # _git_head swallows its own exceptions, but a future change
        # might let one slip through; the migration note must still be
        # emitted.
        git_head = ""
    path = generate_migration_note(
        target=target_path,
        worktree=worktree,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        git_head=git_head,
    )
    click.echo(MIGRATION_REGENERATED.format(path=str(path)))
    raise SystemExit(EXIT_OK)


def _emit_diagnostics(patcher_result: PatcherResult, *, verbose: bool) -> None:
    for diagnostic in patcher_result.diagnostics:
        if verbose:
            click.echo(f"[verbose] {diagnostic}")
        else:
            click.echo(diagnostic)


@click.command(
    help=f"{HELP_EN}\n{HELP_HU}",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--target", type=click.Path(), default=None, help=())
@click.option("--check", is_flag=True, default=False, help=())
@click.option("--apply", "do_apply", is_flag=True, default=False, help=())
@click.option(
    "--task-e-redirect",
    "task_e_redirect",
    is_flag=True,
    default=False,
    help=(),
)
@click.option(
    "--no-schema-redirect",
    "no_schema_redirect",
    is_flag=True,
    default=False,
    help=(),
)
@click.option(
    "--i-accept-line-drift",
    "i_accept_line_drift",
    is_flag=True,
    default=False,
    help=(),
)
@click.option("--force", is_flag=True, default=False, help=())
@click.option(
    "--emit-migration-note",
    "emit_migration_note",
    is_flag=True,
    default=False,
    help=(),
)
@click.option("--yes", is_flag=True, default=False, help=())
@click.option("--verbose", is_flag=True, default=False, help=())
def main(
    target: str | None,
    check: bool,
    do_apply: bool,
    task_e_redirect: bool,
    no_schema_redirect: bool,
    i_accept_line_drift: bool,
    force: bool,
    emit_migration_note: bool,
    yes: bool,
    verbose: bool,
) -> None:
    """Idempotent Hermes patcher (cap raise + 7 Task E sites)."""
    target_path: Path | None = _resolve_target(target)

    if emit_migration_note:
        if target_path is None:
            click.echo(TARGET_REQUIRED, err=True)
            raise SystemExit(4)
        _emit_migration_note_flow(
            target_path,
            task_e_redirect=task_e_redirect,
            no_schema_redirect=no_schema_redirect,
        )

    if not check and not do_apply:
        # default: --check
        check = True

    # The --force / --i-accept-line-drift guard is enforced inside
    # run_patch (which returns EXIT_USER_ABORT). No click-level guard
    # is needed here.

    patcher_result = run_patch(
        target=target_path,
        check=check,
        apply=do_apply,
        force=force,
        i_accept_line_drift=i_accept_line_drift,
        task_e_redirect=task_e_redirect,
        no_schema_redirect=no_schema_redirect,
        yes=yes,
        verbose=verbose,
        git_head=_git_head(target_path) if target_path is not None else "",
    )

    _emit_diagnostics(patcher_result, verbose=verbose)
    raise SystemExit(patcher_result.exit_code)


def _git_head(target: Path) -> str:
    """Best-effort git HEAD SHA for the target; empty on failure."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=_GIT_REV_PARSE_TIMEOUT_SEC,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def _main_entry() -> int:
    """Module entry point — extracted for testability."""
    return main.main(standalone_mode=True)
