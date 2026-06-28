"""Dry-run + apply plan output emitter for the patcher orchestrator.

Extracted from :mod:`._patcher` so the orchestrator stays under the
500-line hard cap and the wemake WPS202 module-member cap.

The plan emitter renders the header, the per-site
``would patch: <file> (site <id>)`` line, the per-line old/new diff
preview, the summary line, and the ``not applied`` / ``applied`` tail
message. It is shared by both the dry-run and the apply branches of
``_drive_pipeline`` so the visible plan stays identical between modes;
only the trailing tail differs.

The function is intentionally pure: it takes the target path, the
resolved ``sites`` list, the ``ValidationResult``, the mode, the
language, and appends plan lines to a returned list. No side-effects,
no I/O.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from easter_hermes_sorry_skills._i18n_pick import Messages, pick
from easter_hermes_sorry_skills._patcher_pipeline_emit import mutate_lines_for_site
from easter_hermes_sorry_skills._patcher_sites import Site
from easter_hermes_sorry_skills._patcher_validation import ValidationResult


def _read_text(file_path: Path) -> str:
    r"""Return the UTF-8 text of ``file_path`` or ``""`` on ``OSError``."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


class _SiteDiffFormatter:
    """Render the per-site diff lines for the resolved language module.

    Bundles ``old_lines``, ``new_lines``, ``anchor``, and ``msgs`` once
    so the per-shape renderers (``cap`` vs ``additive``) stay small.
    Holding the state on ``self`` instead of as function arguments
    keeps the Jones Complexity of each method under wemake WPS221's
    threshold and the local-variable count under WPS210.
    """

    def __init__(self, old_lines: list[str], new_lines: list[str], anchor: int, msgs: Messages) -> None:
        self.old_lines = old_lines
        self.new_lines = new_lines
        self.anchor = anchor
        self.msgs = msgs

    def cap(self) -> list[str]:
        r"""Return the 2-line diff block for a ``cap`` site."""
        start = self.anchor - 1
        old_t = self.msgs.DRY_RUN_DIFF_LINE_OLD
        new_t = self.msgs.DRY_RUN_DIFF_LINE_NEW
        anchor = self.anchor
        return [
            old_t.format(line=anchor, old=self.old_lines[start]),
            new_t.format(line=anchor, new=self.new_lines[start]),
            old_t.format(line=anchor + 1, old=self.old_lines[start + 1]),
            new_t.format(line=anchor + 1, new=self.new_lines[start + 1]),
        ]

    def additive(self) -> list[str]:
        r"""Return the ``anchor + inserted`` diff for an additive site."""
        old_idx = self.anchor - 1
        new_idx = self.anchor
        old_after = self.old_lines[old_idx] if old_idx < len(self.old_lines) else ""
        new_after = self.new_lines[new_idx] if new_idx < len(self.new_lines) else ""
        return [
            self.msgs.DRY_RUN_DIFF_LINE_OLD.format(line=self.anchor, old=old_after),
            self.msgs.DRY_RUN_DIFF_LINE_NEW.format(line=self.anchor, new=new_after),
        ]


def _site_diff(site: Site, text: str, msgs: Messages) -> list[str]:
    r"""Return the per-line ``- old / + new`` diff for ``site``.

    Returns ``[]`` when ``text`` is empty (file missing) or when
    :func:`mutate_lines_for_site` raises ``IndexError`` /
    ``ValueError`` on a stale anchor.
    """
    if not text:
        return []
    old_lines = text.splitlines()
    try:
        new_lines = "".join(mutate_lines_for_site(site, text)).splitlines()
    except (IndexError, ValueError):
        return []
    formatter = _SiteDiffFormatter(old_lines, new_lines, site.primary_anchor().line, msgs)
    if site.kind == "cap":
        return formatter.cap()
    return formatter.additive()


def _build_plan_body(
    target_path: Path,
    applied: list[Site],
    msgs: Messages,
) -> list[str]:
    r"""Build the per-site plan lines for ``applied`` under ``target_path``."""
    lines = [msgs.DRY_RUN_PLAN_HEADER.format(target=str(target_path))]
    for site in applied:
        lines.append(
            msgs.DRY_RUN_PATCH_LINE.format(
                file_path=str(site.file_path),
                site_id=site.site_id,
            ),
        )
        lines.extend(_site_diff(site, _read_text(target_path / site.file_path), msgs))
    lines.append(msgs.DRY_RUN_PLAN_SUMMARY.format(count=len(applied)))
    return lines


def _emit_plan(
    target_path: Path,
    sites: list[Site],
    validation: ValidationResult,
    mode: Literal["dry_run", "apply"],
    lang: str = "en",
) -> list[str]:
    r"""Return the plan lines for ``target_path`` + ``sites``.

    Renders the header, one ``would patch: <file> (site <id>)`` line
    per site, the per-site old/new diff preview, the summary, and the
    mode-specific tail (``not applied`` / ``applied``).

    Sites that already match (idempotency) are skipped from the
    per-site body but still counted in the summary. Drift sites are
    skipped — the plan only renders sites that WOULD be applied.

    ``lang`` selects the single-language i18n module via
    :func:`easter_hermes_sorry_skills._i18n_pick.pick`; defaults to
    ``"en"``.
    """
    msgs = pick(lang)
    drifted_ids = {failure.get("site_id") for failure in validation.failures}
    applied = [site for site in sites if site.site_id not in drifted_ids]
    lines = _build_plan_body(target_path, applied, msgs)
    template = msgs.DRY_RUN_NOT_APPLIED if mode == "dry_run" else msgs.DRY_RUN_APPLIED
    lines.append(template.format(count=len(applied)))
    return lines
