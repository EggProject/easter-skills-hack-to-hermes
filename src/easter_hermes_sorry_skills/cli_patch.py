"""Script #1 click CLI: easter-hermes-sorry-skills-patch-hermes.

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

from easter_hermes_sorry_skills._cli_report_helpers_consts import LANG_EN
from easter_hermes_sorry_skills._patcher import (
    PatcherResult,
    PatchRunInputs,
    hermes_agent_path,
    run_patch,
)
from easter_hermes_sorry_skills.cli_patch_git import git_head as _git_head
from easter_hermes_sorry_skills.cli_patch_options import _add_click_option

HELP_EN = (
    "Patcher applies:\n"
    "  S1.cap   replace hard-coded ``60`` cap with MAX_DESCRIPTION_LENGTH\n"
    "  Task E   5 prompt-injection sites (consult rule for skill-creator)\n"
    "           applied by default, no flag.\n"
    "\n"
    "After a successful write, the on-disk skills prompt snapshot is purged to "
    "force a cold rebuild."
)

HELP_HU = (
    "A patcher a kovetkezoket vegzi:\n"
    "  S1.cap   a hard-coded ``60`` cap-et MAX_DESCRIPTION_LENGTH-re csereli\n"
    "  Task E   5 prompt-injection hely (skill-creator tanacsado szabaly)\n"
    "           alapertelmezetten fut, nincs flag.\n"
    "\n"
    "Sikeres write utan az on-disk skills prompt snapshot torlodik a cold rebuild-hoz."
)


# --- the click command ----------------------------------------------------


class _LangAwareCommand(click.Command):
    """Click command whose ``--help`` text follows the ``--lang`` option.

    ``--lang`` is declared ``is_eager`` so Click parses it before the
    built-in ``--help`` flag fires. When the user only passes ``--help``
    (no ``--lang``), ``ctx.params['lang']`` is ``None`` because Click
    short-circuits before defaults are applied — fall back to ``HELP_EN``
    in that case.

    We override :meth:`format_help_text` rather than :meth:`get_help` so
    that Click's auto-generated ``Options:`` block (which now includes
    ``--lang`` itself) still renders alongside the static help body.
    """

    def format_help_text(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        text = HELP_HU if ctx.params.get("lang") == "hu" else HELP_EN
        if text:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write_text(text)


def _emit_diagnostics(
    patcher_result: PatcherResult,
    *,
    verbose: bool,
    lang: str = LANG_EN,
) -> None:
    """Echo each patcher diagnostic.

    ``lang`` is plumbed for future single-language emission (the
    patcher currently emits bilingual strings regardless of ``lang``).
    """
    for diagnostic in patcher_result.diagnostics:
        if verbose:
            click.echo(f"[verbose] {diagnostic}")
        else:
            click.echo(diagnostic)


@dataclass(frozen=True)
class PatchArgs:
    """Parsed CLI args for ``easter-hermes-sorry-skills-patch-hermes``.

    One field per click option. The click wrapper translates argv into
    an instance and hands it to :func:`_patch_impl`. ``lang`` threads
    the ``--lang`` selection through the CLI struct so it is available
    for downstream emitters (the patcher pipeline will consume it once
    its i18n refactor lands).
    """

    target: str | None
    dry_run: bool
    verbose: bool
    lang: str = LANG_EN


def resolve_target(target_str: str | None) -> Path | None:
    return Path(target_str).resolve() if target_str else None


def _patch_impl(args: PatchArgs) -> int:
    """Idempotent Hermes patcher (S1.cap: MAX_DESCRIPTION_LENGTH cap-raise).

    Returns the exit code; the click wrapper raises ``SystemExit`` so
    that test code can call this directly without click's process-exit
    side-effects.

    ``args.lang`` threads the ``--lang`` selection through the CLI
    struct and is forwarded to :class:`PatchRunInputs.lang` so the
    patcher pipeline emits single-language diagnostics.
    """
    # ``--target`` defaults to ``hermes_agent_path()``; the patcher
    # refuses to write the no-touch sentinel (resolved path compare).
    target_str = args.target if args.target else str(hermes_agent_path())
    target_path: Path | None = resolve_target(target_str)
    if target_path is None:
        sys.exit("target_path must not be None at this point")

    # Default: WRITE. ``--dry-run`` switches to audit-only (check=True,
    # apply=False). The patcher does the rest of the validation.
    dry_run = args.dry_run

    patcher_result = run_patch(
        PatchRunInputs(
            target=target_path,
            dry_run=dry_run,
            verbose=args.verbose,
            git_head=_git_head(target_path),
            lang=args.lang,
        ),
    )

    # ``args.lang`` is the ``--lang`` selection plumbed through the
    # CLI struct; the patcher consumes it for single-language
    # emission via :class:`PatchRunInputs.lang`.
    _emit_diagnostics(patcher_result, verbose=args.verbose, lang=args.lang)
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
                lang=str(opts.get("lang", "en")),
            ),
        ),
    )


# Apply click options to ``main`` directly (the entry-point contract).
main = click.command(
    cls=_LangAwareCommand,
    help=HELP_EN,
    context_settings={"help_option_names": ["-h", "--help"]},
)(main)

main = click.option(
    "--lang",
    type=click.Choice(["en", "hu"]),
    default="en",
    is_eager=True,
    expose_value=True,
    help="Help language (en or hu)",
)(main)

main = _add_click_option(main, "--target", default_val=None)
main = _add_click_option(main, "--dry-run", is_flag_val=True, default_val=False)
main = _add_click_option(main, "--verbose", is_flag_val=True, default_val=False)


def _main_entry() -> int:
    """Module entry point — extracted for testability."""
    main(standalone_mode=True)
    return 0
