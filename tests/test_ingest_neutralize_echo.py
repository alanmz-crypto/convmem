"""Tests for the pre-supersede provenance echo (neutralize-provenance-confirm)."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from ingest import _echo_neutralize_preview


def _capture(preview: list, verbose: bool = True) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        _echo_neutralize_preview(preview, "findings.md", "inter-model/findings.md#a1b2c3", verbose)
    return buf.getvalue()


class NeutralizeEchoTests(unittest.TestCase):
    def test_empty_preview_prints_nothing(self):
        self.assertEqual(_capture([]), "")

    def test_echo_line_has_count_span_and_tag(self):
        out = _capture(
            [
                {"id": "u1", "title": "One", "created_at": "2026-06-01", "updated_at": ""},
                {"id": "u2", "title": "Two", "created_at": "2026-07-07", "updated_at": ""},
            ]
        )
        lines = out.splitlines()
        self.assertIn("[neutralize] 2 active units for findings.md", lines[0])
        self.assertIn("(2026-06-01..2026-07-07)", lines[0])
        self.assertIn("tombstone as inter-model/findings.md#a1b2c3", lines[0])

    def test_missing_timestamps_omit_span(self):
        out = _capture([{"id": "u1", "title": "One", "created_at": "", "updated_at": ""}])
        first = out.splitlines()[0]
        self.assertIn("[neutralize] 1 active units for findings.md ->", first)
        self.assertNotIn("..", first)

    def test_verbose_sample_caps_at_five_with_more_marker(self):
        preview = [
            {"id": f"u{i}", "title": f"T{i}", "created_at": "", "updated_at": ""}
            for i in range(7)
        ]
        out = _capture(preview, verbose=True)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn('u0 "T0"', lines[1])
        self.assertIn('u4 "T4"', lines[1])
        self.assertNotIn("u5", lines[1])
        self.assertIn("(+2 more)", lines[1])

    def test_non_verbose_prints_single_line(self):
        preview = [{"id": "u1", "title": "One", "created_at": "", "updated_at": ""}]
        out = _capture(preview, verbose=False)
        self.assertEqual(len(out.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
