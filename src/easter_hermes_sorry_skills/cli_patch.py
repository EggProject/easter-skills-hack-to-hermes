"""Script #1 click CLI: easter-hermes-sorry-skills-patch.

Bilingual --help (two-section EN/HU) and a small wrapper around
:func:`easter_hermes_sorry_skills._patcher.run_patch`.

The CLI is intentionally thin: every flag flows through to
``run_patch`` which returns a ``PatcherResult``. We then translate the
``exit_code`` into a ``SystemExit`` and emit any bilingual diagnostics
on the way out.

Architecture: the click decorator + options live on a thin ``main``
wrapper that only parses argv into :class:`PatchArgs` and delegates
to :func:`_patch_impl`. All business logic (target resolution,
migration-note flow, drift guards, diagnostics emission) lives in
``_patch_impl`` so structural-floor violations are measured without
the click option noise.

See also: plans/04-script-1-patch.md, plans/08-migration-note-format.md,
plans/10-toolchain-and-conventions.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import click

from easter_hermes_sorry_skills._patcher import (
    PatcherResult,
    PatchRunInputs,
    run_patch,
)
from easter_hermes_sorry_skills.cli_patch_flow import (
    resolve_target as _resolve_target,
)
from easter_hermes_sorry_skills.cli_patch_git import git_head as _git_head
from easter_hermes_sorry_skills.cli_patch_options import _add_click_option

_GIT_REV_PARSE_TIMEOUT_SEC = 5

HELP_EN = """\
Usage (English):
  uv run easter-hermes-sorry-skills-patch --check      --target <dir>
  uv run easter-hermes-sorry-skills-patch --apply      --target <dir> \\
      [--i-accept-line-drift]
  uv run easter-hermes-sorry-skills-patch --help

Options:
  --target DIR                 REQUIRED. User-owned Hermes checkout.
                               Refuses ~/.hermes/hermes-agent (resolve()).
  --check                      Audit only; no writes. Default.
  --apply                      Write the patch atomically.
  --i-accept-line-drift        Required iff --force is set; explicit
                               second confirmation. Without it, --force
                               exits 5.
  --force                      Line-only override. Requires
                               --i-accept-line-drift. Retries ONLY
                               sites with LINE_DRIFT diagnostic.
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
  uv run easter-hermes-sorry-skills-patch --check      --target <mappa>
  uv run easter-hermes-sorry-skills-patch --apply      --target <mappa> \\
      [--i-accept-line-drift]
  uv run easter-hermes-sorry-skills-patch --help

Opciok:
  --target DIR                 KOTELEZO. Felhasznai tulajdonu Hermes
                               checkout. Megtagadja a
                               ~/.hermes/hermes-agent celt
                               (resolve() osszehasonlitas).
  --check                      Csak audit; nem ir. Alapertelmezett.
  --apply                      Atomikusan vegzi a patch-et.
  --i-accept-line-drift        Kotelezo, ha a --force be van allitva;
                               masodik megerosites. Nelkule a --force
                               5-re kilep.
  --force                      Sor-alapu feluliras.
                               --i-accept-line-drift kell hozza. Csak
                               a LINE_DRIFT diagnosztikaju helyeket
                               probalja ujra.
  --yes                        Elnyomja a --force interaktiv TTY
                               megerositeset. A --yes onmagaban nem
                               keruli meg a --target megtagadast.
  --verbose                    Bilingual per-hely diagnosztikat nyomtat.
  --help                       Ezt a sugot mutatja.

Kilepesi kodok: 0 OK / 1 validacio / 2 drift / 3 jogosultsag / 4 I/O /
                5 user-abort.
"""


# --- the click command ----------------------------------------------------


def _emit_diagnostics(patcher_result: PatcherResult, *, verbose: bool) -> None:
    for diagnostic in patcher_result.diagnostics:
        if verbose:
            click.echo(f"[verbose] {diagnostic}")
        else:
            click.echo(diagnostic)


@dataclass(frozen=True)
class PatchArgs:
    """Parsed CLI args for ``easter-hermes-sorry-skills-patch``.

    One field per click option. The click wrapper translates argv into
    an instance and hands it to :func:`_patch_impl`.
    """

    target: str | None
    check: bool
    do_apply: bool
    i_accept_line_drift: bool
    force: bool
    yes: bool
    verbose: bool


def _patch_impl(args: PatchArgs) -> int:
    """Idempotent Hermes patcher (S1.cap: MAX_DESCRIPTION_LENGTH cap-raise).

    Returns the exit code; the click wrapper raises ``SystemExit`` so
    that test code can call this directly without click's process-exit
    side-effects.
    """
    target_path: Path | None = _resolve_target(args.target)

    check, apply_mode = args.check, args.do_apply
    if not check and not apply_mode:
        # default: --check when neither --check nor --apply is given.
        check = True

    # The --force / --i-accept-line-drift guard is enforced inside
    # run_patch (which returns EXIT_USER_ABORT). No click-level guard
    # is needed here.

    patcher_result = run_patch(
        PatchRunInputs(
            target=target_path,
            check=check,
            apply=args.do_apply,
            force=args.force,
            i_accept_line_drift=args.i_accept_line_drift,
            yes=args.yes,
            verbose=args.verbose,
            git_head=_git_head(target_path) if target_path else "",
        ),
    )

    _emit_diagnostics(patcher_result, verbose=args.verbose)
    return patcher_result.exit_code


@click.pass_context
def main(ctx: click.Context, /, **_kwargs: object) -> None:
    """Thin click wrapper — see :func:`_patch_impl` for logic."""
    opts = ctx.params
    sys.exit(
        _patch_impl(
            PatchArgs(
                target=opts.get("target"),
                check=bool(opts.get("check", False)),
                do_apply=bool(opts.get("do_apply", False)),
                i_accept_line_drift=bool(opts.get("i_accept_line_drift", False)),
                force=bool(opts.get("force", False)),
                yes=bool(opts.get("yes", False)),
                verbose=bool(opts.get("verbose", False)),
            ),
        ),
    )


# Apply click options to ``main`` directly (the entry-point contract).
main = click.command(
    help=f"{HELP_EN}\n{HELP_HU}",
    context_settings={"help_option_names": ["-h", "--help"]},
)(main)


main = _add_click_option(main, "--target", default_val=None)
main = _add_click_option(main, "--check", is_flag_val=True, default_val=False)
main = _add_click_option(
    main,
    "--apply",
    dest="do_apply",
    is_flag_val=True,
    default_val=False,
)
main = click.option(
    "--i-accept-line-drift",
    "i_accept_line_drift",
    is_flag=True,
    default=False,
    help=(),
)(main)
main = click.option("--force", is_flag=True, default=False, help=())(main)
main = click.option("--yes", is_flag=True, default=False, help=())(main)
main = click.option("--verbose", is_flag=True, default=False, help=())(main)


def _main_entry() -> int:
    """Module entry point — extracted for testability."""
    main(standalone_mode=True)
    return 0
