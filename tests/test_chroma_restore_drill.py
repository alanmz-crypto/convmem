"""Hermetic tests for chroma restore drill helpers."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chroma_store import UNITS, ChromaStore, open_chroma_for_verify

REPO = Path(__file__).resolve().parent.parent


def _load_drill():
    path = REPO / "scripts" / "chroma_restore_drill.py"
    spec = importlib.util.spec_from_file_location("chroma_restore_drill", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["chroma_restore_drill"] = mod
    spec.loader.exec_module(mod)
    return mod


drill = _load_drill()


class TestVerifyOnlyOpen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.chroma = Path(self.tmp.name) / "chroma"
        self.chroma.mkdir()
        store = ChromaStore(str(self.chroma))
        emb = [0.1] * 8
        store.add_unit(
            "u1",
            "hello",
            emb,
            {"ledger_id": "dec_prop_20260623_161428_c311", "title": "t"},
        )
        store.close()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_verify_open_refuses_missing_collection(self) -> None:
        store = open_chroma_for_verify(str(self.chroma))
        try:
            self.assertFalse(store.create_collections)
            client = store.client
            assert client is not None
            with mock.patch.object(
                client,
                "get_or_create_collection",
                side_effect=AssertionError("get_or_create must not be used"),
            ):
                self.assertEqual(store._collection(UNITS).count(), 1)
            with self.assertRaises(Exception):
                store._collection("__no_such_collection_for_drill__")
        finally:
            store.close()

    def test_fingerprint_stable_across_verify_open(self) -> None:
        before = drill.fingerprint_tree(self.chroma)
        store = open_chroma_for_verify(str(self.chroma))
        try:
            store._collection(UNITS).count()
            unit = store.get_unit("u1", include_embedding=True)
            assert unit and unit.get("embedding")
            store.query_units(unit["embedding"], top_k=1)
        finally:
            store.close()
        after = drill.fingerprint_tree(self.chroma)
        self.assertEqual(before, after)

    def test_fingerprint_changes_when_unit_added(self) -> None:
        before = drill.fingerprint_tree(self.chroma)
        store = ChromaStore(str(self.chroma))
        store.add_unit("u2", "world", [0.2] * 8, {"ledger_id": "x", "title": "t2"})
        store.close()
        self.assertNotEqual(before, drill.fingerprint_tree(self.chroma))


class TestDiscover(unittest.TestCase):
    def test_discover_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "home" / "lauer" / ".local" / "share" / "convmem" / "chroma"
            nested.mkdir(parents=True)
            (nested / "chroma.sqlite3").write_bytes(b"sqlite-bytes")
            self.assertEqual(drill.discover_chroma_root(root), nested)


class TestFixtureGate(unittest.TestCase):
    def test_rejects_older_snapshot(self) -> None:
        fixture = {"created_at": "2026-06-23T16:14:28Z"}
        snap = {"time": "2026-06-01T00:00:00-05:00"}
        with self.assertRaises(drill.DrillError) as ctx:
            drill.assert_fixture_eligible(snap, fixture)
        self.assertEqual(ctx.exception.code, "fixture_ineligible")

    def test_accepts_newer_snapshot(self) -> None:
        fixture = {"created_at": "2026-06-23T16:14:28Z"}
        snap = {"time": "2026-07-12T12:43:01.131567078-05:00"}
        drill.assert_fixture_eligible(snap, fixture)


class TestDefaultCreateFlag(unittest.TestCase):
    def test_default_creates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ChromaStore(td)
            self.assertTrue(store.create_collections)
            store.close()


if __name__ == "__main__":
    unittest.main()
