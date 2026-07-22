"""Fitness: roots_probe URI normalization + ValidationError recovery."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from pydantic import ValidationError, TypeAdapter
from mcp import types as mcp_types

import mcp_server


class McpRootsProbeHelpers(unittest.TestCase):
    def test_normalize_bare_path_to_file_uri(self):
        uri = mcp_server._normalize_root_uri("/home/lauer/Projects/convmem")
        self.assertTrue(uri.startswith("file://"))
        self.assertIn("/home/lauer/Projects/convmem", uri)

    def test_normalize_passes_through_file_uri(self):
        raw = "file:///home/lauer/Projects/convmem"
        self.assertEqual(mcp_server._normalize_root_uri(raw), raw)

    def test_recover_uris_from_cursor_bare_path_validation_error(self):
        # Reproduce Cursor sending a bare filesystem path as Root.uri
        try:
            TypeAdapter(mcp_types.ListRootsResult).validate_python(
                {"roots": [{"uri": "/home/lauer/Projects/convmem"}]}
            )
            self.fail("expected ValidationError")
        except ValidationError as exc:
            uris = mcp_server._uris_from_list_roots_validation_error(exc)
        self.assertEqual(len(uris), 1)
        self.assertTrue(uris[0].startswith("file://"))
        self.assertTrue(uris[0].endswith("/home/lauer/Projects/convmem") or "/home/lauer/Projects/convmem" in uris[0])


if __name__ == "__main__":
    unittest.main()
