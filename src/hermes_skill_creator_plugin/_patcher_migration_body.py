"""Hermes-patch note body composer.

Split from ``_patcher_migration_render.py`` to keep module member count
under wemake's WPS202 threshold. Composes the full
``MIGRATION.hermes-patch.md`` body from a :class:`HermesPatchContext`.
"""

from __future__ import annotations

from hermes_skill_creator_plugin._patcher_migration_consts import LF
from hermes_skill_creator_plugin._patcher_migration_render import (
    HermesPatchContext,
    _yes_no,
)


def _render_migration_hermes_patch(ctx: HermesPatchContext) -> str:
    task_e_section = _build_task_e_section(ctx)
    return _build_body(ctx=ctx, task_e_section=task_e_section)


def _build_task_e_section(ctx: HermesPatchContext) -> str:
    if not ctx.task_e_redirect:
        return ""
    rows_text = "\n".join(ctx.patch_rows)
    return (
        f"{LF}## Task E sites (only if --task-e-redirect)"
        f"{LF}{LF}| site_id | location | current | replacement | anchor |"
        f"{LF}| --- | --- | --- | --- | --- |"
        f"{LF}{rows_text}{LF}"
    )


def _build_body(ctx: HermesPatchContext, *, task_e_section: str) -> str:
    header = _build_body_header(ctx)
    cap_section = _build_cap_section(ctx.cap_row)
    return f"{header}{cap_section}{task_e_section}"


def _build_body_header(ctx: HermesPatchContext) -> str:
    title = "# Hermes Patch — Script #1 (cap raise + 7 Task E sites)"
    comment = "<!-- generated; do not edit by hand -->"
    table = LF.join(_metadata_rows(ctx))
    return f"{title}{LF}{LF}{comment}{LF}{LF}{table}{LF}"


def _metadata_rows(ctx: HermesPatchContext) -> list[str]:
    target_cell = str(ctx.target.resolve())
    task_e_cell = _yes_no(ctx.task_e_redirect)
    schema_cell = _yes_no(ctx.no_schema_redirect)
    return _compose_metadata_rows(
        target_cell,
        ctx.git_head,
        task_e_cell,
        schema_cell,
        ctx.timestamp,
    )


def _compose_metadata_rows(
    target_cell: str,
    git_head: str,
    task_e_cell: str,
    schema_cell: str,
    timestamp: str,
) -> list[str]:
    return [
        "| Field | Value |",
        "| --- | --- |",
        f"| Target | {target_cell} |",
        f"| Target git head | {git_head} |",
        f"| --task-e-redirect | {task_e_cell} |",
        f"| --no-schema-redirect | {schema_cell} |",
        f"| Generated at | {timestamp} |",
    ]


def _build_cap_section(cap_row: str) -> str:
    heading = "## Cap-raise site (always applied)"
    header_row = "| site_id | location | current | replacement | anchor |"
    divider = "| --- | --- | --- | --- | --- |"
    return f"{LF}{heading}{LF}{LF}{header_row}{LF}{divider}{LF}{cap_row}{LF}"
