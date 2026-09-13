# pylint: disable=consider-using-with
"""C0 golden freeze of knowledge_units.jsonl export compaction semantics.

Valid-row cases are the replacement oracle. Malformed cases document the
legacy implementation's unsafe behavior and the intentional fail-closed
hardening required after C2.
"""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from export_compaction import InvalidExportRecordError
from ingest import _deduplicate_units_export_impl


def _write_export(path: Path, data: bytes | str, mode: int = 0o640) -> None:
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    path.write_bytes(raw)
    os.chmod(path, mode)


class ExportCompactionGoldenTests(unittest.TestCase):
    """Freeze current compaction results before the bounded replacement."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "knowledge_units.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _compact(self) -> int:
        return _deduplicate_units_export_impl(self.path)

    def test_missing_file_returns_zero(self) -> None:
        missing = self.dir / "absent.jsonl"
        self.assertEqual(_deduplicate_units_export_impl(missing), 0)
        self.assertFalse(missing.exists())

    def test_all_unique_valid_rows_are_byte_identical_noop(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"b","v":2}\n'
        _write_export(self.path, original)
        mtime = self.path.stat().st_mtime_ns
        self.assertEqual(self._compact(), 0)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)

    def test_unique_without_trailing_newline_is_noop(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"b","v":2}'
        _write_export(self.path, original)
        self.assertEqual(self._compact(), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_blank_and_whitespace_lines_are_not_records(self) -> None:
        original = b'   \n{"id":"a"}\n'
        _write_export(self.path, original)
        self.assertEqual(self._compact(), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_duplicates_retain_last_value_in_first_id_order(self) -> None:
        _write_export(
            self.path,
            '{"id":"a","v":1}\n{"id":"b","v":2}\n{"id":"a","v":3}\n',
        )
        self.assertEqual(self._compact(), 1)
        self.assertEqual(
            self.path.read_bytes(),
            b'{"id":"a","v":3}\n{"id":"b","v":2}\n',
        )

    def test_blank_lines_do_not_count_and_last_value_still_wins(self) -> None:
        _write_export(self.path, '\n{"id":"a","v":1}\n\n{"id":"a","v":2}\n')
        self.assertEqual(self._compact(), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_stripped_whitespace_around_json_on_rewrite(self) -> None:
        _write_export(self.path, '  {"id":"a","v":1}  \n{"id":"a","v":2}\n')
        self.assertEqual(self._compact(), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_final_unterminated_duplicate_is_retained(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}')
        self.assertEqual(self._compact(), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_rewrite_return_count_is_nonblank_minus_retained(self) -> None:
        _write_export(
            self.path,
            '{"id":"a"}\n{"id":"b"}\n{"id":"a"}\n{"id":"c"}\n{"id":"b"}\n',
        )
        self.assertEqual(self._compact(), 2)
        self.assertEqual(
            self.path.read_bytes(),
            b'{"id":"a"}\n{"id":"b"}\n{"id":"c"}\n',
        )

    def test_rewrite_preserves_file_mode(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}\n', mode=0o600)
        self._compact()
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    # --- Intentional fail-closed hardening (C0 recorded the legacy defects) ---

    def test_malformed_json_fails_closed(self) -> None:
        original = b'{"id":"a"}\nNOTJSON\n{"id":"b"}\n'
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            self._compact()
        self.assertEqual(self.path.read_bytes(), original)

    def test_all_malformed_fails_closed(self) -> None:
        original = b"NOTJSON\nALSOBAD\n"
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            self._compact()
        self.assertEqual(self.path.read_bytes(), original)

    def test_missing_empty_null_and_integer_ids_fail_closed(self) -> None:
        cases = (
            b'{"id":"a"}\n{"v":1}\n',
            b'{"id":"a"}\n{"id":""}\n',
            b'{"id":"a"}\n{"id":null}\n',
            b'{"id":"a"}\n{"id":123}\n',
        )
        for original in cases:
            with self.subTest(original=original):
                _write_export(self.path, original)
                with self.assertRaises(InvalidExportRecordError):
                    self._compact()
                self.assertEqual(self.path.read_bytes(), original)

    def test_non_object_json_fails_closed(self) -> None:
        original = b'{"id":"a"}\n[1,2]\n'
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            self._compact()
        self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_utf8_fails_closed(self) -> None:
        original = b'{"id":"a"}\n\xff\n{"id":"b"}\n'
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            self._compact()
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
