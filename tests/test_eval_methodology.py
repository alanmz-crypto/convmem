"""Effect tests for shared eval/judge negative controls."""

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys

import pytest

from eval_methodology import run_judge_negative_control

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FakeJudgeResult:
    score: int | None
    reason: str = "test"
    independent: bool = True
    judge_model: str = "judge"


@pytest.mark.parametrize("kind", ["summary", "synthesis"])
def test_known_bad_control_requires_score_below_three(kind):
    result = run_judge_negative_control(
        kind,
        under_test_model="candidate",
        cfg={},
        judge_fn=lambda *_args, **_kwargs: FakeJudgeResult(score=2),
    )
    assert result["passed"] is True
    assert result["threshold"] == "<3"


@pytest.mark.parametrize("score", [3, 4, 5, None])
def test_weak_or_missing_rejection_fails_closed(score):
    result = run_judge_negative_control(
        "summary",
        under_test_model="candidate",
        cfg={},
        judge_fn=lambda *_args, **_kwargs: FakeJudgeResult(score=score),
    )
    assert result["passed"] is False


def test_unknown_control_kind_refuses():
    with pytest.raises(ValueError, match="unknown negative-control kind"):
        run_judge_negative_control(
            "other",
            under_test_model="candidate",
            cfg={},
            judge_fn=lambda *_args, **_kwargs: FakeJudgeResult(score=1),
        )


@pytest.mark.parametrize(
    ("script_name", "report"),
    [
        (
            "eval-summaries.py",
            {
                "count": 1,
                "structural_pass_rate": 1.0,
                "keyword_recall": 1.0,
                "results": [],
                "judge_independent": True,
                "judge_mean": 5.0,
                "judge_model": "judge",
            },
        ),
        (
            "eval-synthesis.py",
            {
                "count": 1,
                "pass_rate": 1.0,
                "abstain_correct": True,
                "results": [],
                "judge_independent": True,
                "judge_mean": 5.0,
                "judge_model": "judge",
            },
        ),
    ],
)
def test_failed_control_blocks_baseline_update(
    script_name, report, monkeypatch, tmp_path
):
    """A good candidate score cannot hide a failed known-bad control."""
    script_path = REPO_ROOT / "scripts" / script_name
    module_name = "test_" + script_name.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    baseline = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(sys, "argv", [
        script_name,
        "--judge",
        "--update-baseline",
        "--baseline",
        str(baseline),
    ])
    monkeypatch.setattr("config.load_config", lambda: {"models": {}})
    monkeypatch.setattr(module, "load_golden", lambda _path: [{}])
    candidate_row = (
        {
            "id": "candidate",
            "structural_pass": True,
            "keyword_recall": 1.0,
            "n_sentences": 3,
            "n_keywords": 5,
            "missing_mentions": [],
        }
        if script_name == "eval-summaries.py"
        else {
            "id": "candidate",
            "pass": True,
            "mode": "answer",
            "n_citations": 1,
            "detail": {},
        }
    )
    monkeypatch.setattr(
        module, "eval_row", lambda *_args, **_kwargs: candidate_row
    )
    monkeypatch.setattr(module, "summarize_report", lambda *_args, **_kwargs: dict(report))
    monkeypatch.setattr("eval_provenance.model_context", lambda *_args, **_kwargs: {})
    if hasattr(module, "_synth_model"):
        monkeypatch.setattr(module, "_synth_model", lambda _cfg: "candidate")
    monkeypatch.setattr(
        "eval_methodology.run_judge_negative_control",
        lambda *_args, **_kwargs: {
            "passed": False,
            "score": 5,
            "threshold": "<3",
        },
    )

    assert module.main() == 1
    assert not baseline.exists()
