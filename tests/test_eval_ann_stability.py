"""ANN repeatability status separates invalid captures from instability."""

from __future__ import annotations

from eval_corpus.ann_stability import assess_ann_repeatability


def _realizations():
    rows = {"q1": ["a", "b", "c", "d", "e"], "q2": ["f", "g", "h", "i", "j"]}
    return {"baseline-0": rows, "baseline-1": rows.copy(), "baseline-2": rows.copy()}


def test_stable_realizations_preserve_verdict():
    result = assess_ann_repeatability(
        _realizations(),
        {"baseline-0": "BETTER", "baseline-1": "BETTER", "baseline-2": "BETTER"},
    )
    assert result["technical_status"] == "VALID"
    assert result["ann_stability"] == "STABLE"
    assert result["evidence_verdict"] == "BETTER"
    assert result["mean_pairwise_top5_jaccard"] == 1.0


def test_instability_forces_inconclusive_but_remains_valid():
    realizations = _realizations()
    realizations["baseline-2"] = {
        "q1": ["z", "b", "c", "d", "e"],
        "q2": ["z", "g", "h", "i", "j"],
    }
    result = assess_ann_repeatability(
        realizations,
        {"baseline-0": "BETTER", "baseline-1": "BETTER", "baseline-2": "BETTER"},
    )
    assert result["technical_status"] == "VALID"
    assert result["ann_stability"] == "UNSTABLE"
    assert result["evidence_verdict"] == "INCONCLUSIVE"


def test_malformed_realization_is_invalid_not_inconclusive():
    realizations = _realizations()
    realizations["baseline-1"]["q1"] = ["a", "a", "c", "d", "e"]
    result = assess_ann_repeatability(
        realizations,
        {"baseline-0": "BETTER", "baseline-1": "BETTER", "baseline-2": "BETTER"},
    )
    assert result["technical_status"] == "INVALID"
    assert result["evidence_verdict"] == "NOT_ISSUED"
