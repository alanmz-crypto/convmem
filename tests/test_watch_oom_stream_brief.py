"""C2–C4 tests for metadata-iterable ledger/unresolved and brief no-retention."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ledger as _ledger

from chroma_readonly import open_readonly_unit_store
from unresolved import list_unresolved, list_unresolved_from_metadata
from brief import BRIEF_PROJECTION_FIELDS, gather_brief_data, write_brief
from tests.watch_oom_brief_hermetic import (
    FORBIDDEN_BRIEF_KEYS,
    EXPECTED_UNRESOLVED_COUNT,
    freeze_brief_probes,
    write_c0_fixture,
)
from tests.watch_oom_exposure_hermetic import trap_iter_collection_metadata_rows

# pylint cannot infer several ledger.py exports (baseline E0611 on the same
# names). Look them up on the live module instead of a from-import.
_LEDGER_INDEX_CACHE = _ledger.__dict__["_LEDGER_INDEX_CACHE"]
build_ledger_index = _ledger.__dict__["build_ledger_index"]
build_ledger_index_from_metadata = _ledger.__dict__["build_ledger_index_from_metadata"]
invalidate_ledger_index_cache = _ledger.__dict__["invalidate_ledger_index_cache"]


class MetadataIterableLedgerTests(unittest.TestCase):
    def test_index_and_unresolved_match_store_apis(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            store = open_readonly_unit_store(fx["chroma_dir"])
            invalidate_ledger_index_cache()
            from_store = build_ledger_index(store)
            from_rows = build_ledger_index_from_metadata(store.units_metadata())
            self.assertEqual(set(from_store[0]), set(from_rows[0]))
            self.assertEqual(
                {k: [m.get("ledger_id") for m in v] for k, v in from_store[1].items()},
                {k: [m.get("ledger_id") for m in v] for k, v in from_rows[1].items()},
            )
            store_unresolved = list_unresolved(store)
            meta_unresolved = list_unresolved_from_metadata(store.units_metadata())
            self.assertEqual(
                [r["ledger_id"] for r in store_unresolved],
                [r["ledger_id"] for r in meta_unresolved],
            )
            self.assertEqual(len(store_unresolved), EXPECTED_UNRESOLVED_COUNT)


class BriefNoRetentionTests(unittest.TestCase):
    def test_brief_does_not_construct_store_or_mutate_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            invalidate_ledger_index_cache()
            cache_before = dict(_LEDGER_INDEX_CACHE)

            def boom(*_a, **_k):
                raise AssertionError("brief must not construct ReadonlyUnitStore")

            with freeze_brief_probes(), patch(
                "chroma_readonly.ReadonlyUnitStore", side_effect=boom
            ), patch(
                "chroma_readonly.open_readonly_unit_store", side_effect=boom
            ):
                data = gather_brief_data(fx["cfg"])
            self.assertEqual(data["unresolved_count"], EXPECTED_UNRESOLVED_COUNT)
            self.assertEqual(_LEDGER_INDEX_CACHE, cache_before)

    def test_projection_trap_and_forbidden_provenance_calls(self) -> None:
        seen_keys: set[str] = set()

        include_doc: list[bool] = []
        wrapped = trap_iter_collection_metadata_rows(seen_keys, include_doc)

        def forbidden_call(*_a, **_k):
            raise AssertionError("brief path must not call provenance identity helpers")

        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            with freeze_brief_probes(), patch(
                "brief.iter_collection_metadata_rows", wrapped
            ), patch(
                "evidence.filter_superseded_decisions", side_effect=forbidden_call
            ), patch(
                "provenance_binding.provenance_identity", side_effect=forbidden_call
            ):
                data = gather_brief_data(fx["cfg"])
        self.assertTrue(seen_keys)
        for forbidden in FORBIDDEN_BRIEF_KEYS:
            self.assertNotIn(forbidden, seen_keys)
        for row in data["recent_decisions"] + data["recent_monitor"]:
            for forbidden in FORBIDDEN_BRIEF_KEYS:
                self.assertNotIn(forbidden, row)
            extras = set(row) - set(BRIEF_PROJECTION_FIELDS)
            self.assertFalse(extras, extras)

    def test_iterator_failure_is_fail_soft_on_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            out = Path(td) / "brief.md"
            with freeze_brief_probes(), patch("brief.DEFAULT_BRIEF_PATH", out):
                write_brief(fx["cfg"], out_path=out, quiet=True)
                prior = out.read_text(encoding="utf-8")

                def boom(*_a, **_k):
                    raise RuntimeError("scan failed")

                with patch("brief._iter_brief_rows", boom):
                    from brief import refresh_brief_after_change

                    refresh_brief_after_change(fx["cfg"])
                self.assertEqual(out.read_text(encoding="utf-8"), prior)

    def test_unresolved_error_yields_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            with freeze_brief_probes(), patch(
                "unresolved.list_unresolved_from_metadata",
                side_effect=RuntimeError("graph failed"),
            ):
                data = gather_brief_data(fx["cfg"])
        self.assertIsNone(data["unresolved_count"])
        self.assertEqual(len(data["recent_decisions"]), 5)


if __name__ == "__main__":
    unittest.main()
