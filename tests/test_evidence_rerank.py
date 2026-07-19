"""Tests for evidence-aware retrieval ranking (Milestone E)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from evidence import apply_evidence_rerank, evidence_boost, recency_boost


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

    def test_evidence_rerank_uses_cross_encoder_score_as_base(self):
        store = FakeStore([])
        results = [
            {
                "id": "semantic-high",
                "score": 0.95,
                "rerank_score_norm": 0.2,
                "metadata": {},
                "document": "a",
            },
            {
                "id": "rerank-high",
                "score": 0.60,
                "rerank_score_norm": 0.9,
                "metadata": {},
                "document": "b",
            },
        ]

        ranked = apply_evidence_rerank(results, store)

        self.assertEqual(ranked[0]["id"], "rerank-high")
        self.assertEqual(ranked[0]["rank_score"], 0.9)

    # -- recency_boost --------------------------------------------------------

    def test_recency_boost_recent(self):
        """A 6-day-old entry gets ~0.082 with weight=0.1 and half-life=30."""
        ts = (datetime.now(timezone.utc) - timedelta(days=6)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        boost = recency_boost({"timestamp": ts}, weight=0.1, half_life_days=30)
        self.assertAlmostEqual(boost, 0.0819, places=3)

    def test_recency_boost_half_life(self):
        """At exactly half-life days, boost = weight * exp(-1)."""
        ts = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        boost = recency_boost({"timestamp": ts}, weight=0.1, half_life_days=30)
        self.assertAlmostEqual(boost, 0.0368, places=3)

    def test_recency_boost_no_timestamp(self):
        boost = recency_boost({}, weight=0.1)
        self.assertEqual(boost, 0.0)

    def test_recency_boost_weight_zero(self):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        boost = recency_boost({"timestamp": ts}, weight=0.0)
        self.assertEqual(boost, 0.0)

    def test_recency_boost_date_only(self):
        """Plain YYYY-MM-DD timestamps should parse."""
        ts = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        boost = recency_boost({"timestamp": ts}, weight=0.1, half_life_days=30)
        self.assertGreater(boost, 0.08)

    def test_recency_in_rerank(self):
        """Newer unit gets recency boost and moves above older unit."""
        store = FakeStore([])
        recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        results = [
            {"id": "old", "score": 0.85, "metadata": {"timestamp": old_ts, "type": "observation"}, "document": "old"},
            {"id": "new", "score": 0.85, "metadata": {"timestamp": recent_ts, "type": "observation"}, "document": "new"},
        ]
        ranked = apply_evidence_rerank(results, store, recency_weight=0.2)
        self.assertEqual(ranked[0]["id"], "new")
        self.assertGreater(ranked[0]["recency_boost"], ranked[1]["recency_boost"])

    def test_apply_recency_rerank_only(self):
        """Search path: recency without evidence graph."""
        recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        results = [
            {"id": "old", "score": 0.85, "metadata": {"timestamp": old_ts}},
            {"id": "new", "score": 0.85, "metadata": {"timestamp": recent_ts}},
        ]
        from evidence import apply_recency_rerank

        ranked = apply_recency_rerank(results, recency_weight=0.2)
        self.assertEqual(ranked[0]["id"], "new")
        self.assertIn("rank_score", ranked[0])
        self.assertNotIn("evidence_status", ranked[0])

    def test_apply_recency_rerank_weight_zero_noop(self):
        from evidence import apply_recency_rerank

        results = [{"id": "a", "score": 0.5, "metadata": {}}]
        self.assertIs(apply_recency_rerank(results, recency_weight=0.0), results)


if __name__ == "__main__":
    unittest.main()
