"""Strength-preservation row helpers for the migration note.

Split from ``_skill_installer_note`` (WPS202 module surface budget).
Each strength row gets its own tiny builder; the renderer glues them
together via :func:`_render_strength_rows`.
"""

from __future__ import annotations


def _row_subagent_split() -> str:
    """Strength row: Subagent split (artifact → delegate_task)."""
    return "| Subagent split | agents/{grader,analyzer,comparator}.md | delegate_task + agent_name | T3.012-T3.014 |"


def _row_eval_pipeline() -> str:
    """Strength row: Eval pipeline (artifact → Hermes CLI adapter)."""
    return (
        "| Eval pipeline | "
        "scripts/{run_eval, aggregate_benchmark, "
        "generate_report, ...}.py |"
        " same scripts, Hermes CLI, event-shape adapter |"
        " T3.003, T3.011, T3.006 |"
    )


def _row_eval_viewer() -> str:
    """Strength row: Eval viewer (artifact → generate_review.py)."""
    return (
        "| Eval viewer | eval-viewer/{generate_review.py, viewer.html} |"
        " generate_review.py --static, file:// URL | T3.015 |"
    )


def _render_strength_rows() -> list[str]:
    return [
        "",
        "## Strength preservation",
        "",
        "| Strength | Artifact | Hermes equivalent | AC |",
        "| --- | --- | --- | --- |",
        _row_subagent_split(),
        _row_eval_pipeline(),
        _row_eval_viewer(),
        "",
    ]
