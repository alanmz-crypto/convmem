"""C1 tests for projected streaming Chroma metadata iteration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chroma_readonly import (
    collection_metadata_rows,
    iter_collection_metadata_rows,
)
from tests.watch_oom_brief_hermetic import (
    FORBIDDEN_BRIEF_KEYS,
    BRIEF_SQL_METADATA_KEYS,
    write_c0_fixture,
    write_chroma_sqlite,
)


class IterCollectionMetadataTests(unittest.TestCase):
    def test_full_mode_matches_list_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            listed = collection_metadata_rows(fx["chroma_dir"], "knowledge_units")
            streamed = list(
                iter_collection_metadata_rows(fx["chroma_dir"], "knowledge_units")
            )
        self.assertEqual(listed, streamed)
        self.assertTrue(any(row.get("provenance_envelope") for row in listed))

    def test_projection_omits_forbidden_keys_and_keeps_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            rows = list(
                iter_collection_metadata_rows(
                    fx["chroma_dir"],
                    "knowledge_units",
                    metadata_keys=BRIEF_SQL_METADATA_KEYS,
                    include_document=True,
                )
            )
        self.assertTrue(rows)
        for row in rows:
            for forbidden in FORBIDDEN_BRIEF_KEYS:
                self.assertNotIn(forbidden, row)
        self.assertTrue(any(row.get("rationale") for row in rows))
        self.assertTrue(any("document" in row for row in rows))

    def test_include_document_false_skips_document_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            rows = list(
                iter_collection_metadata_rows(
                    fx["chroma_dir"],
                    "knowledge_units",
                    metadata_keys=("title",),
                    include_document=False,
                )
            )
        self.assertTrue(rows)
        self.assertTrue(all("document" not in row for row in rows))

    def test_missing_collection_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            rows = list(iter_collection_metadata_rows(fx["chroma_dir"], "nope"))
        self.assertEqual(rows, [])

    def test_empty_collection_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_chroma_sqlite(chroma, {"knowledge_units": []})
            rows = list(iter_collection_metadata_rows(chroma, "knowledge_units"))
        self.assertEqual(rows, [])

    def test_missing_db_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                list(iter_collection_metadata_rows(td, "knowledge_units"))

    def test_readonly_leaves_mtime_and_no_wal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            db = fx["chroma_dir"] / "chroma.sqlite3"
            canary = fx["chroma_dir"] / "canary.txt"
            canary.write_text("ok", encoding="utf-8")
            before = db.stat().st_mtime_ns
            list(iter_collection_metadata_rows(fx["chroma_dir"], "knowledge_units"))
            self.assertEqual(db.stat().st_mtime_ns, before)
            self.assertFalse((fx["chroma_dir"] / "chroma.sqlite3-wal").exists())
            self.assertFalse((fx["chroma_dir"] / "chroma.sqlite3-shm").exists())
            self.assertEqual(canary.read_text(encoding="utf-8"), "ok")

    def test_exception_closes_connection(self) -> None:
        import os

        def sqlite_fds() -> set[str]:
            found: set[str] = set()
            for entry in Path("/proc/self/fd").iterdir():
                try:
                    target = os.readlink(entry)
                except OSError:
                    continue
                if target.endswith("chroma.sqlite3"):
                    found.add(target)
            return found

        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            before = sqlite_fds()

            def boom(*_a, **_k):
                raise RuntimeError("row explode")

            with patch("chroma_readonly._apply_metadata_row", side_effect=boom):
                with self.assertRaises(RuntimeError):
                    list(
                        iter_collection_metadata_rows(
                            fx["chroma_dir"], "knowledge_units"
                        )
                    )
            self.assertEqual(sqlite_fds(), before)

    def test_early_close_closes_connection(self) -> None:
        import os

        def sqlite_fds() -> set[str]:
            found: set[str] = set()
            for entry in Path("/proc/self/fd").iterdir():
                try:
                    target = os.readlink(entry)
                except OSError:
                    continue
                if target.endswith("chroma.sqlite3"):
                    found.add(target)
            return found

        with tempfile.TemporaryDirectory() as td:
            fx = write_c0_fixture(Path(td))
            before = sqlite_fds()
            it = iter_collection_metadata_rows(fx["chroma_dir"], "knowledge_units")
            self.assertIsNotNone(next(it))
            self.assertTrue(sqlite_fds() - before)
            it.close()
            self.assertEqual(sqlite_fds(), before)


if __name__ == "__main__":
    unittest.main()
