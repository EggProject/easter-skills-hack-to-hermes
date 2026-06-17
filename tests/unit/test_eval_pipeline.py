"""Unit tests for the eval pipeline end-to-end + viewer.

Per docs/plans/07 §TDD test list (Eval pipeline + viewer).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from hermes_skill_creator_plugin import assert_hermes_agent_untouched  # noqa: F401


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "skill-creator"
SCRIPTS = SKILL_DIR / "scripts"
EVAL_VIEWER = SKILL_DIR / "eval-viewer"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Event shape adapter (T3.011)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_event_shape_adapter_handles_known_shapes(skill_creator_home: Path) -> None:
    """Parametrize over candidate Hermes event shapes; the adapter normalizes
    each into the Anthropic-shaped dict.
    """
    run_eval = _load(SCRIPTS / "run_eval.py", "adapter_test")
    samples = [
        {"event": "message", "role": "assistant", "content": "hello"},
        {"event": "tool_use", "role": "assistant", "content": [{"type": "tool_use", "name": "read_file"}]},
        {"type": "message", "role": "assistant", "content": "fallback"},
        {"event": "message", "content": "no-role"},
    ]
    for sample in samples:
        out = run_eval._hermes_event_to_anthropic(sample)
        assert "type" in out
        assert "message" in out
        assert "role" in out["message"]
        assert isinstance(out["message"]["content"], list)


# ---------------------------------------------------------------------------
# aggregate_benchmark: parses Hermes stream-json
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_aggregate_benchmark_parses_hermes_stream_json(skill_creator_home: Path) -> None:
    """Feed a fixture with Anthropic-shaped events (the adapter's output);
    aggregator computes per-case scores + aggregate metrics.
    """
    agg = _load(SCRIPTS / "aggregate_benchmark.py", "agg_test")
    fixture = [
        {
            "case": {"id": "a"},
            "events": [
                {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "score: 0.8"}]}}
            ],
        },
        {
            "case": {"id": "b"},
            "events": [
                {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "score: 0.6"}]}}
            ],
        },
    ]
    result = agg.aggregate(fixture)
    assert result["aggregate"]["mean"] == pytest.approx(0.7, abs=1e-9)
    assert {pc["case_id"] for pc in result["per_case"]} == {"a", "b"}


@assert_hermes_agent_untouched
def test_aggregate_benchmark_handles_empty_results(skill_creator_home: Path) -> None:
    agg = _load(SCRIPTS / "aggregate_benchmark.py", "agg_empty_test")
    result = agg.aggregate([])
    assert result["aggregate"]["mean"] == 0.0
    assert result["per_case"] == []


# ---------------------------------------------------------------------------
# Eval pipeline end-to-end (AC-4.11) — uses subprocess.run spy
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_eval_pipeline_end_to_end(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """2-case eval; assert report.md + feedback.json are produced with the
    expected schema.
    """
    import subprocess as sp

    call_count = {"n": 0}
    outputs = [
        '{"event": "message", "role": "assistant", "content": "score: 0.7"}\n',
        '{"event": "message", "role": "assistant", "content": "score: 0.5"}\n',
    ]

    class _FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        proc = _FakeProc()
        proc.stdout = outputs[call_count["n"]]
        call_count["n"] += 1
        return proc

    monkeypatch.setattr(sp, "run", _fake_run)

    run_eval = _load(SCRIPTS / "run_eval.py", "e2e_run_eval")
    cases = [{"id": "a"}, {"id": "b"}]
    results = run_eval.run_eval(
        cases, hermes_home=skill_creator_home, category="c", target="t"
    )
    assert len(results) == 2
    # Each result has Anthropic-shaped events (translated by the adapter).
    for r in results:
        assert "events" in r
        for ev in r["events"]:
            assert "type" in ev
            assert "message" in ev

    # Aggregate + report.
    agg = _load(SCRIPTS / "aggregate_benchmark.py", "e2e_agg")
    metrics = agg.aggregate(results)
    assert metrics["aggregate"]["mean"] == pytest.approx(0.6, abs=1e-9)

    gen = _load(SCRIPTS / "generate_report.py", "e2e_gen")
    out_dir = tmp_path / "out"
    report, feedback = gen.generate_report(metrics, out_dir=out_dir)
    assert report.exists()
    assert feedback.exists()
    assert "Aggregate" in report.read_text(encoding="utf-8")
    feedback_data = json.loads(feedback.read_text(encoding="utf-8"))
    assert "aggregate" in feedback_data


# ---------------------------------------------------------------------------
# Eval viewer static-open (AC-4.16)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_eval_viewer_static_open(
    skill_creator_home: Path, tmp_path: Path
) -> None:
    """generate_review.py --static writes both files; the HTML's JS reads
    feedback.json via a relative path under the same dir.
    """
    gen = _load(EVAL_VIEWER / "generate_review.py", "viewer_test")
    feedback = {"aggregate": {"mean": 0.7}, "per_case": []}
    out_dir = tmp_path / "review"
    json_path, html_path = gen.write_static(feedback, out_dir=out_dir)
    assert json_path == out_dir / "feedback.json"
    assert html_path == out_dir / "viewer.html"
    html = html_path.read_text(encoding="utf-8")
    # The HTML must reference feedback.json via a relative path.
    assert "feedback.json" in html
    # The relative path must resolve to the same dir (no `../`).
    assert "../" not in html.split("feedback.json")[0].split("fetch('")[-1]


# ---------------------------------------------------------------------------
# Subagent registration matches Anthropic roles (AC-4.17)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_subagent_registration_matches_anthropic_roles(
    skill_creator_home: Path,
) -> None:
    """For each agents/*.md, the registered agent_name + description +
    toolset match the Anthropic file's role (grader / analyzer / comparator).
    """
    import re

    role_to_file = {
        "grader": SKILL_DIR / "agents" / "grader.md",
        "analyzer": SKILL_DIR / "agents" / "analyzer.md",
        "comparator": SKILL_DIR / "agents" / "comparator.md",
    }
    for role, path in role_to_file.items():
        text = path.read_text(encoding="utf-8")
        # agent_name is the role.
        m = re.search(r"agent_name:\s*(\S+)", text)
        assert m is not None, f"{path}: missing agent_name"
        assert m.group(1) == role
        # description is a non-empty string.
        desc_m = re.search(r"description:\s*\|?\s*\n((?:  .+\n)+)", text)
        assert desc_m is not None, f"{path}: missing description"
        assert len(desc_m.group(1).strip()) > 0
        # toolsets is a YAML list.
        ts_m = re.search(r"toolsets:\s*\[([^\]]+)\]", text)
        assert ts_m is not None, f"{path}: missing toolsets"


# ---------------------------------------------------------------------------
# run_eval writes SKILL.md to HERMES_HOME/skills/<cat>/<target>/ (not .claude)
# ---------------------------------------------------------------------------


@assert_hermes_agent_untouched
def test_run_eval_writes_skill_md_to_hermes_home_not_dot_claude(
    skill_creator_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess as sp

    class _FakeProc:
        returncode = 0
        stdout = '{"event": "message", "role": "assistant", "content": "x"}\n'
        stderr = ""

    monkeypatch.setattr(sp, "run", lambda *a, **kw: _FakeProc())
    run_eval = _load(SCRIPTS / "run_eval.py", "write_path_test")
    run_eval.run_eval(
        [{"id": "a"}], hermes_home=skill_creator_home, category="mycat", target="mytarget"
    )
    expected = skill_creator_home / "skills" / "mycat" / "mytarget" / "SKILL.md"
    assert expected.exists(), f"expected {expected} to be written"
    # NOT in .claude/commands
    assert not (skill_creator_home / ".claude").exists()
