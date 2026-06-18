"""Tests for ledger evidence-chain traversal (Milestone B)."""

from __future__ import annotations

import time
import unittest

from ledger import (
    build_ledger_index,
    find_related_units,
    normalize_ledger_record,
    related_chain,
    resolve_unit_ref,
)


class FakeStore:
    def __init__(self, metas: list[dict]):
        self._metas = [dict(m) for m in metas]
        self._units = {
            m["id"]: {"id": m["id"], "metadata": m, "document": m.get("title", "")}
            for m in self._metas
        }

    def units_metadata(self):
        return self._metas

    def get_unit(self, uid: str):
        return self._units.get(uid)


def _chain_fixture() -> FakeStore:
    return FakeStore(
        [
            {
                "id": "c-obs",
                "ledger_id": "obs001",
                "ledger_kind": "observation",
                "type": "observation",
                "title": "Missing CSP header",
                "domain": "web_stack.security",
            },
            {
                "id": "c-dec3",
                "ledger_id": "dec_003",
                "ledger_kind": "decision",
                "type": "decision",
                "title": "Add CSP through nginx",
                "relates_to": "obs001",
                "status": "accepted",
            },
            {
                "id": "c-dec5",
                "ledger_id": "dec_005",
                "ledger_kind": "decision",
                "type": "decision",
                "title": "Reject plugin workaround",
                "relates_to": "obs001",
                "status": "rejected",
            },
            {
                "id": "c-ver2",
                "ledger_id": "ver_002",
                "ledger_kind": "verification",
                "type": "observation",
                "title": "CSP header present",
                "relates_to": "obs001",
                "result": "pass",
                "confidence": 0.95,
                "author_model": "kiro-review",
            },
            {
                "id": "legacy-1",
                "type": "observation",
                "title": "Pre-ledger chat chunk",
                "ledger_id": "",
                "relates_to": "",
            },
            {
                "id": "legacy-2",
                "type": "observation",
                "title": "Another legacy unit",
            },
        ]
    )


class LedgerRelatedTests(unittest.TestCase):
    def test_observation_lookup(self):
        store = _chain_fixture()
        chain = related_chain(store, "obs001")
        assert chain is not None
        self.assertEqual(chain["target_kind"], "observation")
        self.assertEqual(len(chain["decisions"]), 2)
        self.assertEqual(len(chain["verifications"]), 1)

    def test_decision_lookup(self):
        store = _chain_fixture()
        chain = related_chain(store, "dec_003")
        assert chain is not None
        self.assertEqual(chain["target_kind"], "decision")
        self.assertEqual(chain["anchor_id"], "obs001")
        self.assertEqual(len(chain["siblings"]), 1)
        self.assertEqual(chain["siblings"][0]["ledger_id"], "dec_005")

    def test_verification_lookup(self):
        store = _chain_fixture()
        chain = related_chain(store, "ver_002")
        assert chain is not None
        self.assertEqual(chain["target_kind"], "verification")
        self.assertEqual(chain["observation"]["ledger_id"], "obs001")
        self.assertEqual(len(chain["decisions"]), 2)

    def test_find_related_units(self):
        store = _chain_fixture()
        related = find_related_units(store, "obs001")
        lids = {m["ledger_id"] for m in related}
        self.assertEqual(lids, {"dec_003", "dec_005", "ver_002"})

    def test_not_found(self):
        store = _chain_fixture()
        self.assertIsNone(related_chain(store, "obs999"))

    def test_legacy_units_ignored(self):
        store = _chain_fixture()
        by_id, by_rel = build_ledger_index(store)
        self.assertNotIn("legacy-1", by_id)
        self.assertNotIn("", by_rel)
        self.assertEqual(find_related_units(store, ""), [])

    def test_resolve_unit_ref_by_ledger_id(self):
        store = _chain_fixture()
        hit = resolve_unit_ref(store, "dec_003")
        assert hit is not None
        self.assertEqual(hit["metadata"]["ledger_id"], "dec_003")

    def test_orphan_decision_rejected_at_ingest(self):
        raw = {
            "id": "dec_orphan",
            "kind": "decision",
            "summary": "Fix without parent",
            "author_model": "kiro-review",
        }
        self.assertIsNone(normalize_ledger_record(raw))

    def test_orphan_verification_rejected_at_ingest(self):
        raw = {
            "id": "ver_orphan",
            "kind": "verification",
            "summary": "Checked nothing",
            "author_model": "kiro-review",
            "result": "pass",
        }
        self.assertIsNone(normalize_ledger_record(raw))

    def test_related_runtime_under_100ms(self):
        metas = []
        for i in range(1500):
            metas.append(
                {
                    "id": f"u{i}",
                    "ledger_id": f"obs{i:04d}",
                    "ledger_kind": "observation",
                    "type": "observation",
                    "title": f"Finding {i}",
                    "domain": "web_stack.security",
                }
            )
        metas.append(
            {
                "id": "c-dec",
                "ledger_id": "dec_target",
                "ledger_kind": "decision",
                "type": "decision",
                "title": "Decision",
                "relates_to": "obs0142",
            }
        )
        store = FakeStore(metas)
        start = time.perf_counter()
        for _ in range(20):
            related_chain(store, "obs0142")
            related_chain(store, "dec_target")
        elapsed_ms = (time.perf_counter() - start) / 20 * 1000
        self.assertLess(elapsed_ms, 100.0, f"related_chain took {elapsed_ms:.1f}ms")


if __name__ == "__main__":
    unittest.main()
