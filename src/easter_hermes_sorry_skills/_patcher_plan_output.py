"""Dry-run + apply plan output emitter for the patcher orchestrator.

Extracted from :mod:`._patcher` so the orchestrator stays under the
500-line hard cap and the wemake WPS202 module-member cap.

The plan emitter renders the bilingual header, the per-site
``would patch: <file> (site <id>)`` line, the per-line old/new diff
preview, the bilingual summary line, and the bilingual
``not applied`` / ``applied`` tail message. It is shared by both the
dry-run and the apply branches of ``_drive_pipeline`` so the visible
plan stays identical between modes; only the trailing tail differs.

The function is intentionally pure: it takes the target path, the
resolved ``sites`` list, the ``ValidationResult``, the mode, and the
existing diagnostics list, and appends plan lines to that list. No
side-effects, no I/O.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from easter_hermes_sorry_skills._patcher_pipeline_emit import mutate_lines_for_site
from easter_hermes_sorry_skills._patcher_sites import Site
from easter_hermes_sorry_skills._patcher_validation import ValidationResult
from easter_hermes_sorry_skills.i18n.messages_en import (
    DRY_RUN_APPLIED,
    DRY_RUN_DIFF_LINE_NEW,
    DRY_RUN_DIFF_LINE_OLD,
    DRY_RUN_NOT_APPLIED,
    DRY_RUN_PATCH_LINE,
    DRY_RUN_PLAN_HEADER,
    DRY_RUN_PLAN_SUMMARY,
)


def _read_text(file_path: Path) -> str:
    r"""Return the UTF-8 text of ``file_path`` or ``""`` on ``OSError``."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _site_diff(site: Site, text: str) -> list[str]:
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
    anchor = site.primary_anchor().line
    if site.kind == "cap":
        return _cap_diff(old_lines, new_lines, anchor)
    return _additive_diff(old_lines, new_lines, anchor)


def _cap_diff(old: list[str], new: list[str], anchor: int) -> list[str]:
    r"""Return the 2-line diff block for a ``cap`` site."""
    start = anchor - 1
    return [
        DRY_RUN_DIFF_LINE_OLD.format(line=anchor, old=old[start]),
        DRY_RUN_DIFF_LINE_NEW.format(line=anchor, new=new[start]),
        DRY_RUN_DIFF_LINE_OLD.format(line=anchor + 1, old=old[start + 1]),
        DRY_RUN_DIFF_LINE_NEW.format(line=anchor + 1, new=new[start + 1]),
    ]


def _additive_diff(old: list[str], new: list[str], anchor: int) -> list[str]:
    r"""Return the ``anchor + inserted`` diff for an additive site."""
    old_idx = anchor - 1
    new_idx = anchor
    old_after = old[old_idx] if old_idx < len(old) else ""
    new_after = new[new_idx] if new_idx < len(new) else ""
    return [
        DRY_RUN_DIFF_LINE_OLD.format(line=anchor, old=old_after),
        DRY_RUN_DIFF_LINE_NEW.format(line=anchor, new=new_after),
    ]


def _plan_header(target_path: Path) -> list[str]:
    r"""Return the single-line bilingual ``plan for:`` header."""
    return [DRY_RUN_PLAN_HEADER.format(target=str(target_path))]


def _plan_tail(mode: Literal["dry_run", "apply"], count: int) -> str:
    r"""Return the trailing ``not applied`` / ``applied`` bilingual line."""
    template = DRY_RUN_NOT_APPLIED if mode == "dry_run" else DRY_RUN_APPLIED
    return template.format(count=count)


def _emit_plan(
    target_path: Path,
    sites: list[Site],
    validation: ValidationResult,
    mode: Literal["dry_run", "apply"],
) -> list[str]:
    r"""Return the bilingual plan lines for ``target_path`` + ``sites``.

    Renders the header, one ``would patch: <file> (site <id>)`` line
    per site, the per-site old/new diff preview, the summary, and the
    mode-specific tail (``not applied`` / ``applied``).

    Sites that already match (idempotency) are skipped from the
    per-site body but still counted in the summary. Drift sites are
    skipped — the plan only renders sites that WOULD be applied.
    """
    drifted_ids = {failure.get("site_id") for failure in validation.failures}
    applied = [site for site in sites if site.site_id not in drifted_ids]
    count = len(applied)
    plan = _plan_header(target_path)
    for site in applied:
        plan.append(
            DRY_RUN_PATCH_LINE.format(
                file_path=str(site.file_path),
                site_id=site.site_id,
            ),
        )
        plan.extend(_site_diff(site, _read_text(target_path / site.file_path)))
    plan.append(DRY_RUN_PLAN_SUMMARY.format(count=count))
    plan.append(_plan_tail(mode, count))
    return plan
