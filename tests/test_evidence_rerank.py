"""Tests for evidence-aware retrieval ranking (Milestone E)."""

from __future__ import annotations

import unittest

from evidence import apply_evidence_rerank, evidence_boost


def _meta(
    ledger_id: str,
    *,
    kind: str = "observation",
    result: str = "",
    verifier: str = "",
) -> dict:
    m = {
        "ledger_id": ledger_id,
        "ledger_kind": kind,
        "type": "observation" if kind == "verification" else kind,
    }
    if result:
        m["result"] = result
    if verifier:
        m["verifier_model"] = verifier
        m["verification_result"] = result or "pass"
    return m


class FakeStore:
    def __init__(self, metas: list[dict]):
        self._metas = metas

    def units_metadata(self):
        return self._metas


class EvidenceRerankTests(unittest.TestCase):
    def setUp(self):
        self.by_relates = {
            "obs_resolved": [
                _meta("ver_1", kind="verification", result="pass"),
            ],
            "obs_failed": [
                _meta("ver_2", kind="verification", result="fail"),
            ],
        }

    def test_unresolved_boosted_over_resolved(self):
        unresolved = _meta("obs_open")
        resolved = _meta("obs_resolved")
        bu, br = evidence_boost(unresolved, by_relates_to=self.by_relates)
        bres, sr = evidence_boost(resolved, by_relates_to=self.by_relates)
        self.assertEqual(sr, "resolved")
        self.assertGreater(bu, bres)

    def test_failed_check_boosted(self):
        boost, status = evidence_boost(
            _meta("obs_failed"), by_relates_to=self.by_relates
        )
        self.assertEqual(status, "failed_check")
        self.assertGreater(boost, 0)

    def test_failed_verification_boosted(self):
        boost, status = evidence_boost(
            _meta("ver_x", kind="verification", result="fail"),
            by_relates_to={},
        )
        self.assertEqual(status, "failed_verification")
        self.assertGreater(boost, 0)

    def test_legacy_unit_no_boost(self):
        boost, status = evidence_boost({"type": "observation"}, by_relates_to={})
        self.assertEqual(boost, 0.0)
        self.assertEqual(status, "")

    def test_verifier_model_without_pass_not_resolved(self):
        """verifier_model on obs must not imply resolved without verification_result=pass."""
        meta = _meta("obs_checked", verifier="kiro-review")
        meta["verification_result"] = "fail"
        boost, status = evidence_boost(meta, by_relates_to={})
        self.assertNotEqual(status, "resolved")
        self.assertGreater(boost, 0)

    def test_rerank_ordering(self):
        store = FakeStore(
            [
                {**_meta("obs_resolved"), "id": "c1"},
                {**_meta("obs_open"), "id": "c2"},
                {
                    **_meta("ver_1", kind="verification", result="pass"),
                    "id": "c6",
                    "relates_to": "obs_resolved",
                },
            ]
        )
        results = [
            {"id": "c1", "score": 0.92, "metadata": _meta("obs_resolved"), "document": "resolved"},
            {"id": "c2", "score": 0.70, "metadata": _meta("obs_open"), "document": "open"},
        ]
        ranked = apply_evidence_rerank(results, store)
        self.assertEqual(ranked[0]["id"], "c2")
        self.assertEqual(ranked[0]["evidence_status"], "unresolved")
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])


if __name__ == "__main__":
    unittest.main()
