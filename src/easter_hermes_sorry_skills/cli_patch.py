"""Script #1 click CLI: easter-hermes-sorry-skills-patch.

Bilingual --help (two-section EN/HU) and a small wrapper around
:func:`easter_hermes_sorry_skills._patcher.run_patch`.

The patcher applies two classes of changes to a Hermes checkout:
- S1.cap (PRIMARY): replaces the hard-coded ``60`` cap in
  ``agent/skill_utils.py``'s ``extract_skill_description`` with
  ``MAX_DESCRIPTION_LENGTH``.
- 5 Task E sites (ALWAYS-ON, no flag): injects the consult rule
  (``SKILL_CREATOR_CONSULT_RULE``) into the Hermes prompt surfaces
  flagged by Task E.

There are no opt-out flags. Task E runs by default. The patcher
WRITES by default; use ``--dry-run`` to audit without writing.
``--target`` defaults to ``~/.hermes/hermes-agent`` so the patcher
refuses the no-touch sentinel unless an explicit path is given.

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
    hermes_agent_path,
    run_patch,
)
from easter_hermes_sorry_skills.cli_patch_git import git_head as _git_head
from easter_hermes_sorry_skills.cli_patch_options import _add_click_option

HELP_EN = """\
Usage (English):
  uv run easter-hermes-sorry-skills-patch [--dry-run] [--target <dir>]
  uv run easter-hermes-sorry-skills-patch --help

Patcher applies:
  S1.cap  replace hard-coded ``60`` cap with MAX_DESCRIPTION_LENGTH
  Task E  5 prompt-injection sites (consult rule for skill-creator)
          applied by default, no flag
          After a successful write, the on-disk skills prompt snapshot
          is purged to force a cold rebuild.

Options:
  --target DIR                 User-owned Hermes checkout.
                               Defaults to ~/.hermes/hermes-agent,
                               which is REFUSED (resolve() comparison,
                               exit code 4). Pass an explicit path to
                               patch a different checkout.
  --dry-run                    Audit only; no writes. Default: WRITES.
  --verbose                    Print bilingual per-site diagnostics.
  --help                       Show this help.

Exit codes: 0 OK / 1 validation / 2 drift / 3 permission / 4 I/O /
            5 user-abort.
"""

HELP_HU = """\
Használat (magyar):
  uv run easter-hermes-sorry-skills-patch [--dry-run] [--target <mappa>]
  uv run easter-hermes-sorry-skills-patch --help

A patcher a kovetkezoket vegzi:
  S1.cap  a hard-coded ``60`` cap-et MAX_DESCRIPTION_LENGTH-re csereli
  Task E  5 prompt-injection hely (skill-creator tanacsado szabaly)
          alapertelmezetten fut, nincs flag
          Sikeres iras utan a skills-prompt snapshot torolve lesz
          a hideg-rebuildhoz.

Opciok:
  --target DIR                 Felhasznaloi tulajdonu Hermes checkout.
                               Alapertelmezett: ~/.hermes/hermes-agent,
                               amit a patcher MEGTAGAD (resolve()
                               osszehasonlitas, 4-es kilepesi kod).
                               Adj meg explicit utat egy masik
                               checkout patchelesehez.
  --dry-run                    Csak audit; nem ir. Alapertelmezett: IR.
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
    dry_run: bool
    verbose: bool


def resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None


def _patch_impl(args: PatchArgs) -> int:
    """Idempotent Hermes patcher (S1.cap: MAX_DESCRIPTION_LENGTH cap-raise).

    Returns the exit code; the click wrapper raises ``SystemExit`` so
    that test code can call this directly without click's process-exit
    side-effects.
    """
    # ``--target`` defaults to ``hermes_agent_path()``; the patcher
    # refuses to write the no-touch sentinel (resolved path compare).
    target_str = args.target if args.target else str(hermes_agent_path())
    target_path: Path | None = resolve_target(target_str)
    assert target_path is not None  # narrowed by the default above

    # Default: WRITE. ``--dry-run`` switches to audit-only (check=True,
    # apply=False). The patcher does the rest of the validation.
    dry_run = args.dry_run

    patcher_result = run_patch(
        PatchRunInputs(
            target=target_path,
            dry_run=dry_run,
            verbose=args.verbose,
            git_head=_git_head(target_path),
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
                dry_run=bool(opts.get("dry_run", False)),
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
main = _add_click_option(main, "--dry-run", is_flag_val=True, default_val=False)
main = _add_click_option(main, "--verbose", is_flag_val=True, default_val=False)


def _main_entry() -> int:
    """Module entry point — extracted for testability."""
    main(standalone_mode=True)
    return 0
